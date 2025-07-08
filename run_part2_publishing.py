# run_part1_drafting.py

import os
import json
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator


def create_review_package():
    """
    Runs the first part of the workflow: Research, Analysis, and Curation.
    Saves the output to a JSON file for human review.
    """
    load_dotenv()
    print("--- WORKFLOW PART 1: DRAFTING & REVIEW PACKAGE CREATION ---")

    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'max_articles_per_category': 3,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"],
    }

    topic = os.getenv("KEYWORD_INPUT", "Artificial Intelligence")

    orchestrator = Orchestrator(config)

    # Run the first part of the pipeline
    approved_for_review, rejected_for_review = orchestrator.run_curation(topic)

    if not approved_for_review and not rejected_for_review:
        print("\n--- No articles processed. Halting. ---")
        return

    # Prepare the review package
    review_package = {
        "topic": topic,
        "approved_articles": approved_for_review,
        "rejected_articles": rejected_for_review
    }

    # Save to a file
    output_filename = "review_package.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(review_package, f, indent=4)

    print(
        f"\n--- Review package created successfully at '{output_filename}'. Please review, edit, and then run Part 2. ---")


if __name__ == "__main__":
    create_review_package()
