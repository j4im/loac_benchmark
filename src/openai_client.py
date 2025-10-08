"""OpenAI client configuration."""

import os
from openai import OpenAI
from dotenv import load_dotenv


def get_openai_client() -> OpenAI:
    """
    Get configured OpenAI client.

    Raises:
        ValueError: If OPENAI_API_KEY not found in environment
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Please create .env file with your API key."
        )
    return OpenAI(api_key=api_key)
