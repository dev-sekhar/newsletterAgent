# main.py

import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import our new, stateful tools
from tools.newsletter_tools import create_newsletter_draft, review_newsletter_draft, publish_final_newsletter

def main():
    load_dotenv()
    print("--- Initializing Master Reasoning Agent ---")

    llm = ChatGroq(model_name="llama3-70b-8192", temperature=0, api_key=os.getenv("GROQ_API_KEY"))

    tools = [
        create_newsletter_draft,
        review_newsletter_draft,
        publish_final_newsletter
    ]

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

    print("\n--- Agent Initialized. Giving it the primary goal. ---\n")

    keyword = os.getenv("KEYWORD_INPUT", "Venture Capital")
    goal = f"Create, stringently review, and then publish this week's newsletter for the topic '{keyword}'. You must use the review tool before publishing. Do not publish a draft that is rejected."

    agent_executor.invoke({"input": goal})

if __name__ == "__main__":
    main()