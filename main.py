# main.py
import os
import requests
import openai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import dateparser
from jinja2 import Environment, FileSystemLoader

# Import our database functions
from database import setup_database, is_url_processed, add_url_to_db

# --- CONFIGURATION ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

KEYWORD = "Blockchain"
CATEGORIES = ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"


# --- 1. DATA INGESTION ---
def fetch_articles(keyword):
    """Fetches articles from the last 7 days using NewsAPI."""
    print("Fetching articles...")
    since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
    params = {
        'q': keyword,
        'from': since_date,
        'sortBy': 'publishedAt',
        'apiKey': NEWS_API_KEY,
        'language': 'en',
    }
    response = requests.get(NEWS_API_ENDPOINT, params=params)
    response.raise_for_status() # Raise an exception for bad status codes
    return response.json().get('articles', [])

# --- 2. CLASSIFICATION & SUMMARIZATION ---
def classify_and_summarize_article(article):
    """Uses OpenAI to classify and summarize a single article."""
    print(f"Processing article: {article['title']}")
    prompt = f"""
    You are an expert tech news analyst. Your task is to classify and summarize an article.

    Article Title: "{article['title']}"
    Article Description: "{article.get('description', 'No description available.')}"

    First, classify the article into ONE of the following categories: {', '.join(CATEGORIES)}.
    Second, write a concise 3-sentence summary of the article.

    Provide your response in a JSON format with two keys: "category" and "summary".
    Example:
    {{
      "category": "DeFi",
      "summary": "This is a three-sentence summary of the article."
    }}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = openai.get_response_json(response)
        # Validate the category
        if result.get("category") not in CATEGORIES:
            result["category"] = "Other"
        return result
    except Exception as e:
        print(f"  > Could not process article with OpenAI: {e}")
        return None

# --- 3. NEWSLETTER GENERATION ---
def generate_newsletter(classified_articles):
    """Generates the newsletter content using a Jinja2 template."""
    print("Generating newsletter...")
    env = Environment(loader=FileSystemLoader('templates/'))
    template = env.get_template('newsletter_template.md')

    newsletter_content = template.render(
        keyword=KEYWORD,
        date=datetime.now().strftime('%B %d, %Y'),
        classified_articles=classified_articles
    )
    return newsletter_content

# --- MAIN WORKFLOW ---
def run_agent():
    # Setup
    setup_database()

    # 1. Ingestion
    articles = fetch_articles(KEYWORD)
    
    # 2. Filtering, Deduplication, and Classification
    classified_articles = {category: [] for category in CATEGORIES}
    
    for article in articles:
        url = article['url']
        # Filter out already processed articles
        if is_url_processed(url):
            print(f"Skipping already processed article: {url}")
            continue

        # Filter out articles with no title or from unwanted domains if needed
        if not article.get('title') or "[Removed]" in article.get('title'):
            continue

        analysis = classify_and_summarize_article(article)
        
        if analysis:
            category = analysis['category']
            summary = analysis['summary']
            
            classified_articles[category].append({
                'title': article['title'],
                'url': url,
                'source': article['source']['name'],
                'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                'summary': summary
            })
            # Mark as processed
            add_url_to_db(url)

    # 3. Generation
    newsletter = generate_newsletter(classified_articles)
    
    # 4. Publication
    output_filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(output_filename, 'w') as f:
        f.write(newsletter)
    
    print(f"\n✅ Newsletter generated successfully! Saved as {output_filename}")


if __name__ == "__main__":
    run_agent()