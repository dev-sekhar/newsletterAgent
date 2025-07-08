# agents/orchestrator.py

import os
from database import setup_database

from .research_agent import ResearchAgent
from .analysis_agent import AnalysisAgent
from .curation_agent import CurationAgent
# The Writing Agent is not used in this part of the workflow, so no need to import


class Orchestrator:
    def __init__(self, config):
        print("--- ORCHESTRATOR: Initializing all specialist agents... ---")
        self.config = config
        self.research_agent = ResearchAgent(config)
        self.analysis_agent = AnalysisAgent(config)
        self.curation_agent = CurationAgent(config)

    def run_curation(self, topic: str) -> tuple[dict, list]:
        print(
            f"\n--- ORCHESTRATOR: Starting Curation workflow for topic: '{topic}' ---")
        try:
            db_file = "articles.db"
            if os.path.exists(db_file):
                os.remove(db_file)
            setup_database()

            # Step 1: Research Agent returns a list of articles and an explanation
            article_list, research_exp = self.research_agent.execute(topic)
            if not article_list:
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. Research Agent found no articles. ---")
                return {}, []

            # Step 2: Analysis Agent takes the article list and returns categorized content and an explanation
            analyzed_content, analysis_exp = self.analysis_agent.execute(
                article_list)
            if not any(analyzed_content.values()):
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. Analysis Agent could not process any articles. ---")
                return {}, []

            # --- START OF FIX ---
            # Step 3: Curation Agent now returns THREE values. We must unpack all three.
            final_approved, rejected_list, curation_explanation = self.curation_agent.execute(
                analyzed_content)
            # We don't need to use the explanation string here, but we must receive it.

            if not any(final_approved.values()):
                print(
                    "\n--- ORCHESTRATOR: Workflow halted. No articles passed the curation filters. ---")
                return {}, []

            # Return the two data structures needed to build the review package
            return final_approved, rejected_list
            # --- END OF FIX ---

        except Exception as e:
            print(f"\n--- ORCHESTRATOR: A critical error occurred: {e} ---")
            raise e
