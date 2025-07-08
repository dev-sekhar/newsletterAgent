# agents/curation_agent.py

import groq
import json


class CurationAgent:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.smart_model = "llama3-70b-8192"

    def execute(self, analyzed_content: dict) -> tuple[dict, dict]:
        print(f"\n--- CURATION AGENT ---")

        # Flatten all articles into a single list for easier processing
        all_articles_list = [article for category_list in analyzed_content.values(
        ) for article in category_list]

        if not all_articles_list:
            return {}, {}

        all_sources = {article['source'] for article in all_articles_list}
        reputable_sources = self._get_reputable_sources(list(all_sources))

        approved_articles = []
        rejected_articles = []

        for article in all_articles_list:
            # Main curation logic: is the source reputable?
            if article['source'] in reputable_sources:
                approved_articles.append(article)
            else:
                rejected_articles.append(article)

        # Further curate the approved list to ensure diversity
        final_approved_content = {}
        # Use a temporary list to track which approved articles make the final cut
        final_approved_ids = set()

        for category in self.config['categories']:
            # Get approved articles for the current category
            category_articles = [
                a for a in approved_articles if a['category'] == category]
            # Limit the number
            final_for_category = category_articles[:
                                                   self.config['max_articles_per_category']]

            if final_for_category:
                final_approved_content[category] = final_for_category
                for article in final_for_category:
                    final_approved_ids.add(article['url'])

        # Any approved article not in the final limited list is moved to rejected
        for article in approved_articles:
            if article['url'] not in final_approved_ids:
                rejected_articles.append(article)

        print(
            f"  > Curation complete. Proposed: {len(final_approved_ids)} articles. Rejected: {len(rejected_articles)} articles.")
        return final_approved_content, rejected_articles

    def _get_reputable_sources(self, sources: list) -> set:
        # ... (This private method is unchanged)
        print(f"  > Vetting {len(sources)} sources for reputation...")
        prompt = f"""You are a meticulous senior news editor... (your full prompt)"""
        try:
            response = self.groq_client.chat.completions.create(model=self.smart_model, messages=[
                                                                {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            approved = set(json.loads(response.choices[0].message.content).get(
                "approved_sources", []))
            print(f"  > LLM approved {len(approved)} sources.")
            return approved
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Using all sources as fallback.")
            return set(sources)
