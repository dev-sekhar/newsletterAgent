# run_part1_drafting_agent.py

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import our new, smarter set of tools
from tools.newsletter_tools import (
    generate_search_subtopics,
    create_initial_draft,
    review_draft_for_relevance_and_quality,
    publish_approved_newsletter # Agent needs to know about it, even if it doesn't call it
)

def main():
    load_dotenv()
    print("--- Initializing Master Reasoning Agent for Drafting ---")

    llm = ChatGroq(model_name="llama3-70b-8192", temperature=0, api_key=os.getenv("GROQ_API_KEY"))

    tools = [
        generate_search_subtopics,
        create_initial_draft,
        review_draft_for_relevance_and_quality,
        publish_approved_newsletter,
    ]

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, max_iterations=15)

    print("\n--- Agent Initialized. Giving it the primary goal. ---\n")

    keyword = os.getenv("KEYWORD_INPUT", "Artificial Intelligence")
    
    goal = f"""
    Your goal is to create a high-quality draft of a weekly newsletter for the topic '{keyword}'.

    The process is sequential and strict:
    1.  First, use the `generate_search_subtopics` tool to brainstorm specific search queries.
    2.  Next, use the `create_initial_draft` tool with the generated list of sub-topics.
    3.  After the draft is created, you MUST use the `review_draft_for_relevance_and_quality` tool.
    4.  Your final output should be the result of the review. You do not need to publish anything. Your job is complete after the review step.
    """

    agent_executor.invoke({"input": goal})

if __name__ == "__main__":
    main()