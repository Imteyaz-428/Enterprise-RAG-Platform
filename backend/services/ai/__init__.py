# services/ai/__init__.py
from typing import Any


def __getattr__(name: str) -> Any:
    if name == "AIService":
        from services.ai.ai_services import AIService
        return AIService
    if name == "ai_service":
        from services.ai.ai_services import AIService
        return AIService()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
