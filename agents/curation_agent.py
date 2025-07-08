# agents/curation_agent.py

import groq
import json
import time


class CurationAgent:
    def __init__(self, config):
        self.config = config
        self.groq_client = groq.Groq(api_key=config['groq_api_key'])
        self.smart_model = "llama3-70b-8192"  # Use a smart model for judgment calls
        self.fast_model = "llama3-8b-8192"   # Use a fast model for simple yes/no

    def execute(self, analyzed_content: dict) -> tuple[dict, list, str]:
        print(f"\n--- CURATION AGENT ---")

        all_articles_list = [article for category_list in analyzed_content.values(
        ) for article in category_list]
        initial_article_count = len(all_articles_list)

        if not all_articles_list:
            return {}, [], "Curation skipped: No analyzed articles provided."

        all_sources = {article['source'] for article in all_articles_list}

        # --- NEW: ONE-BY-ONE REPUTATION CHECK ---
        reputable_sources = self._get_reputable_sources_iteratively(
            list(all_sources))

        # The fallback is now built into the iterative method, so we can trust its output.
        # If it returns empty, it truly found no reputable sources.
        if not reputable_sources:
            # This is a genuine case where the AI found nothing good, which is valuable information.
            explanation = f"Curation Agent reviewed {len(all_sources)} sources and found none to be reputable enough for the newsletter."
            print(f"  > {explanation}")
            return {}, all_articles_list, explanation

        # --- The rest of the logic remains the same ---

        # Partition articles into approved and rejected based on source
        source_approved_articles = []
        source_rejected_articles = []
        for article in all_articles_list:
            if article['source'] in reputable_sources:
                source_approved_articles.append(article)
            else:
                source_rejected_articles.append(article)

        # Apply diversity limit on the source-approved articles
        final_approved_content = {category: []
                                  for category in self.config['categories']}
        final_approved_urls = set()

        for article in source_approved_articles:
            category = article['category']
            if len(final_approved_content[category]) < self.config['max_articles_per_category']:
                final_approved_content[category].append(article)
                final_approved_urls.add(article['url'])

        diversity_rejected_articles = [
            article for article in source_approved_articles if article['url'] not in final_approved_urls
        ]

        final_rejected_list = source_rejected_articles + diversity_rejected_articles
        total_curated_articles = len(final_approved_urls)

        explanation = (
            f"Curation Agent reviewed {len(all_sources)} sources and approved {len(reputable_sources)}. "
            f"After applying diversity rules, {total_curated_articles} articles were selected for your review."
        )
        print(f"  > {explanation}")

        return final_approved_content, final_rejected_list, explanation

    def _get_reputable_sources_iteratively(self, sources: list) -> set:
        """
        Checks each source individually for reputation. More reliable than a single large prompt.
        """
        print(
            f"  > Vetting {len(sources)} sources for reputation one-by-one...")
        approved_sources = set()
        for source in sources:
            # To avoid hitting API rate limits too quickly
            time.sleep(1)

            prompt = f"""
            You are a news editor. Is the source named "{source}" a reputable, well-known news outlet for topics on technology or business?
            Do not consider personal blogs, press release websites, or unknown entities as reputable.
            Return a single JSON object with one key, "decision", which must be "yes" or "no".
            Example: {{"decision": "yes"}}
            """
            try:
                response = self.groq_client.chat.completions.create(
                    model=self.fast_model,  # Use the fast model for this simple task
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
                if result.get("decision") == "yes":
                    print(f"    - Approving: {source}")
                    approved_sources.add(source)
                else:
                    print(f"    - Rejecting: {source}")
            except Exception as e:
                print(
                    f"    - Error vetting source {source}: {e}. Rejecting by default.")

        print(
            f"  > Iterative vetting complete. Approved {len(approved_sources)} sources.")
        return approved_sources
