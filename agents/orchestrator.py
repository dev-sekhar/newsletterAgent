import groq
from database import setup_database
from .source_identifier_agent import SourceIdentifierAgent
# We are deleting ReputationAgent
from .content_creation_agent import ContentCreationAgent
from .curation_agent import CurationAgent  # <-- NEW
from .newsletter_assembler_agent import NewsletterAssemblerAgent
from .publisher_agent import PublisherAgent


class Orchestrator:
    def __init__(self, config):
        print("ORCHESTRATOR: Initializing all agents...")
        groq_client = groq.Groq(api_key=config['groq_api_key'])

        self.config = config
        self.source_identifier = SourceIdentifierAgent(
            api_key=config['news_api_key'])
        self.content_creator = ContentCreationAgent(
            groq_client=groq_client, model_name=config['model_name'], categories=config['categories'])
        self.curator = CurationAgent(
            groq_client=groq_client, model_name=config['model_name'], max_articles_per_category=config['max_articles_per_category'])
        self.assembler = NewsletterAssemblerAgent(
            template_folder='templates', template_name='newsletter_template.md')
        self.publisher = PublisherAgent()

    def run(self, keyword):
        print(f"\nORCHESTRATOR: Starting workflow for keyword: '{keyword}'")
        try:
            # Setup
            setup_database()

            # Agent 1: Fetch ALL articles
            all_articles, _ = self.source_identifier.execute(
                keyword, 100)  # Count doesn't matter here
            if not all_articles:
                print("ORCHESTRATOR: Workflow halted. No articles found.")
                return

            # Agent 2: Create content for ALL fetched articles
            # This is now the most intensive step
            all_categorized_content, _ = self.content_creator.execute(
                all_articles)

            # Agent 3: Curate the final selection
            final_content, final_article_count = self.curator.execute(
                all_categorized_content)
            if final_article_count == 0:
                print(
                    "ORCHESTRATOR: Workflow halted. No articles passed the curation filters.")
                return

            # Agent 4: Assemble Newsletter from the curated content
            newsletter_markdown = self.assembler.execute(
                final_content, keyword)

            # Agent 5: Publish
            self.publisher.execute(newsletter_markdown)

            print("\nORCHESTRATOR: Workflow completed successfully! ✅")

        except Exception as e:
            print(
                f"\nORCHESTRATOR: A critical error occurred in the workflow: {e}")
