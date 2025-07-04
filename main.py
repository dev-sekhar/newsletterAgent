import os
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator

def main():
    load_dotenv()

    # Centralized Configuration
    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'model_name': "llama3-8b-8192",
        # 'candidate_source_count' is no longer needed
        'max_articles_per_category': 3, # <-- NEW: Set a limit for diversity
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
    }

    keyword = os.getenv("KEYWORD_INPUT", "Blockchain")
    orchestrator = Orchestrator(config)
    orchestrator.run(keyword)

if __name__ == "__main__":
    main()