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

# --- This class holds the logic for our pipeline steps ---


class NewsletterPipeline:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])

    def fetch_all_articles(self, keyword):
        print("TOOL STEP: Fetching all articles...")
        since_date = (datetime.now() - timedelta(days=7)
                      ).strftime('%Y-%m-%dT%H:%M:%S')
        params = {
            'q': keyword,
            'from': since_date,
            'sortBy': 'publishedAt',
            'apiKey': self.config['news_api_key'],
            'language': 'en'
        }
        response = requests.get(
            "https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        return response.json().get('articles', [])

    def categorize_and_summarize_all(self, articles):
        print("TOOL STEP: Categorizing and summarizing all articles...")
        categorized_content = {category: []
                               for category in self.config['categories']}

        for article in articles:
            # Skip articles that are already in our database
            if is_url_processed(article['url']):
                continue

            # Skip articles with no title
            if not article.get('title') or "[Removed]" in article.get('title'):
                continue

            # --- ROBUST ERROR HANDLING FOR EACH ARTICLE ---
            try:
                prompt = f"""
                You are an expert tech news analyst. Your task is to classify and summarize an article.

                Article Title: "{article['title']}"
                Article Description: "{article.get('description', 'No description available.')}"

                First, classify the article into ONE of the following categories: {', '.join(self.config['categories'])}.
                Second, write a concise 3-sentence summary of the article.

                Provide your response as a valid JSON object with two keys: "category" and "summary".
                Do not include any other text or explanation.
                Example:
                {{
                  "category": "DeFi",
                  "summary": "This is a three-sentence summary of the article."
                }}
                """

                response = self.groq_client.chat.completions.create(
                    model=self.config['model_name'],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                analysis = json.loads(response.choices[0].message.content)

                # Check if the required keys exist in the LLM's response
                if "category" in analysis and "summary" in analysis:
                    # Ensure the category is valid, otherwise assign to "Other"
                    if analysis.get("category") not in self.config['categories']:
                        analysis["category"] = "Other"

                    # If all checks pass, add the structured content
                    categorized_content[analysis['category']].append({
                        'title': article['title'], 'url': article['url'], 'source': article['source']['name'],
                        'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                        'summary': analysis['summary']
                    })
                    # Add the URL to the database to prevent future processing
                    add_url_to_db(article['url'])
                else:
                    # The LLM returned valid JSON, but it was missing our required keys.
                    print(
                        f"  > Skipping article '{article['title']}': LLM response missing required keys.")

            except Exception as e:
                # Catch any other error during processing (API errors, JSON parsing, etc.)
                print(
                    f"  > Skipping article '{article['title']}' due to error: {e}")

        return categorized_content

    def curate_selection(self, categorized_content):
        print("TOOL STEP: Curating final selection...")
        all_sources = {article['source'] for articles in categorized_content.values(
        ) for article in articles}
        if not all_sources:
            return categorized_content  # Nothing to curate

        prompt = f"""
        You are a meticulous senior news editor. Review the following list of news sources:
        {list(all_sources)}
        Your task is to identify and return only the sources that are well-known, reputable, and high-quality for news on business and technology. Exclude blogs, press release aggregators, and unknown entities.
        Return a JSON object with a single key "approved_sources" which is a list of strings of the sources you approve.
        Example: {{"approved_sources": ["Reuters", "TechCrunch", "Bloomberg"]}}
        """
        try:
            response = self.groq_client.chat.completions.create(model=self.config['model_name'], messages=[
                                                                {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            reputable_sources = set(json.loads(
                response.choices[0].message.content).get("approved_sources", []))
            print(
                f"  > LLM approved {len(reputable_sources)} sources for curation.")
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Using all sources as fallback.")
            reputable_sources = all_sources  # Fallback

        final_content = {}
        for category, articles in categorized_content.items():
            reputable_articles = [
                a for a in articles if a['source'] in reputable_sources]
            final_content[category] = reputable_articles[:
                                                         self.config['max_articles_per_category']]

        return final_content

    def assemble_newsletter(self, content, keyword):
        print("TOOL STEP: Assembling newsletter markdown...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('newsletter_template.md')
        return template.render(keyword=keyword, date=datetime.now().strftime('%B %d, %Y'), classified_articles=content)

    def publish_newsletter(self, markdown):
        print("TOOL STEP: Publishing newsletter...")
        filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown)
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

    # Instantiate the pipeline and run the steps in a reliable sequence
    pipeline = NewsletterPipeline(config)
    setup_database()

    all_articles = pipeline.fetch_all_articles(keyword)
    if not all_articles:
        return "Workflow failed: No articles were found for the keyword."

    categorized = pipeline.categorize_and_summarize_all(all_articles)
    if not any(categorized.values()):
        return "Workflow failed: No new articles could be processed."

    curated = pipeline.curate_selection(categorized)
    if not any(curated.values()):
        return "Workflow failed: No articles passed the curation filters."

    markdown = pipeline.assemble_newsletter(curated, keyword)
    result = pipeline.publish_newsletter(markdown)

    return result
