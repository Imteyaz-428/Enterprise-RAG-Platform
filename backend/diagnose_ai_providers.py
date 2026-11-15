import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend/.env is loaded reliably
backend_dir = Path(__file__).resolve().parent
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)
else:
    load_dotenv(override=True)

# Add backend directory to sys.path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.groq_provider import GroqProvider
from services.ai.providers.deepseek_provider import DeepSeekProvider
from services.ai.ai_services import classify_provider_error


def mask_key(val: str | None) -> str:
    if not val:
        return "[NOT SET]"
    if len(val) <= 8:
        return f"{val[:2]}...{val[-2:]} (len: {len(val)})"
    return f"{val[:6]}...{val[-4:]} (len: {len(val)})"


def run_diagnostics():
    report = {
        "environment": {
            "loaded_from": str(env_file) if env_file.exists() else "system/cwd",
            "gemini_key": mask_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "groq_key": mask_key(os.getenv("GROQ_API_KEY")),
            "deepseek_key": mask_key(os.getenv("DEEPSEEK_API_KEY")),
        },
        "providers": {},
    }

    # 1. Gemini
    try:
        gemini = GeminiProvider()
        ans = gemini.generate("ping")
        report["providers"]["gemini"] = {
            "status": "healthy",
            "model": gemini.model,
            "authentication": "valid",
            "test_generation": ans.strip()[:50],
            "failure_category": "none",
        }
    except Exception as e:
        cat = classify_provider_error(e)
        report["providers"]["gemini"] = {
            "status": "unhealthy",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "authentication": "invalid" if cat == "authentication" else "untested",
            "test_generation": None,
            "failure_category": cat,
            "error": str(e),
        }

    # 2. Groq
    try:
        groq = GroqProvider()
        ans = groq.generate("ping")
        report["providers"]["groq"] = {
            "status": "healthy",
            "model": groq.model,
            "authentication": "valid",
            "test_generation": ans.strip()[:50],
            "failure_category": "none",
        }
    except Exception as e:
        cat = classify_provider_error(e)
        report["providers"]["groq"] = {
            "status": "unhealthy",
            "model": os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            "authentication": "invalid" if cat == "authentication" else "untested",
            "test_generation": None,
            "failure_category": cat,
            "error": str(e),
        }

    # 3. DeepSeek
    try:
        deepseek = DeepSeekProvider()
        ans = deepseek.generate("ping")
        report["providers"]["deepseek"] = {
            "status": "healthy",
            "model": deepseek.model,
            "authentication": "valid",
            "test_generation": ans.strip()[:50],
            "failure_category": "none",
        }
    except Exception as e:
        cat = classify_provider_error(e)
        report["providers"]["deepseek"] = {
            "status": "unhealthy",
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            "authentication": "invalid" if cat == "authentication" else "valid_or_untested",
            "test_generation": None,
            "failure_category": cat,
            "error": str(e),
        }

    return report


if __name__ == "__main__":
    rep = run_diagnostics()
    print(json.dumps(rep, indent=2))
