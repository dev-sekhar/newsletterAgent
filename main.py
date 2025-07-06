# main.py

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import our new, clearer set of tools
from tools.newsletter_tools import (
    create_initial_draft,
    review_draft_for_relevance_and_quality,
    publish_approved_newsletter
)


def main():
    """
    This is the main entry point for the AGENTIC Newsletter Workflow.
    It creates a Master Reasoning Agent and gives it a high-level, explicit goal.
    """
    load_dotenv()
    print("--- Initializing Master Reasoning Agent ---")

    # The LLM (The "Brain" of the agent)
    llm = ChatGroq(
        model_name="llama3-70b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    # The agent's toolbox, with clear, unambiguous tools.
    tools = [
        create_initial_draft,
        review_draft_for_relevance_and_quality,
        publish_approved_newsletter,
    ]

    # The Agent's "Operating System" or personality.
    prompt = hub.pull("hwchase17/react")

    # Binding the components together to create the agent.
    agent = create_react_agent(llm, tools, prompt)

    # The Agent Executor runs the agent's thought process.
    # max_iterations prevents any potential for runaway loops.
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )

    print("\n--- Agent Initialized. Giving it the primary goal. ---\n")

    # Get the topic from GitHub Actions input or use a default
    keyword = os.getenv("KEYWORD_INPUT", "Blockchain")

    # A very clear, step-by-step goal for the agent to prevent confusion.
    goal = f"""
    Your goal is to create and publish a high-quality weekly newsletter for the topic '{keyword}'.

    The process is sequential and strict:
    1.  You MUST start by using the `create_initial_draft` tool with the keyword.
    2.  After a draft is created, you MUST use the `review_draft_for_relevance_and_quality` tool.
    3.  Examine the output of the review tool.
    4.  If and ONLY IF the review decision is 'approve', you MUST use the `publish_approved_newsletter` tool to finish.
    5.  If the review decision is 'reject', your job is to STOP and report the reason for the rejection as your final answer. Do not try to revise or retry.
    """

    # Invoke the agent to start the process
    agent_executor.invoke({"input": goal})


if __name__ == "__main__":
    main()
