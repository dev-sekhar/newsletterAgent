import requests
from datetime import datetime, timedelta
from collections import Counter

class SourceIdentifierAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.news_api_endpoint = "https://newsapi.org/v2/everything"

    def execute(self, keyword, candidate_source_count):
        print("AGENT 1: Source Identifier - Fetching all articles...")
        all_articles = self._fetch_articles(keyword)
        if not all_articles:
            print("  > No articles found from the API.")
            return []

        print(f"  > Found {len(all_articles)} total articles. Identifying candidate sources...")
        source_counts = Counter(
            article['source']['name'] 
            for article in all_articles if article.get('source') and article['source'].get('name')
        )
        
        candidate_sources = [source[0] for source in source_counts.most_common(candidate_source_count)]
        
        print(f"  > Identified {len(candidate_sources)} candidate sources for review.")
        return all_articles, candidate_sources

    def _fetch_articles(self, keyword):
        since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        params = {'q': keyword, 'from': since_date, 'sortBy': 'publishedAt', 'apiKey': self.api_key, 'language': 'en'}
        response = requests.get(self.news_api_endpoint, params=params)
        response.raise_for_status()
        return response.json().get('articles', []) 
