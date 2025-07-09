# test_langsmith.py

import os
from langchain_groq import ChatGroq

print("--- LangSmith Minimal Test Script ---")

# We don't need dotenv; the GitHub Action provides the environment variables.
# We will explicitly check for them to be sure.
ls_tracing = os.getenv("LANGCHAIN_TRACING_V2")
ls_api_key = os.getenv("LANGCHAIN_API_KEY")
ls_project = os.getenv("LANGCHAIN_PROJECT")

if not all([ls_tracing, ls_api_key, ls_project]):
    print("❌ ERROR: One or more LangSmith environment variables are missing.")
    exit(1)

print(f"✅ Found LangSmith Environment Variables:")
print(f"   - Project: {ls_project}")
print(f"   - Tracing Enabled: {ls_tracing}")
print(f"   - API Key is Set: {'true' if ls_api_key else 'false'}")

try:
    print("\nAttempting to initialize a LangChain component to trigger tracing...")
    # Initializing a component is what triggers the first communication with LangSmith
    llm = ChatGroq(
        model_name="llama3-8b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    print("✅ Component initialized successfully.")

    print("\nAttempting a simple LLM call...")
    llm.invoke("Hello, world!")

    print("✅ LLM call completed. If tracing is configured correctly, this run should now appear in your LangSmith project.")
    print("\n--- Test Script Finished ---")

except Exception as e:
    print(f"\n❌ An error occurred during the test script execution: {e}")
    exit(1)
