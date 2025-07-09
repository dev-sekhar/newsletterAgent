# run_part1_drafting.py

import os
import json
from dotenv import load_dotenv

# --- START OF FIX: EXPLICIT LANGSMITH SETUP ---
from langsmith import Client
from langchain_core.tracers.langchain import LangChainTracer

def setup_langsmith_tracer():
    """Explicitly configures and returns a configuration dictionary for LangChain tracing."""
    # Check if the required environment variables are set
    if all(os.getenv(var) for var in ["LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT", "LANGCHAIN_TRACING_V2"]):
        if os.getenv("LANGCHAIN_TRACING_V2").lower() == 'true':
            print("--- LangSmith environment variables found. Setting up tracer. ---")
            client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
            tracer = LangChainTracer(project_name=os.getenv("LANGCHAIN_PROJECT"), client=client)
            # This config dict will be passed to LLM calls
            return {"callbacks": [tracer]}
    
    print("--- LangSmith environment variables not set or tracing not enabled. Skipping tracer setup. ---")
    return {} # Return an empty config if not enabled
# --- END OF FIX ---

from agents.orchestrator import Orchestrator

def create_review_package():
    """
    Runs the first part of the workflow: Research, Analysis, and Curation.
    Saves the output to a JSON file for human review.
    """
    load_dotenv()
    print("--- WORKFLOW PART 1: DRAFTING & REVIEW PACKAGE CREATION ---")

    # Setup tracer config first
    tracer_config = setup_langsmith_tracer()

    # Centralized Configuration, now including tracer config
    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'max_articles_per_category': 3,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"],
        'tracer_config': tracer_config # Pass the tracer config down
    }

    topic = os.getenv("KEYWORD_INPUT", "Artificial Intelligence")
    
    orchestrator = Orchestrator(config)
    
    approved_for_review, rejected_for_review = orchestrator.run_curation(topic)

    if not approved_for_review and not rejected_for_review:
        print("\n--- No articles processed. Halting. No review package will be created. ---")
        return

    review_package = {
        "topic": topic,
        "approved_articles": approved_for_review,
        "rejected_articles": rejected_for_review
    }

    output_filename = "review_package.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(review_package, f, indent=4)
        
    print(f"\n--- Review package created successfully at '{output_filename}'. Please review, edit, and then run Part 2. ---")

if __name__ == "__main__":
    create_review_package()