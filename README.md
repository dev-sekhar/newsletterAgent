# 📰 AI-Powered Autonomous Newsletter Agent

This project implements a sophisticated, autonomous AI agent designed to create, review, and publish a weekly newsletter on any given topic. It uses a multi-tool, goal-driven architecture powered by LangChain and Large Language Models (LLMs) to ensure high-quality, relevant, and consistent output.

---

## ✨ Features

- **Autonomous Operation**: Given a high-level goal, the agent independently plans and executes the necessary steps.
- **Dynamic Research Strategy**: Brainstorms high-signal subtopics to gather more relevant articles.
- **Multi-Layered Curation**: Filters articles based on source reputation and category diversity.
- **AI-Powered Quality Assurance**: An "Editor-in-Chief" agent reviews every draft before publication.
- **Robust State Management**: Prevents duplicate articles and ensures clean weekly runs.
- **Graceful Failure**: Halts and reports if the draft doesn't meet quality standards.
- **Flexible & Reusable**: Easily retarget the newsletter by changing the input keyword—no code changes required.

---

## 🧠 Agentic Architecture

This system is built as a true agentic workflow using the LangChain framework. A "Master Reasoning Agent" coordinates a toolbox of specialized functions to achieve its goal.

### 🧩 Example Thought Process (Topic: "Blockchain")

1. **Goal**: “Create and publish a high-quality newsletter about ‘Blockchain’.”
2. **Strategy Formulation**: Use `generate_search_subtopics` to find specific, high-signal queries.
3. **Draft Creation**: Use `create_initial_draft` to generate content from those subtopics.
4. **Quality Review**: Use `review_draft_for_relevance_and_quality` to act as an editor.
5. **Decision Making**:
   - ✅ If approved: Use `publish_approved_newsletter`
   - ❌ If rejected: Halt and report the reason
6. **Completion**: Report final status.

---

## 🗂️ Project Structure

The project is organized into a modular structure to separate concerns:
Generated code
newsletter-agent/
├── tools/
│   ├── __init__.py
│   └── newsletter_tools.py   # Defines the agent's toolbox and pipeline logic.
├── templates/
│   └── newsletter_template.md  # Jinja2 template for the final newsletter format.
├── .github/
│   └── workflows/
│       └── weekly_newsletter.yml # GitHub Actions workflow for weekly automation.
├── main.py                     # Main entry point to initialize and run the agent.
├── database.py                 # Handles the SQLite database for tracking articles.
├── requirements.txt            # Lists all necessary Python packages.
├── .gitignore                  # Specifies files for Git to ignore.
└── .env                        # Local configuration file for API keys (DO NOT COMMIT).
Use code with caution.

---

## 🛠️ Local Setup and Installation

### 🔧 Prerequisites

- Python 3.10 or higher
- Git

### 📥 1. Clone the Repository

```bash
git clone <your-repository-url>
cd newsletter-agent

Use code with caution.
Bash
### 📥 2. Set Up a Virtual Environment
It is highly recommended to use a Python virtual environment to manage dependencies and avoid conflicts with other projects.
Generated bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Use code with caution.
Bash
You will know the environment is active when you see (venv) at the beginning of your terminal prompt.
3. Install Dependencies
Install all the required Python libraries using the requirements.txt file.
Generated bash
pip install -r requirements.txt
Use code with caution.
Bash
4. Configure API Keys
The agent requires API keys from NewsAPI (for fetching articles) and Groq (for LLM access). These should be stored in a local .env file for security.
Create the .env file: In the root of the project directory (newsletter-agent/), create a new file named .env.
Get Your Keys:
NewsAPI: Get a free API key from newsapi.org.
Groq: Get a free API key from groq.com.
Add Keys to .env File: Open the .env file and add your keys and the default keyword for local runs. The file should look exactly like this:
Generated env
# .env

NEWS_API_KEY="your_key_from_newsapi_org"
GROQ_API_KEY="your_key_from_groq"
KEYWORD_INPUT="Startups"
Use code with caution.
Env
Note: This .env file is listed in .gitignore and should never be committed to your repository.
How to Run the Agent
Running Locally
Once your setup is complete, you can run the agent directly from your terminal. Make sure you are in the project's root directory and your virtual environment is activated.
Generated bash
python main.py
Use code with caution.
Bash
The agent will start its process, and you will see its detailed thought process and actions printed to the console, thanks to the verbose=True setting. A successful run will produce a newsletter_YYYY-MM-DD.md file in the project directory.
Running with GitHub Actions
The repository is configured to run automatically once a week via the .github/workflows/weekly_newsletter.yml file. You can also trigger it manually for any topic.
Navigate to your repository on GitHub and click the "Actions" tab.
Select the "Generate Weekly Newsletter" workflow from the left sidebar.
Click the "Run workflow" button.
An input box will appear, pre-filled with the default keyword from the YAML file. You can change this to any topic you want.
Click the green "Run workflow" button to start the job. You can monitor the progress in real-time.