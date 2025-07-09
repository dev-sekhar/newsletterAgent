# run_part2_publish_script.py

import os
import json
from dotenv import load_dotenv
from agents.writing_agent import WritingAgent


def publish_from_review():
    """
    This is a simple, non-agentic script that reads the final, human-edited
    review_package.json and publishes the newsletter.
    """
    load_dotenv()
    print("--- WORKFLOW PART 2: FINAL PUBLISHING SCRIPT ---")

    review_package_filename = "review_package.json"
    if not os.path.exists(review_package_filename):
        print(
            f"Error: Review package '{review_package_filename}' not found. Cannot publish.")
        # Exit gracefully so the GitHub Action doesn't fail
        return

    with open(review_package_filename, 'r', encoding='utf-8') as f:
        review_data = json.load(f)

    # The approved_articles are already grouped by category in the JSON
    final_articles_to_publish = review_data.get("approved_articles", {})
    topic = review_data.get("topic", "Newsletter")

    if not any(final_articles_to_publish.values()):
        print("The 'approved_articles' section is empty. Nothing to publish.")
        return

    config = {
        'template_folder': 'templates',
        'template_name': 'newsletter_template.md'
    }

    # We don't need the full orchestrator, just the simple Writing Agent
    writing_agent = WritingAgent(config)

    # The writing agent doesn't need explanations in this simple script
    writing_agent.execute(final_articles_to_publish, topic, explanations=[])

    print(f"\n--- Newsletter published successfully based on your final review. ---")


if __name__ == "__main__":
    publish_from_review()
