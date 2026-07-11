import os
from dotenv import load_dotenv

from services.ai.providers.gemini_provider import generate_answer as gemini_answer
from services.ai.providers.groq_provider import generate_answer as groq_answer

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")


def generate_answer(prompt: str) -> str:

    if LLM_PROVIDER == "gemini":
        return gemini_answer(prompt)

    elif LLM_PROVIDER == "groq":
        return groq_answer(prompt)

    raise ValueError(f"Unsupported LLM Provider: {LLM_PROVIDER}")