from unittest.mock import MagicMock, patch
from services.chat.query_rewriter import rewrite_query, clean_rewritten_query
from services.chat.chat_service import ChatService


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
