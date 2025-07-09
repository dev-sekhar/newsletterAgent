# agents/research_agent.py

import os
import requests
import groq
import json
from datetime import datetime, timedelta


class ResearchAgent:
    def __init__(self, config):
        self.config = config
        self.news_api_key = config['news_api_key']
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.smart_model = "llama3-70b-8192"
        # Store the tracer config from the main config object
        self.tracer_config = config.get('tracer_config', {})

    def execute(self, topic: str) -> tuple[list[dict], str]:
        print(f"\n--- RESEARCH AGENT ---")
        sub_topics = self._generate_subtopics(topic)

        all_articles = []
        for sub_topic in sub_topics:
            all_articles.extend(self._fetch_articles(sub_topic))

        cleaned_articles = []
        seen_urls = set()
        for article in all_articles:
            if isinstance(article, dict) and article.get('url'):
                if article['url'] not in seen_urls:
                    cleaned_articles.append(article)
                    seen_urls.add(article['url'])

        explanation = (
            f"Initial research for topic '{topic}' was expanded to {len(sub_topics)} specific sub-topics: {sub_topics}. "
            f"A total of {len(cleaned_articles)} unique articles were fetched."
        )
        print(f"  > {explanation}")

        return cleaned_articles, explanation

    def _generate_subtopics(self, topic: str) -> list[str]:
        print(f"  > Generating search sub-topics for '{topic}'...")
        prompt = f"""You are a research analyst... (your full prompt)"""
        try:
            # Pass the tracer config to the LLM call
            response = self.groq_client.chat.completions.create(
                model=self.smart_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"},
                config=self.tracer_config
            )
            result = json.loads(response.choices[0].message.content)
            sub_topics = result.get("sub_topics", [])
            print(f"  > Generated sub-topics: {sub_topics}")
            return sub_topics
        except Exception as e:
            print(
                f"  > Failed to generate sub-topics: {e}. Falling back to main topic.")
            return [topic]

    def _fetch_articles(self, keyword: str) -> list:
        # ... (This method makes no LLM calls, so it is unchanged)
        print(f"  > Fetching articles for: '{keyword}'...")
        since_date = (datetime.now() - timedelta(days=7)
                      ).strftime('%Y-%m-%dT%H:%M:%S')
        params = {'q': keyword, 'from': since_date, 'sortBy': 'publishedAt',
                  'apiKey': self.news_api_key, 'language': 'en'}
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('articles', []) if isinstance(data, dict) else []
        except Exception as e:
            print(
                f"    > Could not fetch articles for keyword '{keyword}'. Error: {e}")
            return []
