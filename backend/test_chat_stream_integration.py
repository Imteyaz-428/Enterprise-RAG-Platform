import os
import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from models.user import User
from models.organization import Organization
from models.chat_session import ChatSession
from models.chat_message import ChatMessage
from services.chat.chat_service import ChatService
from services.ai.ai_services import AIProviderError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="TestOrg", slug="testorg")
    session.add(org)
    session.commit()

    user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        password="hashedpassword",
        organization_id=1,
        role="employee",
    )
    session.add(user)
    session.commit()

    yield session
    session.close()


def create_mock_chunk():
    mock_doc = MagicMock()
    mock_doc.id = 10
    mock_doc.original_filename = "enterprise_rag.pdf"

    mock_chunk = MagicMock()
    mock_chunk.chunk_index = 0

    mock_res = MagicMock()
    mock_res.document = mock_doc
    mock_res.chunk = mock_chunk
    mock_res.text = "Enterprise RAG integrates enterprise search with LLMs."
    return mock_res


def test_chat_stream_live_generation_with_citations_and_session(db_session):
    """
    Tests POST /chat/stream end-to-end logic:
    - Verifies metadata event includes session_id and citations.
    - Verifies actual generated tokens are streamed.
    - Verifies done event completes the stream.
    - Verifies assistant message is saved to the session.
    """
    chat_service = ChatService()

    # Mock retrieval service to avoid pgvector distance operator on SQLite
    mock_item = create_mock_chunk()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[mock_item])

    # Mock stream_answer to allow deterministic offline testing without burning API credits
    def mock_stream_tokens(prompt):
        yield "Enterprise "
        yield "RAG "
        yield "answers "
        yield "queries."

    chat_service.ai_service.stream_answer = MagicMock(side_effect=mock_stream_tokens)

    # Mock Redis to avoid external dependency in unit tests
    chat_service.redis = MagicMock()
    chat_service.redis.get.return_value = None

    stream = chat_service.chat_stream(
        db=db_session,
        question="What is Enterprise RAG?",
        organization_id=1,
        user_id=1,
        session_id=None,
    )

    events = list(stream)
    raw_stream = "".join(events)

    # 1. Metadata event verification
    assert "event: metadata" in raw_stream
    metadata_lines = [e for e in events if "event: metadata" in e]
    assert len(metadata_lines) >= 1
    metadata_data = json.loads(metadata_lines[0].split("data: ")[1].split("\n")[0])
    assert "session_id" in metadata_data
    assert len(metadata_data["citations"]) == 1
    assert metadata_data["citations"][0]["document"] == "enterprise_rag.pdf"

    # 2. Token events verification
    token_lines = [e for e in events if "event: token" in e]
    assert len(token_lines) > 0, "Tokens must be streamed"

    # 3. Done event verification
    assert "event: done" in raw_stream

    # 4. Session & message persistence verification
    session_id = metadata_data["session_id"]
    saved_session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
    assert saved_session is not None

    messages = db_session.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
    assert len(messages) >= 2  # user message + assistant message
    assistant_msg = [m for m in messages if m.role == "assistant"][0]
    assert len(assistant_msg.content) > 0
    assert assistant_msg.citations == metadata_data["citations"]


def test_chat_stream_redis_failure_resilience(db_session):
    """
    Verifies that Redis failure (connection error, timeout) does not prevent successful AI generation.
    """
    chat_service = ChatService()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[])

    def mock_stream_tokens(prompt):
        yield "RAG "
        yield "token."

    chat_service.ai_service.stream_answer = MagicMock(side_effect=mock_stream_tokens)

    # Simulate Redis connection failure
    mock_failing_redis = MagicMock()
    mock_failing_redis.get.side_effect = Exception("Redis connection refused")
    mock_failing_redis.set.side_effect = Exception("Redis write failed")
    chat_service.redis = mock_failing_redis

    stream = chat_service.chat_stream(
        db=db_session,
        question="What is RAG?",
        organization_id=1,
        user_id=1,
    )

    events = list(stream)
    raw_stream = "".join(events)

    # AI generation must succeed regardless of Redis failure
    assert "event: metadata" in raw_stream
    assert "event: token" in raw_stream
    assert "event: done" in raw_stream
    assert "event: error" not in raw_stream


def test_chat_stream_terminal_error_emits_no_token_events(db_session):
    """
    Task 2 requirement:
    After a terminal error event, no token event is emitted.
    """
    chat_service = ChatService()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[])
    chat_service.redis = MagicMock()
    chat_service.redis.get.return_value = None

    # Simulate all providers failing
    chat_service.ai_service = MagicMock()
    chat_service.ai_service._sanitize_error = lambda x: x
    chat_service.ai_service.stream_answer.side_effect = AIProviderError(
        "All AI providers failed: gemini (authentication), groq (authentication), deepseek (billing)"
    )

    stream = chat_service.chat_stream(
        db=db_session,
        question="What is RAG?",
        organization_id=1,
        user_id=1,
    )

    events = list(stream)
    raw_stream = "".join(events)

    # Must emit error event
    assert "event: error" in raw_stream
    # Must NOT emit any token event after terminal error
    assert "event: token" not in raw_stream
    # Must emit done event
    assert "event: done" in raw_stream


def parse_sse_events(sse_text: str):
    """
    Small spec-compliant SSE parser:
    Splits the stream into messages on '\n\n', and for each message,
    joins the 'data: ' lines with '\n' to return the original message text.
    """
    events = []
    for raw in sse_text.split("\n\n"):
        if not raw.strip():
            continue
        event_name = "message"
        data_lines = []
        for line in raw.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:"):].lstrip(" ")
            elif line.startswith("data:"):
                val = line[len("data:"):]
                if val.startswith(" "):
                    val = val[1:]
                data_lines.append(val)
        events.append({"event": event_name, "data": "\n".join(data_lines)})
    return events


def test_sse_token_framing_unit():
    """
    Unit tests for SSE token framing per the SSE spec:
    - a newline token: "a\nb" -> "event: token\ndata: a\ndata: b\n\n"
    - a "\n\n" token: "\n\n" -> "event: token\ndata: \ndata: \ndata: \n\n"
    - a token without newline: "hello" -> "event: token\ndata: hello\n\n"
    - error framing: text with newline and without newline
    """
    # 1. Newline token
    assert ChatService.format_sse_event("token", "a\nb") == "event: token\ndata: a\ndata: b\n\n"

    # 2. "\n\n" token
    assert ChatService.format_sse_event("token", "\n\n") == "event: token\ndata: \ndata: \ndata: \n\n"

    # 3. Token without newline (byte-for-byte identical to today)
    assert ChatService.format_sse_event("token", "normal_token") == "event: token\ndata: normal_token\n\n"

    # 4. Error text framing
    assert ChatService.format_sse_event("error", "err_no_nl") == "event: error\ndata: err_no_nl\n\n"
    assert (
        ChatService.format_sse_event("error", "err\nwith\nnewline")
        == "event: error\ndata: err\ndata: with\ndata: newline\n\n"
    )


def test_chat_stream_tokens_with_newlines_round_trip_streamed(db_session):
    """
    Tests live streamed path with:
    - a newline token ("a\nb")
    - a "\n\n" token
    - a token without newline
    - round trip through a small spec-compliant parser (joining data lines with "\n")
      that returns the original text.
    """
    chat_service = ChatService()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[])
    chat_service.redis = MagicMock()
    chat_service.redis.get.return_value = None

    tokens_to_stream = [
        "First token without newline. ",
        "a\nb",
        " middle token ",
        "\n\n",
        "Final code block:\n```python\nprint(42)\n```\nDone.",
    ]
    expected_original_text = "".join(tokens_to_stream)

    chat_service.ai_service.stream_answer = MagicMock(return_value=iter(tokens_to_stream))

    stream = chat_service.chat_stream(
        db=db_session,
        question="Test streamed newlines",
        organization_id=1,
        user_id=1,
    )

    events = list(stream)
    raw_stream = "".join(events)

    # Verify exact framing of specific tokens
    assert "event: token\ndata: a\ndata: b\n\n" in raw_stream
    assert "event: token\ndata: \ndata: \ndata: \n\n" in raw_stream
    assert "event: token\ndata: First token without newline. \n\n" in raw_stream
    assert "event: done\ndata: {}\n\n" in raw_stream

    # Parse through spec-compliant parser
    parsed_events = parse_sse_events(raw_stream)
    token_events = [e for e in parsed_events if e["event"] == "token"]
    extracted_tokens = [e["data"] for e in token_events]

    # Individual token round-trip
    assert extracted_tokens == tokens_to_stream

    # Complete text round-trip
    reconstructed_text = "".join(extracted_tokens)
    assert reconstructed_text == expected_original_text


def test_chat_stream_tokens_with_newlines_round_trip_cached(db_session):
    """
    Tests cached path with:
    - a newline token ("a\nb")
    - a "\n\n" token
    - a token without newline
    - round trip through a small spec-compliant parser (joining data lines with "\n")
      that returns the original text.
    """
    chat_service = ChatService()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[])

    original_cached_answer = "Header without newline.\n\nSection with a\nb and code:\n```\nresult\n```\n"

    mock_redis = MagicMock()
    mock_redis.get.return_value = {
        "answer": original_cached_answer,
        "citations": [{"document": "test.pdf", "chunk_index": 0}],
    }
    chat_service.redis = mock_redis

    stream = chat_service.chat_stream(
        db=db_session,
        question="Test cached newlines",
        organization_id=1,
        user_id=1,
    )

    events = list(stream)
    raw_stream = "".join(events)

    # Verify exact framing pieces are present per SSE spec
    assert "event: token\ndata: a\ndata: b" in raw_stream
    assert "event: token\ndata: \ndata: \ndata: \n\n" in raw_stream or "data: \n" in raw_stream
    assert "event: done\ndata: {}\n\n" in raw_stream

    # Parse through spec-compliant parser
    parsed_events = parse_sse_events(raw_stream)
    token_events = [e for e in parsed_events if e["event"] == "token"]
    extracted_tokens = [e["data"] for e in token_events]

    # Complete text round-trip returns original text
    reconstructed_text = "".join(extracted_tokens)
    assert reconstructed_text == original_cached_answer


def test_chat_stream_error_event_spec_framing(db_session):
    """
    Verifies that event: error formatting adheres to SSE spec framing.
    """
    chat_service = ChatService()
    chat_service.retrieval_service.retrieve = MagicMock(return_value=[])
    chat_service.redis = MagicMock()
    chat_service.redis.get.return_value = None

    chat_service.ai_service = MagicMock()
    chat_service.ai_service._sanitize_error = lambda x: x
    chat_service.ai_service.stream_answer.side_effect = AIProviderError("Provider failure")

    stream = chat_service.chat_stream(
        db=db_session,
        question="Test error framing",
        organization_id=1,
        user_id=1,
    )

    events = list(stream)
    raw_stream = "".join(events)

    parsed = parse_sse_events(raw_stream)
    error_events = [e for e in parsed if e["event"] == "error"]
    assert len(error_events) == 1
    err_json = json.loads(error_events[0]["data"])
    assert "AI provider generation failed" in err_json["error"]


