# tools/newsletter_tools.py

import os
import requests
import groq
import json
import ast  # For safely parsing string representations of lists/dicts
from datetime import datetime, timedelta
import dateparser
from jinja2 import Environment, FileSystemLoader

from langchain_core.tools import tool
from database import setup_database, is_url_processed, add_url_to_db
from bs4 import BeautifulSoup  # Import for HTML sanitation

# --- This class holds the core logic for our pipeline steps ---


class NewsletterPipeline:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.fast_model = "llama3-8b-8192"
        self.smart_model = "llama3-70b-8192"

    def fetch_all_articles(self, keyword):
        print(f"PIPELINE STEP: Fetching articles for keyword: '{keyword}'...")
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
                # Sanitize the description to remove HTML tags
                raw_description = article.get('description', '')
                if raw_description:
                    soup = BeautifulSoup(raw_description, 'html.parser')
                    clean_description = soup.get_text(
                        separator=' ', strip=True)
                else:
                    clean_description = ''

                # STEP 1: CATEGORIZE
                cat_prompt = f"Categorize the following article into ONE of these categories: {self.config['categories']}. Article Title: \"{article['title']}\". Return a JSON object with one key: \"category\". Example: {{\"category\": \"DeFi\"}}"
                cat_response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                                        {"role": "user", "content": cat_prompt}], temperature=0, response_format={"type": "json_object"})
                category = json.loads(cat_response.choices[0].message.content).get(
                    "category", "Other")
                if category not in self.config['categories']:
                    category = "Other"

                # STEP 2: SUMMARIZE
                sum_prompt = f"Write a concise, 3-sentence summary for the following article. Article Title: \"{article['title']}\". Article Description: \"{clean_description}\". Return a JSON object with one key: \"summary\". Example: {{\"summary\": \"This is a summary.\"}}"
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
def create_initial_draft(keywords: list[str] | str) -> str:
    """
    Creates the first draft of the newsletter using a list of specific keywords. This must be used after generating sub-topics.
    Input can be a list of keyword strings OR a string representation of a list.
    It fetches, categorizes, curates, and assembles the draft, saving it to the context.
    """
    print(f"\nTOOL: `create_initial_draft` called.")
    global CONTEXT

    try:
        if isinstance(keywords, str):
            import ast
            keywords = ast.literal_eval(keywords)
        if not isinstance(keywords, list):
            raise ValueError("Input must be a list of strings.")
        print(f"  > Processing with {len(keywords)} keywords: {keywords}")
    except (ValueError, SyntaxError) as e:
        return f"Error: Input was not a valid list or list string. Error: {e}"

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
        'max_articles_per_category': 5,
        'categories': ["DeFi", "Crypto", "Web3", "NFTs", "Regulation", "Metaverse", "Other"]
    }

    pipeline = NewsletterPipeline(config)
    all_articles = []
    for keyword in keywords:
        all_articles.extend(pipeline.fetch_all_articles(keyword))

    unique_articles = list(
        {article['url']: article for article in all_articles}.values())
    print(f"  > Found {len(unique_articles)} unique articles in total.")

    if not unique_articles:
        return "Error: No articles were found for any of the sub-topics."

    categorized = pipeline.categorize_and_summarize_all(unique_articles)
    if not any(categorized.values()):
        return "Error: No new articles could be processed."

    curated = pipeline.curate_selection(categorized)
    if not any(curated.values()):
        return "Error: No articles passed the curation filters."

    primary_keyword = keywords[0] if keywords else "General"
    markdown_draft = pipeline.assemble_newsletter(curated, primary_keyword)
    CONTEXT["draft"] = markdown_draft
    return f"Successfully created an initial draft using {len(keywords)} sub-topics. It is now ready for review."


@tool
def review_draft_for_relevance_and_quality(topic: str) -> str:
    """
    Reviews the draft currently in the context. This is a critical quality check step that must be performed after creating a draft.
    Input is the original topic string to check for relevance. Returns a JSON object with a 'decision' ('approve' or 'reject') and a 'reason'.
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
    Publishes the newsletter if approved. Creates versioned files to prevent overwriting.
    This is the final step and takes no input.
    """
    print("\nTOOL: `publish_approved_newsletter` called.")
    global CONTEXT
    review = CONTEXT.get("review")
    newsletter_markdown = CONTEXT.get("draft")

    if not newsletter_markdown:
        return "Error: No draft found in the context to publish."
    if not review or review.get("decision") != "approve":
        return f"Error: Cannot publish. The draft was not approved. Last review reason: {review.get('reason', 'No reason provided.')}"

    base_filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}"
    output_filename = f"{base_filename}.md"
    version = 2
    while os.path.exists(output_filename):
        output_filename = f"{base_filename}_v{version}.md"
        version += 1

    print(f"  > Target filename for publishing is '{output_filename}'.")
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(newsletter_markdown)

    return f"Successfully published the approved newsletter to {output_filename}"
