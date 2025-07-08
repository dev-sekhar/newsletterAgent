# agents/curation_agent.py

import groq
import json


class CurationAgent:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.smart_model = "llama3-70b-8192"

    def execute(self, categorized_content: dict) -> tuple[dict, list, str]:
        print(f"\n--- CURATION AGENT ---")

        all_articles_list = [article for category_list in categorized_content.values(
        ) for article in category_list]
        initial_article_count = len(all_articles_list)

        if not all_articles_list:
            return {}, [], "Curation skipped: No analyzed articles provided."

        all_sources = {article['source'] for article in all_articles_list}
        reputable_sources, justification = self._get_reputable_sources(
            list(all_sources))

        # --- START OF FIX: ADD COMMON SENSE FALLBACK ---
        # If the LLM returns an empty list, it's likely an error or an overly strict judgment.
        # In this case, we fall back to using ALL sources to ensure there's content to review.
        if not reputable_sources:
            print(
                "  > LLM returned no reputable sources. This is unlikely. Using all sources as a fallback.")
            reputable_sources = all_sources
            justification = "LLM failed to provide a valid list of reputable sources; all sources were included for human review."
        # --- END OF FIX ---

        # Partition articles into approved and rejected based on source
        source_approved_articles = []
        source_rejected_articles = []
        for article in all_articles_list:
            if article['source'] in reputable_sources:
                source_approved_articles.append(article)
            else:
                source_rejected_articles.append(article)

        # Now, apply diversity limit on the source-approved articles
        final_approved_content = {category: []
                                  for category in self.config['categories']}
        final_approved_urls = set()

        for article in source_approved_articles:
            category = article['category']
            if len(final_approved_content[category]) < self.config['max_articles_per_category']:
                final_approved_content[category].append(article)
                final_approved_urls.add(article['url'])

        # Articles that were approved by source but not by diversity limit are also rejected
        diversity_rejected_articles = [
            article for article in source_approved_articles if article['url'] not in final_approved_urls
        ]

        final_rejected_list = source_rejected_articles + diversity_rejected_articles
        total_curated_articles = len(final_approved_urls)

        explanation = (
            f"Curation Agent started with {initial_article_count} articles from {len(all_sources)} unique sources. "
            f"LLM Justification for source selection: '{justification}'. "
            f"The final selection was filtered and limited, resulting in {total_curated_articles} articles for approval."
        )
        print(f"  > {explanation}")

        return final_approved_content, final_rejected_list, explanation

    def _get_reputable_sources(self, sources: list) -> tuple[set, str]:
        # This method is already correct and does not need to be changed.
        print(f"  > Vetting {len(sources)} sources for reputation...")
        prompt = f"""You are a meticulous senior news editor... (your full JSON prompt)"""
        try:
            response = self.groq_client.chat.completions.create(model=self.smart_model, messages=[
                                                                {"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
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
