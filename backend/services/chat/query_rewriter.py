import re
from typing import Any, Dict, List
from utils.logger import logger


REWRITE_PROMPT_TEMPLATE = """Rewrite the follow-up question into ONE standalone question using only the conversation history. Resolve pronouns and references. The standalone question must be under 40 words. Do not answer it. Return only the question with no quotes or extra text.

Conversation History:
{history_text}

Follow-up Question: {question}

Standalone Question:"""


def clean_rewritten_query(raw_output: str, original_question: str) -> str:
    """
    Cleans raw LLM query rewrite output:
    - Strips prefixes like 'Standalone Question:' or 'Question:'
    - Strips surrounding quotes, backticks, and whitespace
    - Replaces newlines and carriage returns with spaces
    - Collapses multiple whitespace
    - Caps output at 300 characters
    - Returns original_question if empty or invalid
    """
    if not raw_output or not str(raw_output).strip():
        return original_question

    cleaned = str(raw_output).strip()

    # Remove possible leading prefix labels
    cleaned = re.sub(
        r"^(standalone\s+question|rewritten\s+question|question)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Normalize newlines and whitespace
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Strip surrounding quotes
    cleaned = cleaned.strip("\"'“”` ")

    # Cap at 300 characters
    cleaned = cleaned[:300].strip()

    if not cleaned:
        return original_question

    return cleaned


def rewrite_query(
    history: List[Dict[str, Any]] | None,
    question: str,
    ai_service: Any = None,
) -> str:
    """
    Rewrites a follow-up question into a standalone question using conversation history.

    - If history is empty, returns the question unchanged without calling the LLM.
    - Uses the last 4 messages of history, each truncated to 500 characters.
    - Short prompt resolves pronouns and coreferences into one standalone question (<40 words).
    - Cleans output (strips quotes/newlines, capped at 300 chars).
    - If the LLM fails or returns empty text, returns the original question (never raises).
    - Logs original and rewritten question at INFO level (no sensitive keys).
    """
    if not history or not question or not str(question).strip():
        return question

    try:
        # Use the last 4 messages of history, each truncated to 500 characters
        recent_history = history[-4:]
        history_lines = []

        for item in recent_history:
            if isinstance(item, dict):
                role = item.get("role", "")
                content = item.get("content", "")
            else:
                role = getattr(item, "role", "")
                content = getattr(item, "content", "")

            if hasattr(role, "value"):
                role = role.value

            role_str = str(role).capitalize() if role else "User"
            content_str = str(content or "")[:500]
            history_lines.append(f"{role_str}: {content_str}")

        history_text = "\n".join(history_lines)

        prompt = REWRITE_PROMPT_TEMPLATE.format(
            history_text=history_text,
            question=question.strip(),
        )

        # Lazily import AIService if not provided to avoid circular imports
        if ai_service is None:
            from services.ai.ai_services import AIService
            ai_service = AIService()

        raw_output = ai_service.generate_answer(prompt=prompt)
        rewritten = clean_rewritten_query(raw_output, question)

        logger.info(
            f"Query rewriter: original={question!r} -> rewritten={rewritten!r}"
        )
        return rewritten

    except Exception as e:
        logger.warning(
            f"Query rewriter failed ({type(e).__name__}: {e}), keeping original={question!r}"
        )
        return question
