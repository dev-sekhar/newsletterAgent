# agents/writing_agent.py

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


class WritingAgent:
    def __init__(self, config):
        self.config = config

    def execute(self, curated_content: dict, primary_keyword: str, explanations: list[str]):
        print(f"\n--- WRITING AGENT ---")
        if not any(curated_content.values()):
            print("  > No content to write. Halting.")
            return

        markdown = self._assemble_newsletter(
            curated_content, primary_keyword, explanations)
        self._publish_newsletter(markdown)

    def _assemble_newsletter(self, content: dict, keyword: str, explanations: list[str]) -> str:
        print("  > Assembling newsletter markdown with explanations...")
        env = Environment(loader=FileSystemLoader(
            self.config['template_folder']))
        template = env.get_template(self.config['template_name'])
        return template.render(
            keyword=keyword,
            date=datetime.now().strftime('%B %d, %Y'),
            classified_articles=content,
            explanations=explanations  # Pass explanations to the template
        )

    def _publish_newsletter(self, markdown: str) -> str:
        print("  > Publishing newsletter...")
        base_filename = f"newsletter_{datetime.now().strftime('%Y-%m-%d')}"
        output_filename = f"{base_filename}.md"
        version = 2
        while os.path.exists(output_filename):
            output_filename = f"{base_filename}_v{version}.md"
            version += 1

        print(f"  > Saving to file: '{output_filename}'.")
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return output_filename
