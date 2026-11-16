import re
from typing import Any, Dict, List
from utils.logger import logger


REWRITE_PROMPT_TEMPLATE = """Rewrite the follow-up question into ONE standalone question using only the conversation history. Resolve pronouns and references. If the follow-up question already makes sense on its own, return it exactly as written. The standalone question must be under 40 words. Do not answer it. Return only the question with no quotes or extra text.

Conversation History:
{history_text}

Follow-up Question: {question}

Standalone Question:"""


STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can", "can't",
    "cannot", "could", "couldn't", "d", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further",
    "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd",
    "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in",
    "into", "is", "isn't", "it", "it's", "its", "itself", "just", "let's",
    "ll", "m", "many", "me", "more", "most", "much", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "re", "s",
    "same", "shall", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "t", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "ve", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "will", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves",
}


def extract_content_words(text: str) -> List[str]:
    """
    Extracts content words from text:
    - Lowercases
    - Drops punctuation (extracts alphanumeric word tokens)
    - Drops standard stopwords
    """
    if not text:
        return []
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS]


def _word_matches(w1: str, w2: str) -> bool:
    """
    Compares two words by their first 5 characters so inflections match.
    Also handles words with length < 5 when they share the same base prefix.
    """
    if w1[:5] == w2[:5]:
        return True
    prefix_len = min(len(w1), len(w2), 5)
    if prefix_len >= 3 and w1[:prefix_len] == w2[:prefix_len]:
        return True
    return False


def guard_rewritten_query(
    original_question: str,
    rewritten: str,
    history_text: str = "",
) -> str:
    """
    Validates a rewritten query against the original question and history:
    - Lowercase, drop stopwords and punctuation, take content words of original question.
    - If fewer than half of them (minimum 1) appear in the rewrite
      (comparing words by their first 5 characters so inflections match),
      returns original_question and logs a WARNING.
    - If the original has no content words, accepts the rewrite only if it shares
      at least one content word with the history text (comparing words by first 5 characters);
      otherwise returns original_question and logs a WARNING.
    """
    if not rewritten or rewritten.strip() == original_question.strip():
        return original_question

    orig_content = extract_content_words(original_question)
    rewrite_words = extract_content_words(rewritten)

    if orig_content:
        matches = sum(
            1 for w in orig_content
            if any(_word_matches(w, rw) for rw in rewrite_words)
        )
        required_matches = max(1, len(orig_content) / 2)
        if matches < required_matches:
            logger.warning(
                f"Query rewrite guard rejected rewrite {rewritten!r} for original {original_question!r} "
                f"({matches}/{len(orig_content)} content words matched, required {required_matches}). "
                f"Falling back to original question."
            )
            return original_question
        return rewritten
    else:
        # Original has no content words: accept rewrite only if it shares at least one
        # content word with the history text
        history_words = extract_content_words(history_text)
        shares_with_history = any(
            any(_word_matches(rw, hw) for hw in history_words)
            for rw in rewrite_words
        )
        if not shares_with_history:
            logger.warning(
                f"Query rewrite guard rejected rewrite {rewritten!r} for original {original_question!r} "
                f"(original has no content words and rewrite shares no content words with history). "
                f"Falling back to original question."
            )
            return original_question
        return rewritten


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

        try:
            raw_output = ai_service.generate_answer(
                prompt=prompt,
                timeout_seconds=5,
                max_attempts=1,
                max_fallbacks=1,
            )
        except TypeError:
            raw_output = ai_service.generate_answer(prompt=prompt)
        cleaned = clean_rewritten_query(raw_output, question)
        rewritten = guard_rewritten_query(
            original_question=question,
            rewritten=cleaned,
            history_text=history_text,
        )

        logger.info(
            f"Query rewriter: original={question!r} -> rewritten={rewritten!r}"
        )
        return rewritten

    except Exception as e:
        logger.warning(
            f"Query rewriter failed ({type(e).__name__}: {e}), keeping original={question!r}"
        )
        return question
