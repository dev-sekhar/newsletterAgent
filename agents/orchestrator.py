import groq
from database import setup_database
from .source_identifier_agent import SourceIdentifierAgent
from .reputation_agent import ReputationAgent
from .content_creation_agent import ContentCreationAgent
from .newsletter_assembler_agent import NewsletterAssemblerAgent
from .publisher_agent import PublisherAgent

class Orchestrator:
    def __init__(self, config):
        print("ORCHESTRATOR: Initializing all agents...")
        groq_client = groq.Groq(api_key=config['groq_api_key'])
        
        self.config = config
        self.source_identifier = SourceIdentifierAgent(api_key=config['news_api_key'])
        self.reputation_filter = ReputationAgent(groq_client=groq_client, model_name=config['model_name'])
        self.content_creator = ContentCreationAgent(groq_client=groq_client, model_name=config['model_name'], categories=config['categories'])
        self.assembler = NewsletterAssemblerAgent(template_folder='templates', template_name='newsletter_template.md')
        self.publisher = PublisherAgent()

    def run(self, keyword):
        print(f"\nORCHESTRATOR: Starting workflow for keyword: '{keyword}'")
        try:
            # Setup
            setup_database()

            # Agent 1: Identify Sources
            all_articles, candidate_sources = self.source_identifier.execute(keyword, self.config['candidate_source_count'])
            if not all_articles:
                print("ORCHESTRATOR: Workflow halted. No articles found.")
                return

            # Agent 2: Filter by Reputation
            reputable_articles = self.reputation_filter.execute(all_articles, candidate_sources)

            # Agent 3: Create Content
            classified_content, new_articles_count = self.content_creator.execute(reputable_articles)
            if new_articles_count == 0:
                print("ORCHESTRATOR: Workflow halted. No new articles to publish.")
                return

            # Agent 4: Assemble Newsletter
            newsletter_markdown = self.assembler.execute(classified_content, keyword)

            # Agent 5: Publish
            self.publisher.execute(newsletter_markdown)
            
            print("\nORCHESTRATOR: Workflow completed successfully! ✅")

        except Exception as e:
            print(f"\nORCHESTRATOR: A critical error occurred in the workflow: {e}")
