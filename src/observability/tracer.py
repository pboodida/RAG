import os
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

# Securely load the variables from the .env file into the system environment
load_dotenv()

def get_text_tracer():
    """
    Initializes and returns the Langfuse callback handler for LangChain components.
    Automatically detects system environment variables for keys.
    """
    if not os.environ.get("LANGFUSE_PUBLIC_KEY") or not os.environ.get("LANGFUSE_SECRET_KEY"):
        print("⚠️ Warning: Langfuse API keys are missing from your .env file. Tracing will be skipped.")
        return None
        
    handler = CallbackHandler()
    return handler