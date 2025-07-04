
import json


class CurationAgent:
    def __init__(self, groq_client, model_name, max_articles_per_category):
        self.client = groq_client
        self.model_name = model_name
        self.max_articles_per_category = max_articles_per_category

    def execute(self, all_categorized_content):
        print("AGENT: Curation - Curating final article selection for diversity and quality...")
        if not any(all_categorized_content.values()):
            print("  > No content to curate.")
            return {}, 0

        # Step 1: Identify all unique sources from the content pool
        all_sources = set()
        for category_articles in all_categorized_content.values():
            for article in category_articles:
                all_sources.add(article['source'])

        # Step 2: Get a list of reputable sources from the LLM
        reputable_sources = self._get_reputable_sources_from_llm(
            list(all_sources))
        reputable_sources_set = set(reputable_sources)
        print(
            f"\n  > Curation will prioritize {len(reputable_sources_set)} reputable sources.")

        # Step 3: Curate the final list
        final_curated_content = {}
        total_curated_articles = 0

        for category, articles in all_categorized_content.items():
            if not articles:
                continue

            # First, filter by reputation
            reputable_articles_in_category = [
                article for article in articles if article['source'] in reputable_sources_set
            ]

            # Second, limit the number of articles per category for diversity
            curated_for_category = reputable_articles_in_category[:self.max_articles_per_category]

            if curated_for_category:
                final_curated_content[category] = curated_for_category
                total_curated_articles += len(curated_for_category)
                print(
                    f"  > Selected {len(curated_for_category)} articles for category '{category}'")

        print(
            f"\n  > Curation complete. Final selection includes {total_curated_articles} articles.")
        return final_curated_content, total_curated_articles

    def _get_reputable_sources_from_llm(self, sources):
        # This is the same logic that was in the old ReputationAgent
        prompt = f"""You are a meticulous senior news editor... (rest of prompt)"""  # Your updated JSON prompt
        try:
            response = self.client.chat.completions.create(model=self.model_name, messages=[
                                                           {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            result = json.loads(response.choices[0].message.content)
            return result.get("approved_sources", [])
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Cannot filter by reputation.")
            return sources  # Fallback: consider all sources reputable if LLM fails
