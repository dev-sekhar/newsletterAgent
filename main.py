# main.py

import os
from dotenv import load_dotenv

# Import the main Orchestrator class from your new agents package
from agents.orchestrator import Orchestrator


def main():
    """
    This is the main entry point for the Newsletter Agent workflow.
    It sets up the configuration and triggers the orchestrator.
    """

    # Load environment variables from a .env file if it exists (for local development)
    load_dotenv()

    # --- Centralized Configuration ---
    # All settings for the agents are defined here.
    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'model_name': "llama3-8b-8192",
        'candidate_source_count': 25,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
    }

    # Get the primary keyword from the GitHub Actions input, with a fallback for local runs.
    keyword = os.getenv("KEYWORD_INPUT", "Blockchain")

    # Initialize the Orchestrator with the configuration
    orchestrator = Orchestrator(config)

    # Run the entire multi-agent workflow
    orchestrator.run(keyword)


if __name__ == "__main__":
    # This ensures the main() function is called when you run "python main.py"
    main()
