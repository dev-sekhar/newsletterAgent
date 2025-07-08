# agents/orchestrator.py

import os
from database import setup_database

from .research_agent import ResearchAgent
from .analysis_agent import AnalysisAgent
from .curation_agent import CurationAgent
from .writing_agent import WritingAgent


class Orchestrator:
    def __init__(self, config):
        print("--- ORCHESTRATOR: Initializing all specialist agents... ---")
        self.config = config
        self.research_agent = ResearchAgent(config)
        self.analysis_agent = AnalysisAgent(config)
        self.curation_agent = CurationAgent(config)
        self.writing_agent = WritingAgent(config)

    def run_curation(self, topic: str) -> tuple[dict, list]:
        print(
            f"\n--- ORCHESTRATOR: Starting Curation workflow for topic: '{topic}' ---")
        try:
            db_file = "articles.db"
            if os.path.exists(db_file):
                os.remove(db_file)
            setup_database()

            # --- START OF FIX ---
            # Correctly unpack the tuple returned by the research agent
            article_list, research_exp = self.research_agent.execute(topic)
            if not article_list:
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. Research Agent found no articles. ---")
                return {}, []

            # Pass ONLY the list of articles to the analysis agent
            analyzed_content, analysis_exp = self.analysis_agent.execute(
                article_list)
            if not any(analyzed_content.values()):
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. Analysis Agent could not process any articles. ---")
                return {}, []

            # Pass ONLY the categorized dictionary to the curation agent
            approved_content, curation_exp = self.curation_agent.execute(
                analyzed_content)

            # This Orchestrator's job is to create the review package, not call the writer.
            # We return the data needed for the review package.
            # The 'rejected_articles' logic needs to be in the Curation agent. Let's ensure it is.

            # The CurationAgent needs to return the final approved content and the rejected articles.
            # Let's adjust the Curation agent's return value and this orchestrator's handling.

            # The Curation agent will return (final_approved_dict, rejected_list, explanation_string)
            final_approved, rejected_list, curation_explanation = self.curation_agent.execute(
                analyzed_content)

            if not any(final_approved.values()):
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. No articles passed the curation filters. ---")
                return {}, []

            # We don't need the explanations here, just the data for the package
            return final_approved, rejected_list
            # --- END OF FIX ---

        except Exception as e:
            print(f"\n--- ORCHESTRATOR: A critical error occurred: {e} ---")
            raise e
