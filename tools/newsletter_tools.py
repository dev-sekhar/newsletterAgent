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

# --- This class holds the core logic for our pipeline steps ---


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
                # STEP 1: CATEGORIZE
                cat_prompt = f"Categorize the following article into ONE of these categories: {self.config['categories']}. Article Title: \"{article['title']}\". Return a JSON object with one key: \"category\". Example: {{\"category\": \"DeFi\"}}"
                cat_response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                                        {"role": "user", "content": cat_prompt}], temperature=0, response_format={"type": "json_object"})
                category = json.loads(cat_response.choices[0].message.content).get(
                    "category", "Other")
                if category not in self.config['categories']:
                    category = "Other"

                # STEP 2: SUMMARIZE
                sum_prompt = f"Write a concise, 3-sentence summary for the following article. Article Title: \"{article['title']}\". Article Description: \"{article.get('description', '')}\". Return a JSON object with one key: \"summary\". Example: {{\"summary\": \"This is a summary.\"}}"
                sum_response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                                        {"role": "user", "content": sum_prompt}], temperature=0, response_format={"type": "json_object"})
                summary = json.loads(
                    sum_response.choices[0].message.content).get("summary")

                # STEP 3: COMBINE
                if category and summary:
                    processed_articles.append({
                        'title': article['title'], 'url': article['url'], 'source': article['source']['name'],
                        'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                        'category': category, 'summary': summary
                    })
                    add_url_to_db(article['url'])
                else:
                    print(
                        f"  > Skipping article '{article['title']}': Failed to get both category and summary.")
            except Exception as e:
                print(
                    f"  > Skipping article '{article['title']}' due to a critical error: {e}")

        # Group the successfully processed articles by category
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
            print(
                f"  > Curation LLM approved {len(reputable_sources)} sources.")
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Using all sources as fallback.")
            reputable_sources = all_sources

        final_content = {}
        for category, articles in categorized_content.items():
            reputable_articles = [
                a for a in articles if a['source'] in reputable_sources]
            final_content[category] = reputable_articles[:
                                                         self.config['max_articles_per_category']]
        return final_content

    def assemble_newsletter(self, content, keyword):
        print("PIPELINE STEP: Assembling newsletter markdown...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('newsletter_template.md')
        return template.render(keyword=keyword, date=datetime.now().strftime('%B %d, %Y'), classified_articles=content)

# --- SHARED STATE & THE FINAL, ADVANCED TOOLBOX ---


CONTEXT = {"draft": None, "review": None}


@tool
def create_initial_draft(keyword: str) -> str:
    """
    This is the very first step. It fetches articles for a broad keyword, processes them, and creates an initial newsletter draft.
    This draft MUST be reviewed. It saves the draft to a shared context.
    """
    print(f"\nTOOL: `create_initial_draft` called for keyword '{keyword}'.")
    global CONTEXT
    # Clear context and db at the start of a new process to prevent loops
    CONTEXT = {"draft": None, "review": None}
    db_file = "articles.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print("  > Cleared previous database for a fresh start.")
    setup_database()

    config = {
        'groq_api_key': os.getenv("GROQ_API_KEY"),
        'news_api_key': os.getenv("NEWS_API_KEY"),
        'model_name': "llama3-8b-8192",
        'max_articles_per_category': 5,  # Create a larger draft for the reviewer
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
    }

    pipeline = NewsletterPipeline(config)

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
    CONTEXT["draft"] = markdown_draft
    return f"Successfully created an initial draft for '{keyword}'. It is now ready for review."


@tool
def review_draft_for_relevance_and_quality(topic: str) -> str:
    """
    Reviews the draft currently in the context. This is a critical quality check step.
    Input is the original topic to check for relevance. Returns a JSON object with a 'decision' ('approve' or 'reject') and a 'reason'.
    """
    print("\nTOOL: `review_draft_for_relevance_and_quality` called.")
    global CONTEXT
    newsletter_draft = CONTEXT.get("draft")
    if not newsletter_draft:
        return "Error: No draft found in the context to review. You must run `create_initial_draft` first."

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
        review_result = json.loads(response.choices[0].message.content)
        CONTEXT["review"] = review_result
        return f"Review complete. Decision: {review_result.get('decision')}. Reason: {review_result.get('reason')}"
    except Exception as e:
        CONTEXT["review"] = {"decision": "reject",
                             "reason": f"An error occurred during review: {e}"}
        return f"An error occurred during review: {e}"


@tool
def publish_approved_newsletter() -> str:
    """
    Publishes the newsletter if the latest review decision was 'approve'. This is the final step.
    This tool takes no input, as it reads all required information from the shared context.
    """
    print("\nTOOL: `publish_approved_newsletter` called.")
    global CONTEXT
    newsletter_markdown = CONTEXT.get("draft")
    review = CONTEXT.get("review")

    if not newsletter_markdown:
        return "Error: No draft found in the context to publish. A draft must be created first."
    if not review or review.get("decision") != "approve":
        return f"Error: Cannot publish. The draft was not approved by the review step. The reason was: {review.get('reason', 'No reason provided.')}"

    filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(newsletter_markdown)
    return f"Successfully published the approved newsletter to {filename}"
