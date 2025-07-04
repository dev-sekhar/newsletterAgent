import json


class ReputationAgent:
    def __init__(self, groq_client, model_name):
        self.client = groq_client
        self.model_name = model_name

    def execute(self, all_articles, candidate_sources):
        print("AGENT 2: Reputation Filter - Consulting LLM...")
        if not candidate_sources:
            print("  > No candidate sources to vet. Passing all articles.")
            return all_articles

        approved_sources = self._get_reputable_sources_from_llm(
            candidate_sources)
        approved_sources_set = set(approved_sources)

        filtered_articles = [
            article for article in all_articles
            if article.get('source') and article['source'].get('name') in approved_sources_set
        ]
        print(
            f"  > Filtered down to {len(filtered_articles)} articles from LLM-approved sources.")
        return filtered_articles

    def _get_reputable_sources_from_llm(self, sources):
        prompt = f"""
        You are a meticulous senior news editor. Review the following list of news sources:
        {sources}
        Your task is to identify and return only the sources that are well-known, reputable, and high-quality for news on business and technology. Exclude blogs, press release aggregators, and unknown entities.
        
        Return a valid JSON object with a single key "approved_sources" which is a list of strings of the sources you approve.
        Example: {{"approved_sources": ["Reuters", "TechCrunch", "Bloomberg"]}}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            approved_list = result.get("approved_sources", [])
            print(f"  > LLM approved {len(approved_list)} sources.")
            return approved_list
        except Exception as e:
            print(
                f"  > LLM reputation check failed: {e}. Falling back to all candidates.")
            return sources
