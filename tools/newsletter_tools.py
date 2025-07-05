# tools/newsletter_tools.py

import os
import requests
import groq
import json
from datetime import datetime, timedelta
import dateparser
from jinja2 import Environment, FileSystemLoader

from langchain_core.tools import tool
from database import setup_database, is_url_processed, add_url_to_db

# --- This class still holds our core logic, but it's now used by multiple tools ---
class NewsletterPipeline:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])

    def fetch_all_articles(self, keyword):
        # ... (This method is the same as before)
        print("PIPELINE STEP: Fetching all articles...")
        since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        params = {'q': keyword, 'from': since_date, 'sortBy': 'publishedAt', 'apiKey': self.config['news_api_key'], 'language': 'en'}
        response = requests.get("https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        return response.json().get('articles', [])

    def categorize_and_summarize_all(self, articles):
        # ... (This method is the same as before, with the robustness fix)
        print("PIPELINE STEP: Categorizing and summarizing all articles...")
        categorized_content = {category: [] for category in self.config['categories']}
        for article in articles:
            if is_url_processed(article['url']): continue
            if not article.get('title') or "[Removed]" in article.get('title'): continue
            try:
                prompt = f"Provide your response as a valid JSON object... (Your full classification prompt)"
                response = self.groq_client.chat.completions.create(model=self.config['model_name'], messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
                analysis = json.loads(response.choices[0].message.content)
                if "category" in analysis and "summary" in analysis:
                    if analysis.get("category") not in self.config['categories']: analysis["category"] = "Other"
                    categorized_content[analysis['category']].append({'title': article['title'], 'url': article['url'], 'source': article['source']['name'], 'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'), 'summary': analysis['summary']})
                    add_url_to_db(article['url'])
                else:
                    print(f"  > Skipping article '{article['title']}': LLM response missing keys.")
            except Exception as e:
                print(f"  > Skipping article '{article['title']}' due to error: {e}")
        return categorized_content

    def curate_selection(self, categorized_content):
        # ... (This method is the same as before)
        print("PIPELINE STEP: Curating final selection...")
        all_sources = {article['source'] for articles in categorized_content.values() for article in articles}
        if not all_sources: return categorized_content
        prompt = f"Return a JSON object with a single key \"approved_sources\"... (Your full reputation prompt)"
        try:
            response = self.groq_client.chat.completions.create(model=self.config['model_name'], messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            reputable_sources = set(json.loads(response.choices[0].message.content).get("approved_sources", []))
        except Exception:
            reputable_sources = all_sources
        final_content = {}
        for category, articles in categorized_content.items():
            reputable_articles = [a for a in articles if a['source'] in reputable_sources]
            final_content[category] = reputable_articles[:self.config['max_articles_per_category']]
        return final_content
    
    def assemble_newsletter(self, content, keyword):
        # ... (This method is the same as before)
        print("PIPELINE STEP: Assembling newsletter markdown...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('newsletter_template.md')
        return template.render(keyword=keyword, date=datetime.now().strftime('%B %d, %Y'), classified_articles=content)

# --- THE NEW, GRANULAR TOOLBOX ---

@tool
def create_newsletter_draft(keyword: str) -> str:
    """
    Creates a complete draft of the newsletter for a given topic. This is the first major step.
    It performs fetching, categorization, curation, and assembly.
    The output is the full newsletter content as a single markdown string.
    """
    print("\nTOOL: `create_newsletter_draft` called.")
    config = {'groq_api_key': os.getenv("GROQ_API_KEY"), 'news_api_key': os.getenv("NEWS_API_KEY"), 'model_name': "llama3-8b-8192", 'max_articles_per_category': 5, 'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]} # Increased max per category to create a larger draft
    pipeline = NewsletterPipeline(config)
    setup_database()
    
    all_articles = pipeline.fetch_all_articles(keyword)
    if not all_articles: return "Error: No articles were found for the keyword."
    
    categorized = pipeline.categorize_and_summarize_all(all_articles)
    if not any(categorized.values()): return "Error: No new articles could be processed."

    curated = pipeline.curate_selection(categorized)
    if not any(curated.values()): return "Error: No articles passed the curation filters."

    markdown_draft = pipeline.assemble_newsletter(curated, keyword)
    return markdown_draft

@tool
def review_newsletter_draft(newsletter_draft: str, topic: str) -> str:
    """
    Reviews a newsletter draft for quality and relevance. This is a critical quality assurance step.
    Input is the full markdown text of the newsletter and the original topic.
    Returns a JSON object with a 'decision' ('approve' or 'reject') and a 'reason'.
    """
    print("\nTOOL: `review_newsletter_draft` called.")
    client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    You are a meticulous Editor-in-Chief. Your task is to review the following newsletter draft on the topic of '{topic}'.

    Perform two checks:
    1.  **Quality & Sufficiency:** Is the newsletter substantial? A good newsletter should have at least 3 categories with articles. If it's too short or empty, reject it.
    2.  **Relevance:** Read each article's summary. Is every single article genuinely related to '{topic}'? If you find any off-topic articles, reject the draft and mention which articles are problematic.

    Return your final verdict as a single, valid JSON object with two keys: "decision" (which must be "approve" or "reject") and "reason" (a brief explanation for your decision).

    Newsletter Draft:
    ---
    {newsletter_draft}
    ---
    """
    try:
        response = client.chat.completions.create(model="llama3-70b-8192", messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"decision": "reject", "reason": f"An error occurred during review: {e}"})

@tool
def publish_final_newsletter(newsletter_markdown: str) -> str:
    """
    Saves the final, approved newsletter content to a file. This is the final step.
    Input must be the full markdown string of the newsletter.
    """
    print("\nTOOL: `publish_final_newsletter` called.")
    filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(newsletter_markdown)
    return f"Successfully published newsletter to {filename}"