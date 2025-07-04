import json
import dateparser
from database import is_url_processed, add_url_to_db


class ContentCreationAgent:
    def __init__(self, groq_client, model_name, categories):
        self.client = groq_client
        self.model_name = model_name
        self.categories = categories

    def execute(self, articles):
        print("AGENT 3: Content Creation - Classifying and summarizing articles...")
        classified_content = {category: [] for category in self.categories}
        new_articles_found = 0

        for article in articles:
            if is_url_processed(article['url']):
                continue
            if not article.get('title') or "[Removed]" in article.get('title'):
                continue

            analysis = self._classify_and_summarize(article)
            if analysis:
                new_articles_found += 1
                classified_content[analysis['category']].append({
                    'title': article['title'],
                    'url': article['url'],
                    'source': article['source']['name'],
                    'published_at': dateparser.parse(article['publishedAt']).strftime('%b %d, %Y'),
                    'summary': analysis['summary']
                })
                add_url_to_db(article['url'])

        print(
            f"  > Processed and created content for {new_articles_found} new articles.")
        return classified_content, new_articles_found

    def _classify_and_summarize(self, article):
        prompt = f"""
        You are an expert tech news analyst. Your task is to classify and summarize an article.

        Article Title: "{article['title']}"
        Article Description: "{article.get('description', 'No description available.')}"

        First, classify the article into ONE of the following categories: {', '.join(self.categories)}.
        Second, write a concise 3-sentence summary of the article.

        Provide your response as a valid JSON object with two keys: "category" and "summary".
        Do not include any other text or explanation.
        Example:
        {{
          "category": "DeFi",
          "summary": "This is a three-sentence summary of the article."
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            if result.get("category") not in self.categories:
                result["category"] = "Other"
            return result
        except Exception as e:
            print(
                f"  > Content creation failed for article '{article['title']}': {e}")
            return None
