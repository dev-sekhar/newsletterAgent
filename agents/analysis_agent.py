# agents/analysis_agent.py

import groq
import json
import dateparser
from bs4 import BeautifulSoup
from database import is_url_processed, add_url_to_db


class AnalysisAgent:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.fast_model = "llama3-8b-8192"
        # Store the tracer config from the main config object
        self.tracer_config = config.get('tracer_config', {})

    def execute(self, articles: list[dict]) -> tuple[dict, str]:
        # ... (The main execute logic is unchanged)
        print(f"\n--- ANALYSIS AGENT ---")
        print(f"  > Analyzing {len(articles)} articles...")
        processed_articles = []
        skipped_count = 0
        total_to_process = len(
            articles) - sum(1 for article in articles if is_url_processed(article.get('url', '')))

        for article in articles:
            if is_url_processed(article.get('url')):
                continue
            if not article.get('title') or "[Removed]" in article.get('title'):
                skipped_count += 1
                continue
            try:
                clean_description = self._sanitize_description(
                    article.get('description', ''))
                category = self._categorize(article['title'])
                summary = self._summarize(article['title'], clean_description)
                if category and summary:
                    processed_articles.append({'title': article['title'], 'url': article['url'], 'source': article['source']['name'], 'published_at': dateparser.parse(
                        article['publishedAt']).strftime('%b %d, %Y'), 'category': category, 'summary': summary})
                    add_url_to_db(article['url'])
                else:
                    skipped_count += 1
            except Exception as e:
                skipped_count += 1
                print(
                    f"  > Skipping article '{article['title']}' due to a critical error: {e}")

        categorized_content = {category: []
                               for category in self.config['categories']}
        for p_article in processed_articles:
            categorized_content[p_article['category']].append(p_article)

        explanation = f"Analysis Agent received {total_to_process} new articles to process. It successfully analyzed and enriched {len(processed_articles)} of them. {skipped_count} articles were skipped."
        print(f"  > {explanation}")
        return categorized_content, explanation

    def _sanitize_description(self, raw_html: str) -> str:
        # ... (This method is unchanged)
        if not raw_html:
            return ''
        soup = BeautifulSoup(raw_html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def _categorize(self, title: str) -> str:
        prompt = f"Categorize the following article title... (your full prompt)"
        # Pass the tracer config to the LLM call
        response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                            {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"}, config=self.tracer_config)
        category = json.loads(response.choices[0].message.content).get(
            "category", "Other")
        if category not in self.config['categories']:
            category = "Other"
        return category

    def _summarize(self, title: str, description: str) -> str:
        prompt = f"Write a concise, 3-sentence summary... (your full prompt)"
        # Pass the tracer config to the LLM call
        response = self.groq_client.chat.completions.create(model=self.fast_model, messages=[
                                                            {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"}, config=self.tracer_config)
        return json.loads(response.choices[0].message.content).get("summary")
