import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.dependencies import get_current_user
from database.database import Base
from dependencies.database import get_db
from models.chat_message import ChatMessage
from models.chat_session import ChatSession
from models.organization import Organization
from models.user import User
from router.chat import router as chat_router, chat_service
from services.ai.ai_services import AIProviderError


@pytest.fixture
def test_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Organization.__table__,
            User.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
        ],
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )
    init_db = TestingSessionLocal()

    # Create tenants
    org1 = Organization(id=1, name="Org One", slug="org-one")
    org2 = Organization(id=2, name="Org Two", slug="org-two")
    init_db.add_all([org1, org2])
    init_db.commit()

    # Create users
    user1 = User(
        id=1,
        name="User One",
        email="user1@example.com",
        password="hashedpassword",
        organization_id=1,
        role="employee",
    )
    user2 = User(
        id=2,
        name="User Two",
        email="user2@example.com",
        password="hashedpassword",
        organization_id=2,
        role="employee",
    )
    init_db.add_all([user1, user2])
    init_db.commit()
    init_db.close()

    # Mock retrieval service to avoid pgvector and sentence-transformers in tests
    mock_doc = MagicMock()
    mock_doc.id = 10
    mock_doc.original_filename = "enterprise_rag.pdf"

    mock_chunk = MagicMock()
    mock_chunk.chunk_index = 0

    mock_res = MagicMock()
    mock_res.document = mock_doc
    mock_res.chunk = mock_chunk
    mock_res.text = "Enterprise RAG combines search with LLMs."

    chat_service.retrieval_service = MagicMock()
    chat_service.retrieval_service.retrieve.return_value = [mock_res]

    # In-memory mock Redis
    mock_redis = MagicMock()
    mock_redis._store = {}

    def redis_get(key):
        return mock_redis._store.get(key)

    def redis_set(key, val, ttl=None):
        mock_redis._store[key] = val
        return True

    mock_redis.get.side_effect = redis_get
    mock_redis.set.side_effect = redis_set
    mock_redis._is_available = True
    chat_service.redis = mock_redis

    test_app = FastAPI()
    test_app.include_router(chat_router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    user1_mock = SimpleNamespace(
        id=1,
        name="User One",
        email="user1@example.com",
        organization_id=1,
        role="employee",
    )
    user2_mock = SimpleNamespace(
        id=2,
        name="User Two",
        email="user2@example.com",
        organization_id=2,
        role="employee",
    )

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: user1_mock

    client = TestClient(test_app)

    yield {
        "SessionLocal": TestingSessionLocal,
        "app": test_app,
        "client": client,
        "user1": user1_mock,
        "user2": user2_mock,
        "mock_redis": mock_redis,
    }

    test_app.dependency_overrides.clear()


def test_chat_non_streaming_success(test_setup):
    """Verifies POST /chat end-to-end execution."""
    client = test_setup["client"]
    SessionLocal = test_setup["SessionLocal"]

    chat_service.ai_service.generate_answer = MagicMock(
        return_value="Enterprise RAG is an AI knowledge retrieval platform."
    )

    response = client.post("/chat", json={"question": "What is Enterprise RAG?"})
    assert response.status_code == 200
    data = response.json()

    assert "session_id" in data
    assert data["answer"] == "Enterprise RAG is an AI knowledge retrieval platform."
    assert len(data["citations"]) == 1
    assert data["citations"][0]["document"] == "enterprise_rag.pdf"

    # Verify messages saved to DB
    db = SessionLocal()
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == data["session_id"]).all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What is Enterprise RAG?"
    assert messages[1].role == "assistant"
    assert messages[1].content == data["answer"]
    db.close()


def test_chat_non_streaming_cache_hit(test_setup):
    """Verifies that cache hit in /chat returns cached answer without invoking AI."""
    client = test_setup["client"]
    mock_redis = test_setup["mock_redis"]

    # Pre-populate cache
    cache_key = chat_service._get_cache_key(organization_id=1, question="Cached Question")
    mock_redis._store[cache_key] = {
        "answer": "This is a cached answer.",
        "citations": [{"document": "cached_doc.pdf", "chunk_index": 0}],
    }

    chat_service.ai_service.generate_answer = MagicMock()

    response = client.post("/chat", json={"question": "Cached Question"})
    assert response.status_code == 200
    data = response.json()

    assert data["answer"] == "This is a cached answer."
    assert data["citations"][0]["document"] == "cached_doc.pdf"
    # AI service must NOT be called on cache hit
    chat_service.ai_service.generate_answer.assert_not_called()


def test_chat_empty_question_raises_400(test_setup):
    """Verifies that empty questions return HTTP 400 for both non-streaming and streaming."""
    client = test_setup["client"]

    # Non-streaming
    res_chat = client.post("/chat", json={"question": "   "})
    assert res_chat.status_code == 400
    assert "Question cannot be empty" in res_chat.json()["detail"]

    # Streaming
    res_stream = client.post("/chat/stream", json={"question": ""})
    assert res_stream.status_code == 400
    assert "Question cannot be empty" in res_stream.json()["detail"]


def test_chat_nonexistent_session_raises_404(test_setup):
    """Verifies that invalid session_id returns HTTP 404."""
    client = test_setup["client"]

    # Non-streaming
    res_chat = client.post("/chat", json={"question": "Valid question", "session_id": 9999})
    assert res_chat.status_code == 404

    # Streaming
    res_stream = client.post("/chat/stream", json={"question": "Valid question", "session_id": 9999})
    assert res_stream.status_code == 404


def test_chat_cross_tenant_session_isolation_404(test_setup):
    """Verifies that User 2 (Org 2) cannot access or chat in User 1's (Org 1) session."""
    client = test_setup["client"]
    SessionLocal = test_setup["SessionLocal"]
    test_app = test_setup["app"]

    # Create session owned by User 1
    db = SessionLocal()
    session1 = ChatSession(id=10, title="Org 1 Chat", organization_id=1, user_id=1)
    db.add(session1)
    db.commit()
    db.close()

    # Switch current user to User 2 (Org 2)
    test_app.dependency_overrides[get_current_user] = lambda: test_setup["user2"]

    # Non-streaming
    res_chat = client.post("/chat", json={"question": "Cross-tenant probe", "session_id": 10})
    assert res_chat.status_code == 404

    # Streaming
    res_stream = client.post("/chat/stream", json={"question": "Cross-tenant probe", "session_id": 10})
    assert res_stream.status_code == 404


def test_chat_non_streaming_ai_provider_failure_returns_503(test_setup):
    """Verifies that AI provider failure in /chat returns HTTP 503 instead of 500."""
    client = test_setup["client"]

    chat_service.ai_service.generate_answer = MagicMock(
        side_effect=AIProviderError("All AI providers failed: gemini (401), groq (401)")
    )

    response = client.post("/chat", json={"question": "What is AI?"})
    assert response.status_code == 503
    assert "AI service is currently unavailable" in response.json()["detail"]


def test_chat_stream_success(test_setup):
    """Verifies POST /chat/stream end-to-end token delivery and message persistence."""
    client = test_setup["client"]
    SessionLocal = test_setup["SessionLocal"]

    def mock_stream(prompt):
        yield "Streaming "
        yield "response "
        yield "works!"

    chat_service.ai_service.stream_answer = MagicMock(side_effect=mock_stream)

    response = client.post("/chat/stream", json={"question": "Stream test question"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    body = response.text
    assert "event: metadata" in body
    assert "event: token" in body
    assert "Streaming " in body
    assert "response " in body
    assert "works!" in body
    assert "event: done" in body

    # Verify messages saved
    db = SessionLocal()
    session = db.query(ChatSession).filter(ChatSession.title.contains("Stream test question")).first()
    assert session is not None
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
    assert len(messages) == 2
    assert messages[1].content == "Streaming response works!"
    db.close()


def test_chat_stream_cache_hit(test_setup):
    """Verifies POST /chat/stream on cache hit streams cached tokens."""
    client = test_setup["client"]
    mock_redis = test_setup["mock_redis"]

    cache_key = chat_service._get_cache_key(organization_id=1, question="Stream Cache Question")
    mock_redis._store[cache_key] = {
        "answer": "Cached stream answer.",
        "citations": [{"document": "cached_doc.pdf", "chunk_index": 0}],
    }

    chat_service.ai_service.stream_answer = MagicMock()

    response = client.post("/chat/stream", json={"question": "Stream Cache Question"})
    assert response.status_code == 200
    body = response.text

    assert "event: metadata" in body
    assert "event: token" in body
    assert "Cached " in body
    assert "event: done" in body
    chat_service.ai_service.stream_answer.assert_not_called()


def test_chat_stream_terminal_error_emits_no_token_events(test_setup):
    """Verifies that streaming failure emits metadata, error, and done, with zero tokens."""
    client = test_setup["client"]

    chat_service.ai_service.stream_answer = MagicMock(
        side_effect=AIProviderError("All AI providers failed")
    )

    response = client.post("/chat/stream", json={"question": "Failure test question"})
    assert response.status_code == 200
    body = response.text

    assert "event: metadata" in body
    assert "event: error" in body
    assert "event: token" not in body
    assert "event: done" in body


def test_chat_session_management_lifecycle(test_setup):
    """Verifies session listing, detail retrieval, and deletion."""
    client = test_setup["client"]
    SessionLocal = test_setup["SessionLocal"]

    # Create session with messages
    db = SessionLocal()
    session = ChatSession(id=42, title="Test Lifecycle", organization_id=1, user_id=1)
    db.add(session)
    db.commit()

    msg1 = ChatMessage(session_id=42, role="user", content="Hello")
    msg2 = ChatMessage(session_id=42, role="assistant", content="Hi there!")
    session.messages.extend([msg1, msg2])
    db.commit()
    db.close()

    # 1. List sessions
    res_list = client.get("/chat/sessions")
    assert res_list.status_code == 200
    session_list = res_list.json()
    assert any(s["id"] == 42 for s in session_list)

    # 2. Get session details
    res_detail = client.get("/chat/sessions/42")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["title"] == "Test Lifecycle"
    assert len(detail["messages"]) == 2

    # 3. Delete session
    res_delete = client.delete("/chat/sessions/42")
    assert res_delete.status_code == 200

    # 4. Verify 404 after deletion
    res_get_deleted = client.get("/chat/sessions/42")
    assert res_get_deleted.status_code == 404
