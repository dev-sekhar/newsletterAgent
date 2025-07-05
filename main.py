# main.py

import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import hub

# Import our new, powerful tool
from tools.newsletter_tools import run_newsletter_creation_pipeline


def main():
    """
    This is the main entry point for the AGENTIC Newsletter Workflow.
    It creates a Master Reasoning Agent and gives it a high-level goal.
    """
    load_dotenv()

    print("--- Initializing Master Reasoning Agent ---")

    # 1. The LLM (The "Brain" of the agent)
    # We use a powerful model for reasoning tasks.
    llm = ChatGroq(
        model_name="llama3-70b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    # 2. The Toolbox
    # The Master Agent has access to all functions decorated with @tool.
    tools = [run_newsletter_creation_pipeline]

    # 3. The Prompt (The Agent's "Personality" or "Operating System")
    # We use a standard "ReAct" (Reason+Act) prompt from the LangChain Hub.
    # This prompt tells the agent how to think, what tools it has, and how to use them.
    prompt = hub.pull("hwchase17/react")

    # 4. The Agent
    # We bind the LLM, tools, and prompt together to create the agent.
    agent = create_react_agent(llm, tools, prompt)

    # 5. The Agent Executor (The "Runtime" for the agent)
    # This is what actually runs the agent's thought process and executes its chosen tools.
    # verbose=True lets us see the agent's thoughts in real-time.
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    print("\n--- Agent Initialized. Giving it the primary goal. ---\n")

    # Get the keyword from GitHub Actions or use a default
    keyword = os.getenv("KEYWORD_INPUT", "Quantum Computing")

    # This is the high-level goal we give to our agent.
    goal = f"Create and publish this week's newsletter for the topic '{keyword}'."

    # Invoke the agent and let it figure out how to achieve the goal.
    agent_executor.invoke({"input": goal})


if __name__ == "__main__":
    main()
