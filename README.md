# Autonomous AI Newsletter Agent

This project is an advanced, multi-agent system designed to autonomously research, curate, and draft a weekly topical newsletter. It leverages Large Language Models (LLMs) for content generation and analysis, and is built with a "Human-in-the-Loop" (HITL) architecture, ensuring that a human editor has the final say before publication.

What began as a simple script evolved into a sophisticated AI collaborator, showcasing modern agentic design patterns, automated workflows, and the power of combining AI judgment with human oversight.

## Key Features

- **Multi-Agent Architecture:** The system is not a single script, but a team of specialized AI agents, each with a distinct responsibility (Research, Analysis, Curation, Writing).
- **Intelligent Content Sourcing:** The AI first brainstorms a list of specific, high-relevance sub-topics before fetching articles, dramatically improving the quality of the source material.
- **AI-Powered Curation:** An editor agent vets all sources for reputability and filters articles for quality and diversity, reducing dozens of articles to a manageable, high-quality selection.
- **Human-in-the-Loop (HITL):** The system's primary output is a `review_package.json` file. This allows a human editor to review the AI's selections, approve, reject, or modify the list before publishing.
- **Fully Automated with GitHub Actions:** The entire workflow is managed by two distinct GitHub Actions, one for automated draft creation and one for manual, on-demand publishing.
- **Explainability & Observability:** Integrated with **LangSmith** for detailed tracing, providing full transparency into each agent's decision-making process.

## How It Works: The Two-Part Workflow

The system is intentionally split into two parts to facilitate human review.

### Part 1: AI Draft Creation

1.  **Trigger:** This workflow runs automatically on a schedule (e.g., every Friday) or can be triggered manually.
2.  **Research:** The `ResearchAgent` takes a broad topic (e.g., "Artificial Intelligence") and uses a powerful LLM to generate a list of specific sub-topics (e.g., "AI-powered healthcare diagnosis," "Ethical considerations of autonomous vehicles").
3.  **Fetch:** It then fetches articles for all these sub-topics from the NewsAPI.
4.  **Analysis:** The `AnalysisAgent` processes each unique article, sanitizing any HTML, categorizing it, and generating a concise summary. All processed articles are temporarily stored in a local SQLite database to prevent re-processing.
5.  **Curation:** The `CurationAgent` reviews all processed articles. It uses an LLM to judge the reputability of each news source and then selects a balanced, diverse list of the best articles.
6.  **Output:** The workflow generates a `review_package.json` file containing the AI's recommended "approved" articles and a list of all "rejected" articles. This file is then committed back to the repository.

### Part 2: Human Review & Publishing

1.  **Human Review:** The project owner (the "Editor-in-Chief") receives a notification that the `review_package.json` has been updated. They can edit this file directly in GitHub, moving articles between the `approved_articles` and `rejected_articles` lists to give their final editorial approval.
2.  **Trigger:** Once satisfied, the editor manually triggers the "Publish" workflow from the GitHub Actions tab.
3.  **Publishing:** The `WritingAgent` reads the final, human-approved list from `review_package.json`, renders it using a Jinja2 template, and saves the final `newsletter_YYYY-MM-DD.md` file.
4.  **Commit:** The final newsletter is committed to the repository.

## Technology Stack

- **Language:** Python 3.10
- **AI/LLMs:**
  - **Groq API:** For high-speed access to open-source LLMs.
  - **Llama 3 (8B & 70B):** Used strategically for simple and complex reasoning tasks.
- **Core AI Framework:**
  - **LangChain:** While we evolved past the `AgentExecutor`, the core `langchain-groq` and `langchain-core` libraries are still used for interacting with the LLM.
- **Automation:**
  - **GitHub Actions:** For scheduling, execution, and CI/CD.
- **Data & Storage:**
  - **NewsAPI:** For fetching news articles.
  - **SQLite:** For tracking processed article URLs.
  - **Jinja2:** For newsletter templating.
  - **BeautifulSoup:** For HTML sanitation of article descriptions.
- **Observability:**
  - **LangSmith:** For detailed tracing and debugging of the agent's internal processes.

## How to Run This Project

### 1. Prerequisites

- A GitHub repository cloned to your local machine.
- Python 3.10+ and `pip` installed.
- API keys for **NewsAPI** and **Groq**.
- (Optional but Recommended) An API key for **LangSmith**.

### 2. Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/dev-sekhar/newsletterAgent.git
    cd newsletterAgent
    ```
2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set Up Environment Variables:**
    - **GitHub Secrets:** For the automated workflows, add your API keys to your repository's secrets under `Settings > Secrets and variables > Actions`. Required secrets:
      - `NEWS_API_KEY`
      - `GROQ_API_KEY`
      - `LANGCHAIN_TRACING_V2` (set to `true`)
      - `LANGCHAIN_API_KEY`
      - `LANGCHAIN_PROJECT` (e.g., `Newsletter Production`)
    - **Local `.env` File:** For local testing, create a `.env` file in the root directory and add your keys:
      ```
      NEWS_API_KEY="your_key"
      GROQ_API_KEY="your_key"
      LANGCHAIN_TRACING_V2="true"
      LANGCHAIN_API_KEY="your_key"
      LANGCHAIN_PROJECT="Newsletter - Local Test"
      ```

### 3. Manual Workflow Execution

1.  **Run the Draft Creation:** Go to the **Actions** tab in your GitHub repository, select **"1: Create Newsletter Draft for Review"**, and run the workflow. You can provide a custom topic.
2.  **Review the Package:** Once the workflow completes, pull the latest changes to your local machine or edit `review_package.json` directly on GitHub. Make your editorial changes and commit them.
3.  **Run the Publishing Workflow:** Go back to the Actions tab, select **"2: Publish Approved Newsletter"**, and run the workflow. This will use your edited JSON file to generate the final newsletter.```
