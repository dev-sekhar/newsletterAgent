# agents/curation_agent.py

import groq
import json


class CurationAgent:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.smart_model = "llama3-70b-8192"
        # Store the tracer config from the main config object
        self.tracer_config = config.get('tracer_config', {})

    def execute(self, categorized_content: dict) -> tuple[dict, list, str]:
        # ... (The main execute logic is unchanged)
        print(f"\n--- CURATION AGENT ---")
        all_articles_list = [article for category_list in categorized_content.values(
        ) for article in category_list]
        initial_article_count = len(all_articles_list)
        if not all_articles_list:
            return {}, [], "Curation skipped: No analyzed articles provided."
        all_sources = {article['source'] for article in all_articles_list}
        reputable_sources, justification = self._get_reputable_sources(
            list(all_sources))
        if not reputable_sources:
            justification = "LLM failed to provide a valid list of reputable sources; all sources were included for human review."
            reputable_sources = all_sources

        source_approved_articles = [
            a for a in all_articles_list if a['source'] in reputable_sources]
        source_rejected_articles = [
            a for a in all_articles_list if a['source'] not in reputable_sources]

        final_approved_content = {category: []
                                  for category in self.config['categories']}
        final_approved_urls = set()
        for article in source_approved_articles:
            category = article['category']
            if len(final_approved_content[category]) < self.config['max_articles_per_category']:
                final_approved_content[category].append(article)
                final_approved_urls.add(article['url'])

        diversity_rejected_articles = [
            a for a in source_approved_articles if a['url'] not in final_approved_urls]
        final_rejected_list = source_rejected_articles + diversity_rejected_articles
        total_curated_articles = len(final_approved_urls)
        explanation = f"Curation Agent reviewed {len(all_sources)} sources. Justification: '{justification}'. After filtering, {total_curated_articles} articles were selected for approval."
        print(f"  > {explanation}")
        return final_approved_content, final_rejected_list, explanation

    def _get_reputable_sources(self, sources: list) -> tuple[set, str]:
        print(f"  > Vetting {len(sources)} sources for reputation...")
        prompt = f"""You are a meticulous senior news editor... (your full prompt)"""
        try:
            # Pass the tracer config to the LLM call
            response = self.groq_client.chat.completions.create(model=self.smart_model, messages=[
                                                                {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"}, config=self.tracer_config)
            result = json.loads(response.choices[0].message.content)
            approved = set(result.get("approved_sources", []))
            justification = result.get(
                "justification", "No justification provided.")
            print(f"  > LLM approved {len(approved)} sources.")
            return approved, justification
        except Exception as e:
            print(
                f"  > Curation LLM check failed: {e}. Using all sources as fallback.")
            return set(sources), "LLM check failed; all sources were included as a fallback."
