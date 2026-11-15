import os
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """Ensures .env is loaded reliably regardless of current working directory."""
    load_dotenv()
    # Check parent directory (backend/.env) if not already loaded
    backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)


load_environment()

# Support overriding provider priority via environment (RAG_PROVIDERS or AI_PROVIDERS)
_configured_providers = os.getenv("RAG_PROVIDERS") or os.getenv("AI_PROVIDERS")
if _configured_providers:
    RAG_PROVIDERS = [p.strip().lower() for p in _configured_providers.split(",") if p.strip()]
else:
    RAG_PROVIDERS = [
        "gemini",
        "groq",
        "deepseek"
    ]

SEARCH_TOP_K = 5
RERANK_CANDIDATES = 20

# AI Provider Reliability & Execution Configuration
AI_REQUEST_TIMEOUT = 30  # seconds per request
AI_MAX_RETRIES = 2       # maximum attempts per provider for transient errors
AI_RETRY_MIN_WAIT = 1    # minimum backoff wait in seconds
AI_RETRY_MAX_WAIT = 4    # maximum backoff wait in seconds

