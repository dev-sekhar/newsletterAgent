# main.py

import os
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator


def main():
    """
    This is the main entry point for the Multi-Agent Newsletter System.
    It sets up the configuration and triggers the main orchestrator.
    """
    load_dotenv()
    print("--- System Booting Up ---")

    # Centralized Configuration
    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'max_articles_per_category': 3,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"],
        'template_folder': 'templates',
        'template_name': 'newsletter_template.md'
    }

    # Get the topic from GitHub Actions input or use a default
    topic = os.getenv("KEYWORD_INPUT", "Artificial Intelligence")

    # Initialize and run the main orchestrator
    orchestrator = Orchestrator(config)
    orchestrator.run(topic)


if __name__ == "__main__":
    main()
