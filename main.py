# main.py
import os
import requests
import groq  # Changed from openai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import dateparser
from jinja2 import Environment, FileSystemLoader

# Import our database functions
from database import setup_database, is_url_processed, add_url_to_db

# --- CONFIGURATION ---
load_dotenv()
# Initialize Groq client
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

KEYWORD = "Blockchain"
CATEGORIES = ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"
MODEL_NAME = "llama3-8b-8192" # Using Llama 3 8B on Groq

# --- 1. DATA INGESTION ---
# This function remains IDENTICAL
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
    response.raise_for_status()
    return response.json().get('articles', [])

# --- 2. CLASSIFICATION & SUMMARIZATION (MODIFIED FOR GROQ) ---
def classify_and_summarize_article(article):
    """Uses an open-source model via Groq to classify and summarize."""
    print(f"Processing article: {article['title']}")
    # The prompt is the same, as Llama 3 is excellent at following instructions.
    prompt = f"""
    You are an expert tech news analyst. Your task is to classify and summarize an article.

    Article Title: "{article['title']}"
    Article Description: "{article.get('description', 'No description available.')}"

    First, classify the article into ONE of the following categories: {', '.join(CATEGORIES)}.
    Second, write a concise 3-sentence summary of the article.

    Provide your response ONLY in a valid JSON format with two keys: "category" and "summary".
    Do not include any other text or explanation before or after the JSON object.
    Example:
    {{
      "category": "DeFi",
      "summary": "This is a three-sentence summary of the article."
    }}
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0, # For consistent, deterministic output
            response_format={"type": "json_object"} # Crucial for reliable JSON output
        )
        # Note: Groq's response structure is identical to OpenAI's
        result = groq.get_response_json(response)

        # Validate the category
        if result.get("category") not in CATEGORIES:
            result["category"] = "Other"
        return result
    except Exception as e:
        print(f"  > Could not process article with Groq: {e}")
        return None

# --- 3. NEWSLETTER GENERATION & MAIN WORKFLOW ---
# The rest of the file (generate_newsletter, run_agent, etc.) remains IDENTICAL
# to the previous version. I'm omitting it here for brevity, but you would
# just paste the new classification function into the original file.

# ... (paste the generate_newsletter and run_agent functions from the previous response here)
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
    setup_database()
    articles = fetch_articles(KEYWORD)
    classified_articles = {category: [] for category in CATEGORIES}

    for article in articles:
        url = article['url']
        if is_url_processed(url):
            print(f"Skipping already processed article: {url}")
            continue
        if not article.get('title') or "[Removed]" in article.get('title'):
            continue

        analysis = classify_and_summarize_article(article)

        if analysis:
            category = analysis['category']
            summary = analysis['summary']
            classified_articles[category].append({
                'title': article['title'], 'url': url, 'source': article['source']['name'],
                'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                'summary': summary
            })
            add_url_to_db(url)

    newsletter = generate_newsletter(classified_articles)
    output_filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(output_filename, 'w') as f:
        f.write(newsletter)

    print(f"\n✅ Newsletter generated successfully! Saved as {output_filename}")

if __name__ == "__main__":
    run_agent()