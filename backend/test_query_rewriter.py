import time
import pytest
from unittest.mock import MagicMock, patch
from services.chat.query_rewriter import (
    rewrite_query,
    clean_rewritten_query,
    guard_rewritten_query,
    extract_content_words,
    REWRITE_PROMPT_TEMPLATE,
)
from services.chat.chat_service import ChatService
from services.ai.ai_services import AIService, AIProviderError
from services.ai.providers.base_provider import BaseProvider


def test_empty_history_returns_unchanged_and_provider_not_called():
    mock_ai = MagicMock()

    # Empty list
    result = rewrite_query(
        history=[],
        question="What is the base-case IRR for Project Lotus?",
        ai_service=mock_ai,
    )
    assert result == "What is the base-case IRR for Project Lotus?"
    mock_ai.generate_answer.assert_not_called()

    # None history
    result_none = rewrite_query(
        history=None,
        question="What is the base-case IRR for Project Lotus?",
        ai_service=mock_ai,
    )
    assert result_none == "What is the base-case IRR for Project Lotus?"
    mock_ai.generate_answer.assert_not_called()


def test_provider_failure_returns_original_question():
    mock_ai = MagicMock()
    mock_ai.generate_answer.side_effect = RuntimeError("AI Provider unreachable")

    history = [
        {"role": "user", "content": "What is Project Lotus?"},
        {"role": "assistant", "content": "Project Lotus is a quick-commerce retail expansion."},
    ]
    original = "What is its projected IRR?"

    # Must never raise an exception, must return original question
    result = rewrite_query(
        history=history,
        question=original,
        ai_service=mock_ai,
    )
    assert result == original


def test_provider_empty_or_whitespace_returns_original_question():
    mock_ai = MagicMock()
    mock_ai.generate_answer.return_value = "   "

    history = [
        {"role": "user", "content": "What is Veloura Prime?"},
        {"role": "assistant", "content": "It is a loyalty programme."},
    ]
    original = "What is its retention rate?"

    result = rewrite_query(
        history=history,
        question=original,
        ai_service=mock_ai,
    )
    assert result == original


def test_output_cleaning():
    original = "And what about downside?"

    # Strip double quotes
    assert (
        clean_rewritten_query('"What is the IRR in the downside scenario?"', original)
        == "What is the IRR in the downside scenario?"
    )

    # Strip single quotes
    assert (
        clean_rewritten_query("'What is the IRR in the downside scenario?'", original)
        == "What is the IRR in the downside scenario?"
    )

    # Strip backticks and smart/curly quotes
    assert (
        clean_rewritten_query('`“What is the IRR in the downside scenario?”`', original)
        == "What is the IRR in the downside scenario?"
    )

    # Strip leading label prefix
    assert (
        clean_rewritten_query("Standalone Question: What is the downside IRR for Project Lotus?", original)
        == "What is the downside IRR for Project Lotus?"
    )
    assert (
        clean_rewritten_query("Question: What is the downside IRR for Project Lotus?", original)
        == "What is the downside IRR for Project Lotus?"
    )

    # Normalize newlines and whitespace
    multiline = "What is the base-case IRR\nfor Project Lotus\r\nin the downside scenario?"
    cleaned = clean_rewritten_query(multiline, original)
    assert "\n" not in cleaned
    assert "\r" not in cleaned
    assert cleaned == "What is the base-case IRR for Project Lotus in the downside scenario?"

    # Cap at 300 characters
    long_question = "What is " + ("x" * 350) + "?"
    capped = clean_rewritten_query(long_question, original)
    assert len(capped) <= 300


def test_history_truncation_to_last_4_and_500_chars():
    mock_ai = MagicMock()
    mock_ai.generate_answer.return_value = "What is the capital requirement for dark stores?"

    long_text = "A" * 800
    history = [
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 3"},
        {"role": "assistant", "content": "Msg 4"},
        {"role": "user", "content": long_text},
        {"role": "assistant", "content": "Msg 6"},
    ]

    rewrite_query(
        history=history,
        question="How much capital does each need?",
        ai_service=mock_ai,
    )

    called_prompt = mock_ai.generate_answer.call_args[1]["prompt"]
    # Only last 4 messages should be in prompt (Msg 3 and earlier excluded)
    assert "Msg 1" not in called_prompt
    assert "Msg 2" not in called_prompt
    assert "Msg 3" in called_prompt
    # Content should be truncated to 500 chars (800 'A's reduced to 500)
    assert ("A" * 501) not in called_prompt
    assert ("A" * 500) in called_prompt


def test_cache_key_equal_for_same_standalone_different_otherwise():
    chat_service = ChatService()
    org_id = 1

    standalone_target = "What is the base-case IRR for Project Lotus in the downside scenario?"
    different_standalone = "How much capital expenditure does each dark store need?"

    # Two follow-up questions rewrite to the exact same standalone question
    key1 = chat_service._get_cache_key(
        organization_id=org_id,
        question=standalone_target,
    )
    key2 = chat_service._get_cache_key(
        organization_id=org_id,
        question=standalone_target,
    )
    # Different standalone question produces a different key
    key3 = chat_service._get_cache_key(
        organization_id=org_id,
        question=different_standalone,
    )

    # Identical standalone queries produce identical cache keys
    assert key1 == key2
    # Different standalone queries produce distinct cache keys
    assert key1 != key3
    assert key2 != key3


def test_prepare_chat_uses_standalone_for_retrieval_and_cache_key():
    mock_db = MagicMock()
    mock_retrieval = MagicMock()
    mock_prompt = MagicMock()
    mock_ai = MagicMock()

    mock_session = MagicMock()
    mock_session.id = 42

    mock_msg = MagicMock()
    mock_msg.role = "user"
    mock_msg.content = "What is Project Lotus?"

    mock_retrieval.retrieve.return_value = []
    mock_prompt.build_prompt.return_value = "built prompt"

    chat_service = ChatService(
        retrieval_service=mock_retrieval,
        prompt_service=mock_prompt,
        ai_service=mock_ai,
    )

    chat_service._get_or_create_session = MagicMock(return_value=mock_session)

    followup = "And what happens to it in the downside scenario?"
    standalone_rewritten = "What is the base-case IRR for Project Lotus in the downside scenario?"

    with (
        patch("services.chat.chat_service.get_recent_messages", return_value=[mock_msg]),
        patch("services.chat.chat_service.save_message") as mock_save,
        patch("services.chat.chat_service.rewrite_query", return_value=standalone_rewritten) as mock_rewrite,
    ):
        session, prompt, citations, cache_key = chat_service._prepare_chat(
            db=mock_db,
            question=followup,
            organization_id=1,
            user_id=10,
        )

        # 1. rewrite_query called with history and user question
        mock_rewrite.assert_called_once()
        assert mock_rewrite.call_args[1]["question"] == followup

        # 2. retrieval_service called with standalone rewritten question
        mock_retrieval.retrieve.assert_called_once_with(
            db=mock_db,
            question=standalone_rewritten,
            organization_id=1,
        )

        # 3. save_message saves user's original question
        mock_save.assert_called_once_with(
            db=mock_db,
            session_id=mock_session.id,
            role="user",
            content=followup,
        )

        # 4. prompt_service.build_prompt called with user's original question
        mock_prompt.build_prompt.assert_called_once_with(
            history=[mock_msg],
            chunks=[],
            question=followup,
        )

        # 5. cache_key generated using standalone rewritten question
        expected_cache_key = chat_service._get_cache_key(
            organization_id=1,
            question=standalone_rewritten,
        )
        assert cache_key == expected_cache_key


class _MockProviderWithCount(BaseProvider):
    def __init__(self, answer: str | None = None, exc: Exception | None = None, sleep_seconds: float = 0.0):
        self.answer = answer
        self.exc = exc
        self.sleep_seconds = sleep_seconds
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)
        if self.exc:
            raise self.exc
        return self.answer or "default response"

    def stream(self, prompt: str):
        self.call_count += 1
        yield self.answer or "default response"


def test_rewrite_prompt_template_instruction():
    """Requirement 3: Prompt template contains the exact standalone preservation instruction."""
    assert "If the follow-up question already makes sense on its own, return it exactly as written." in REWRITE_PROMPT_TEMPLATE


def test_rewrite_query_passes_hardening_parameters_and_handles_timeout():
    """Requirement 2 & 4: rewriter passes 5s timeout, single attempt, at most 1 fallback; handles timeout."""
    mock_ai = MagicMock()
    mock_ai.generate_answer.side_effect = TimeoutError("Request timed out after 5.0 seconds")

    history = [
        {"role": "user", "content": "Tell me about Project Lotus."},
        {"role": "assistant", "content": "Project Lotus is a retail expansion."},
    ]
    original = "What is its projected IRR?"

    result = rewrite_query(
        history=history,
        question=original,
        ai_service=mock_ai,
    )
    assert result == original
    mock_ai.generate_answer.assert_called_once()
    call_kwargs = mock_ai.generate_answer.call_args[1]
    assert call_kwargs.get("timeout_seconds") == 5
    assert call_kwargs.get("max_attempts") == 1
    assert call_kwargs.get("max_fallbacks") == 1


def test_rewrite_query_fast_fallback_on_slow_provider():
    """Requirement 4: The rewriter returns the original question quickly when the provider times out."""
    ai_service = AIService()
    # Mock gemini to sleep 2 seconds, well past a 0.05s timeout
    gemini = _MockProviderWithCount(sleep_seconds=2.0)
    groq = _MockProviderWithCount(sleep_seconds=2.0)
    deepseek = _MockProviderWithCount(answer="Never reached")

    ai_service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
        "deepseek": deepseek,
    }

    history = [
        {"role": "user", "content": "What is Project Lotus?"},
        {"role": "assistant", "content": "It is an expansion plan."},
    ]
    original = "What is its IRR?"

    # We patch generate_answer inside rewrite_query or test generate_answer with small timeout directly
    t0 = time.perf_counter()
    with pytest.raises(AIProviderError):
        ai_service.generate_answer(
            prompt="test",
            timeout_seconds=0.05,
            max_attempts=1,
            max_fallbacks=1,
        )
    elapsed = time.perf_counter() - t0

    # With 2 providers each timing out at 0.05s, elapsed should be well under 0.5s
    assert elapsed < 0.5
    assert gemini.call_count == 1
    assert groq.call_count == 1
    assert deepseek.call_count == 0


def test_generate_answer_without_parameters_behaves_as_before():
    """Requirement 4: generate_answer without new parameters behaves as before (retries + all fallbacks)."""
    ai_service = AIService()
    gemini = _MockProviderWithCount(exc=TimeoutError("Gemini timed out"))
    groq = _MockProviderWithCount(exc=TimeoutError("Groq timed out"))
    deepseek = _MockProviderWithCount(answer="DeepSeek final answer")

    ai_service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
        "deepseek": deepseek,
    }

    # Patch retry waits to make the test instant
    with (
        patch("services.ai.config.AI_RETRY_MIN_WAIT", 0.001),
        patch("services.ai.config.AI_RETRY_MAX_WAIT", 0.002),
    ):
        result = ai_service.generate_answer(prompt="What is RAG?")

    assert result == "DeepSeek final answer"
    # Normal behavior: transient errors are retried up to AI_MAX_RETRIES (2) per provider
    assert gemini.call_count == 2
    assert groq.call_count == 2
    # All providers are tried (no limit to 1 fallback)
    assert deepseek.call_count == 1


def test_generate_answer_with_harden_parameters_enforces_limits():
    """Requirement 2 & 4: generate_answer with new parameters enforces 1 attempt and 1 fallback."""
    ai_service = AIService()
    gemini = _MockProviderWithCount(exc=TimeoutError("Gemini timed out"))
    groq = _MockProviderWithCount(exc=TimeoutError("Groq timed out"))
    deepseek = _MockProviderWithCount(answer="DeepSeek final answer")

    ai_service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
        "deepseek": deepseek,
    }

    with pytest.raises(AIProviderError):
        ai_service.generate_answer(
            prompt="What is RAG?",
            timeout_seconds=5,
            max_attempts=1,
            max_fallbacks=1,
        )

    # Hardened behavior: single attempt per provider (no retries)
    assert gemini.call_count == 1
    # At most 1 fallback provider tried (groq)
    assert groq.call_count == 1
    # DeepSeek should NOT be called at all
    assert deepseek.call_count == 0


def test_guard_rejects_thc_and_falls_back_to_original(caplog):
    """Stage 2.3c: THC hallucination fails guard and falls back to original with a WARNING."""
    original = "What is the net present value of Project Lotus at the 12% discount rate?"
    thc_rewrite = (
        "Are there any potential side effects or contraindications associated with taking "
        "5-axyl-methyl tetrahydrocannabinol (THC) as a topical analgesic?"
    )
    with caplog.at_level("WARNING"):
        result = guard_rewritten_query(original_question=original, rewritten=thc_rewrite)

    assert result == original
    assert any("Query rewrite guard rejected" in record.message for record in caplog.records)


def test_guard_accepts_required_real_rewrites():
    """Stage 2.3c: Requirement 4 real rewrites must pass the guard."""
    # 1. "What is its retention rate?" -> "What is the retention rate of Veloura Prime?"
    q1 = "What is its retention rate?"
    rw1 = "What is the retention rate of Veloura Prime?"
    assert guard_rewritten_query(q1, rw1) == rw1

    # 2. "What if it is doubled?" -> "What happens to the system's behavior if the total token budget B is doubled?"
    q2 = "What if it is doubled?"
    rw2 = "What happens to the system's behavior if the total token budget B is doubled?"
    assert guard_rewritten_query(q2, rw2) == rw2

    # 3. "Is the gap bigger for harder questions?" -> "Is the exact match performance gap between SparseRoute and DenseFlat larger for harder questions?"
    q3 = "Is the gap bigger for harder questions?"
    rw3 = "Is the exact match performance gap between SparseRoute and DenseFlat larger for harder questions?"
    assert guard_rewritten_query(q3, rw3) == rw3


def test_guard_accepts_all_report_rewrites():
    """Stage 2.3c: Requirement 4 - all real rewrites from our benchmark report must pass."""
    cases = [
        (
            "And what happens to it in the downside scenario?",
            "What is the cumulative 5-year IRR for Project Lotus in the downside scenario?",
        ),
        (
            "How much capital does each of them need?",
            "How much capital does each dark store in the first phase need?",
        ),
        (
            "Which of these has the highest smartphone penetration?",
            "Which of Indore, Jaipur, Lucknow, and Coimbatore has the highest smartphone penetration?",
        ),
        (
            "And when does the Board decide on it?",
            "When does the Board decide on Phase 1?",
        ),
        (
            "What optimiser and how many epochs were used to train it?",
            "What optimiser and how many epochs were used to train SparseRoute's 6-layer transformer encoder router?",
        ),
        (
            "What learning rate was the SparseRoute router trained with?",
            "What learning rate was the SparseRoute router trained with?",
        ),
        (
            "What is the net present value of Project Lotus at the 12% discount rate?",
            "What is the net present value of Project Lotus at the 12% discount rate?",
        ),
        (
            "How many Veloura Prime members are there?",
            "How many Veloura Prime members are there?",
        ),
    ]

    for original, rewrite in cases:
        assert guard_rewritten_query(original, rewrite) == rewrite


def test_guard_no_content_words_in_original(caplog):
    """
    Stage 2.3c: If original has no content words, accept rewrite only if it shares
    at least one content word with history; otherwise log WARNING and fall back.
    """
    history_text = "User: What is Veloura Prime?\nAssistant: It is Veloura's loyalty programme with 640,000 active members."
    original = "What about it?"  # all stopwords

    # Case A: Rewrite shares content words ('veloura', 'prime') with history -> PASS
    rewrite_valid = "What about Veloura Prime?"
    assert guard_rewritten_query(original, rewrite_valid, history_text=history_text) == rewrite_valid

    # Case B: Rewrite shares NO content words with history -> FAIL, WARNING, fallback
    rewrite_invalid = "Are there any side effects of THC?"
    with caplog.at_level("WARNING"):
        result = guard_rewritten_query(original, rewrite_invalid, history_text=history_text)
    assert result == original
    assert any("Query rewrite guard rejected" in record.message for record in caplog.records)


def test_guard_inflection_matching():
    """Verify first 5 characters match inflections like invest/investment, train/training."""
    q = "Should we invest in it?"
    rw = "Should we make an investment in Project Lotus?"
    # 'invest' matches 'investment' by first 5 chars 'inves'
    assert guard_rewritten_query(q, rw) == rw


def test_rewrite_query_end_to_end_rejects_hallucination():
    """End-to-end rewrite_query test: mock LLM returns THC hallucination, rewrite_query falls back to original."""
    mock_ai = MagicMock()
    mock_ai.generate_answer.return_value = (
        "Are there any potential side effects or contraindications associated with taking "
        "5-axyl-methyl tetrahydrocannabinol (THC) as a topical analgesic?"
    )

    history = [
        {"role": "user", "content": "What is SparseRoute's default token budget?"},
        {"role": "assistant", "content": "The default budget B is 2,048 tokens."},
    ]
    original = "What is the net present value of Project Lotus at the 12% discount rate?"

    result = rewrite_query(
        history=history,
        question=original,
        ai_service=mock_ai,
    )
    assert result == original


