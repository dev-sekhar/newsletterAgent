# tools/newsletter_tools.py

from langchain_core.tools import tool
import requests
import groq
import json
from datetime import datetime, timedelta
import dateparser
from collections import Counter
from jinja2 import Environment, FileSystemLoader
from database import setup_database, is_url_processed, add_url_to_db

# --- This class holds the logic for our pipeline steps ---
# It's not an agent itself, but a collection of methods our tool can call.
class NewsletterPipeline:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])

    def fetch_all_articles(self, keyword):
        # Logic from old SourceIdentifierAgent
        print("TOOL STEP: Fetching all articles...")
        since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        params = {'q': keyword, 'from': since_date, 'sortBy': 'publishedAt', 'apiKey': self.config['news_api_key'], 'language': 'en'}
        response = requests.get("https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        return response.json().get('articles', [])

    def categorize_and_summarize_all(self, articles):
        # Logic from old ContentCreationAgent
        print("TOOL STEP: Categorizing and summarizing all articles...")
        categorized_content = {category: [] for category in self.config['categories']}
        for article in articles:
            if is_url_processed(article['url']): continue
            prompt = f"Provide your response as a valid JSON object... (Your full classification prompt)"
            try:
                response = self.groq_client.chat.completions.create(model=self.config['model_name'], messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
                analysis = json.loads(response.choices[0].message.content)
                if analysis.get("category") not in self.config['categories']: analysis["category"] = "Other"
                categorized_content[analysis['category']].append({
                    'title': article['title'], 'url': article['url'], 'source': article['source']['name'],
                    'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                    'summary': analysis['summary']
                })
                add_url_to_db(article['url'])
            except Exception as e:
                print(f"  > Failed to process article '{article['title']}': {e}")
        return categorized_content

    def curate_selection(self, categorized_content):
        # Logic from old CurationAgent
        print("TOOL STEP: Curating final selection...")
        all_sources = {article['source'] for articles in categorized_content.values() for article in articles}
        prompt = f"Return a valid JSON object... (Your full reputation prompt for sources: {list(all_sources)})"
        try:
            response = self.groq_client.chat.completions.create(model=self.config['model_name'], messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            reputable_sources = set(json.loads(response.choices[0].message.content).get("approved_sources", []))
        except Exception:
            reputable_sources = all_sources # Fallback

        final_content = {}
        for category, articles in categorized_content.items():
            reputable = [a for a in articles if a['source'] in reputable_sources]
            final_content[category] = reputable[:self.config['max_articles_per_category']]
        return final_content
    
    def assemble_newsletter(self, content, keyword):
        # Logic from old NewsletterAssemblerAgent
        print("TOOL STEP: Assembling newsletter markdown...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('newsletter_template.md')
        return template.render(keyword=keyword, date=datetime.now().strftime('%B %d, %Y'), classified_articles=content)

    def publish_newsletter(self, markdown):
        # Logic from old PublisherAgent
        print("TOOL STEP: Publishing newsletter...")
        filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f: f.write(markdown)
        return f"Successfully published newsletter to {filename}"

# --- This is the single, powerful tool the Master Agent will use ---
@tool
def run_newsletter_creation_pipeline(keyword: str) -> str:
    """
    Use this tool to run the entire weekly newsletter creation process.
    The input must be a single string representing the topic keyword for the newsletter.
    This tool will automatically handle fetching, classifying, curating, assembling, and publishing.
    """
    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'model_name': "llama3-8b-8192",
        'max_articles_per_category': 3,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
    }
    
    # Instantiate the pipeline and run the steps in a hardcoded, reliable sequence
    pipeline = NewsletterPipeline(config)
    setup_database()
    
    all_articles = pipeline.fetch_all_articles(keyword)
    if not all_articles: return "Workflow failed: No articles were found for the keyword."
    
    categorized = pipeline.categorize_and_summarize_all(all_articles)
    if not any(categorized.values()): return "Workflow failed: No new articles could be processed."

    curated = pipeline.curate_selection(categorized)
    if not any(curated.values()): return "Workflow failed: No articles passed the curation filters."

    markdown = pipeline.assemble_newsletter(curated, keyword)
    result = pipeline.publish_newsletter(markdown)
    
    return result 
