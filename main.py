# main.py

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import our new, smarter set of tools
from tools.newsletter_tools import (
    generate_search_subtopics, # NEW
    create_initial_draft,
    review_draft_for_relevance_and_quality,
    publish_approved_newsletter
)

def main():
    load_dotenv()
    print("--- Initializing Master Reasoning Agent ---")

    llm = ChatGroq(model_name="llama3-70b-8192", temperature=0, api_key=os.getenv("GROQ_API_KEY"))

    # The agent's complete toolbox
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
    
    # The final, most advanced goal prompt
    goal = f"""
    Your goal is to create and publish a high-quality weekly newsletter for the main topic '{keyword}'.

    To ensure high relevance, you must follow this specific strategy:
    1.  First, use the `generate_search_subtopics` tool to brainstorm a list of specific search queries related to '{keyword}'.
    2.  Next, use the `create_initial_draft` tool, passing it the list of sub-topics you just generated.
    3.  Once the draft is created, you MUST use the `review_draft_for_relevance_and_quality` tool to perform a quality check.
    4.  If the review decision is 'approve', publish it using `publish_approved_newsletter`.
    5.  If the review decision is 'reject', your job is to STOP and report the reason for the rejection as your final answer. Do not retry or revise.
    """

    agent_executor.invoke({"input": goal})

if __name__ == "__main__":
    main()