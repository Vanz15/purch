import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Two models, two jobs:
# - THINKING_MODEL: structured extraction, classification, anything using
#   tool-calling where we need reliable, predictable JSON output.
# - CONVERSATION_MODEL: tone/personality responses, anything conversational
#   where natural language quality (especially multilingual Taglish) matters
#   more than raw extraction precision.
THINKING_MODEL = "openai/gpt-oss-20b"
CONVERSATION_MODEL = "llama-3.3-70b-versatile"

_client = None


def get_client() -> Groq:
    """Returns a singleton Groq client, initialized from GROQ_API_KEY in .env."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found. Make sure it's set in your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client