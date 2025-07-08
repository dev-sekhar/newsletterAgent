# agents/orchestrator.py

import os
from database import setup_database
from .research_agent import ResearchAgent
from .analysis_agent import AnalysisAgent
from .curation_agent import CurationAgent
# Writing agent is no longer needed here

class Orchestrator:
    def __init__(self, config):
        print("--- ORCHESTRATOR: Initializing specialist agents... ---")
        self.config = config
        self.research_agent = ResearchAgent(config)
        self.analysis_agent = AnalysisAgent(config)
        self.curation_agent = CurationAgent(config)

    def run_curation(self, topic: str) -> tuple[dict, list]:
        print(f"\n--- ORCHESTRATOR: Starting Curation workflow for topic: '{topic}' ---")
        try:
            db_file = "articles.db"
            if os.path.exists(db_file):
                os.remove(db_file)
            setup_database()

            articles = self.research_agent.execute(topic)
            if not articles:
                return {}, []

            analyzed_content = self.analysis_agent.execute(articles)
            if not any(analyzed_content.values()):
                return {}, []
            
            approved_content, rejected_content = self.curation_agent.execute(analyzed_content)
            return approved_content, rejected_content

        except Exception as e:
            print(f"\n--- ORCHESTRATOR: A critical error occurred: {e} ---")
            raise e