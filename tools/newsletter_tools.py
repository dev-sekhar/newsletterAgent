import os
import requests
import groq
import json
from datetime import datetime, timedelta
import dateparser
from jinja2 import Environment, FileSystemLoader

from langchain_core.tools import tool
from database import setup_database, is_url_processed, add_url_to_db


class NewsletterPipeline:

    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.fast_model = "llama3-8b-8192"
        self.smart_model = "llama3-70b-8192"

    def fetch_all_articles(self, keyword):
        print("PIPELINE STEP: Fetching all articles...")
        since_date = (datetime.now() - timedelta(days=7)
                      ).strftime('%Y-%m-%dT%H:%M:%S')
        params = {'q': keyword, 'from': since_date, 'sortBy': 'publishedAt',
                  'apiKey': self.config['news_api_key'], 'language': 'en'}
        response = requests.get(
            "https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        return response.json().get('articles', [])

    def categorize_and_summarize_all(self, articles):
        print("PIPELINE STEP: Categorizing and summarizing all articles...")
        processed_articles = []
        for article in articles:
            if is_url_processed(article['url']):
                continue
            if not article.get('title') or "[Removed]" in article.get('title'):
                continue
            try:
                cat_prompt = f"Categorize the following article into ONE of these categories: {self.config['categories']}. Article Title: \"{article['title']}\". Return a JSON object with one key: \"category\". Example: {{\"category\": \"DeFi\"}}"
                cat_response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                                        {"role": "user", "content": cat_prompt}], temperature=0, response_format={"type": "json_object"})
                category = json.loads(cat_response.choices[0].message.content).get(
                    "category", "Other")
                if category not in self.config['categories']:
                    category = "Other"
                sum_prompt = f"Write a concise, 3-sentence summary for the following article. Article Title: \"{article['title']}\". Article Description: \"{article.get('description', '')}\". Return a JSON object with one key: \"summary\". Example: {{\"summary\": \"This is a summary.\"}}"
                sum_response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                                        {"role": "user", "content": sum_prompt}], temperature=0, response_format={"type": "json_object"})
                summary = json.loads(
                    sum_response.choices[0].message.content).get("summary")
                if category and summary:
                    processed_articles.append({'title': article['title'], 'url': article['url'], 'source': article['source']['name'], 'published_at': dateparser.parse(
                        article['publishedAt']).strftime('%b %d, %Y'), 'category': category, 'summary': summary})
                    add_url_to_db(article['url'])
                else:
                    print(
                        f"  > Skipping article '{article['title']}': Failed to get both category and summary.")
            except Exception as e:
                print(
                    f"  > Skipping article '{article['title']}' due to a critical error: {e}")
        categorized_content = {category: []
                               for category in self.config['categories']}
        for p_article in processed_articles:
            categorized_content[p_article['category']].append(p_article)
        return categorized_content

    def curate_selection(self, categorized_content):
        print("PIPELINE STEP: Curating final selection...")
        all_sources = {article['source'] for articles in categorized_content.values(
        ) for article in articles}
        if not all_sources:
            return categorized_content

        prompt = f"""You are a meticulous senior news editor. Review the following list of news sources: {list(all_sources)}. Your task is to identify and return only the sources that are well-known, reputable, and high-quality for news on business and technology. Exclude blogs, press release aggregators, and unknown entities. Return a valid JSON object with a single key "approved_sources" which is a list of strings of the sources you approve. Example: {{"approved_sources": ["Reuters", "TechCrunch", "Bloomberg"]}}"""
        try:
            response = self.groq_client.chat.completions.create(model=self.smart_model, messages=[
                                                                {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            reputable_sources = set(json.loads(
                response.choices[0].message.content).get("approved_sources", []))
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Using all sources as fallback.")
            reputable_sources = all_sources
        final_content = {}
        for category, articles in categorized_content.items():
            final_content[category] = [a for a in articles if a['source']
                                       in reputable_sources][:self.config['max_articles_per_category']]
        return final_content

    def assemble_newsletter(self, content, keyword):
        print("PIPELINE STEP: Assembling newsletter markdown...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('newsletter_template.md')
        return template.render(keyword=keyword, date=datetime.now().strftime('%B %d, %Y'), classified_articles=content)


@tool
def create_newsletter_draft(keyword: str) -> str:
    """Creates a draft of the newsletter for a given topic. This is the first step."""
    print("\nTOOL: `create_newsletter_draft` called.")
    config = {'groq_api_key': os.getenv("GROQ_API_KEY"), 'news_api_key': os.getenv("NEWS_API_KEY"), 'model_name': "llama3-8b-8192",
              'max_articles_per_category': 5, 'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]}
    pipeline = NewsletterPipeline(config)
    setup_database()
    all_articles = pipeline.fetch_all_articles(keyword)
    if not all_articles:
        return "Error: No articles were found for the keyword."
    categorized = pipeline.categorize_and_summarize_all(all_articles)
    if not any(categorized.values()):
        return "Error: No new articles could be processed."
    curated = pipeline.curate_selection(categorized)
    if not any(curated.values()):
        return "Error: No articles passed the curation filters."
    markdown_draft = pipeline.assemble_newsletter(curated, keyword)
    return markdown_draft


@tool
def review_newsletter_draft(review_input: dict | str) -> str:
    """
    Reviews a newsletter draft. Input can be a JSON object OR a string representation of a JSON object with two keys: 'newsletter_draft' (the full markdown text) and 'topic' (the original topic string).
    Returns a JSON object with 'decision' ('approve' or 'reject') and 'reason'.
    """
    print("\nTOOL: `review_newsletter_draft` called.")

    try:
        # If the agent passes a string, try to parse it as JSON
        if isinstance(review_input, str):
            # A common issue is the agent using single quotes, which is invalid JSON.
            # We can replace them with double quotes for a more robust parse.
            review_input = json.loads(review_input.replace("'", "\""))

        newsletter_draft = review_input.get('newsletter_draft')
        topic = review_input.get('topic')

        if not newsletter_draft or not topic:
            return json.dumps({"decision": "reject", "reason": "Input error: 'newsletter_draft' and 'topic' keys are required."})

    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"decision": "reject", "reason": f"Input error: The provided input was not a valid dictionary or JSON string. Error: {e}"})

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
        response = client.chat.completions.create(model="llama3-70b-8192", messages=[
                                                  {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"decision": "reject", "reason": f"An error occurred during review: {e}"})


@tool
def publish_final_newsletter(newsletter_markdown: str) -> str:
    """Saves the final, approved newsletter. Input is the full markdown string."""
    print("\nTOOL: `publish_final_newsletter` called.")
    filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(newsletter_markdown)
    return f"Successfully published newsletter to {filename}"
