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

