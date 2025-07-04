from jinja2 import Environment, FileSystemLoader
from datetime import datetime

class NewsletterAssemblerAgent:
    def __init__(self, template_folder, template_name):
        self.env = Environment(loader=FileSystemLoader(template_folder))
        self.template = self.env.get_template(template_name)

    def execute(self, classified_content, keyword):
        print("AGENT 4: Newsletter Assembler - Generating markdown...")
        newsletter_content = self.template.render(
            keyword=keyword,
            date=datetime.now().strftime('%B %d, %Y'),
            classified_articles=classified_content
        )
        print("  > Markdown content assembled successfully.")
        return newsletter_content
