"""
Tests for Phase 1 - Step 5: SQLAlchemy Issues, Relationship Registry, and Cascade Behavior.

Verifies:
1. All models register without InvalidRequestError in configure_mappers().
2. Bidirectional relationships have matching back_populates.
3. Cascading delete-orphan behavior:
   - Organization deletion cascades to users, documents, and chat sessions.
   - Document deletion cascades to chunks.
   - ChatSession deletion cascades to chat messages.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy.pool import StaticPool

from database.database import Base
from models import Organization, User, Document, DocumentChunk, ChatSession, ChatMessage
from core.enums import UserRole


@pytest.fixture
def db_session():
    """Provides a fresh SQLite in-memory database with all models created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_mappers()
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


def test_mapper_registry_configuration():
    """Verifies that the SQLAlchemy mapper registry compiles without any errors."""
    configure_mappers()
    # Check mapper existence for all models
    assert Organization.__mapper__ is not None
    assert User.__mapper__ is not None
    assert Document.__mapper__ is not None
    assert DocumentChunk.__mapper__ is not None
    assert ChatSession.__mapper__ is not None
    assert ChatMessage.__mapper__ is not None


def test_bidirectional_relationships_navigation(db_session):
    """Verifies that navigation across all bidirectional relationships works in both directions."""
    # 1. Create Organization
    org = Organization(name="Acme Corp", slug="acme-corp")
    db_session.add(org)
    db_session.commit()

    # 2. Create User linked to Organization
    user = User(
        name="Alice Admin",
        email="alice@acme.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization=org,
    )
    db_session.add(user)
    db_session.commit()

    # 3. Create Document linked to Organization & User
    doc = Document(
        title="Architecture Guide",
        original_filename="arch.pdf",
        stored_filename="arch-123.pdf",
        file_path="/tmp/arch.pdf",
        file_size=1024,
        organization=org,
        uploader=user,
    )
    db_session.add(doc)
    db_session.commit()

    # 4. Create Chunk linked to Document
    chunk = DocumentChunk(
        document=doc,
        chunk_index=0,
        page_number=1,
        chunk_text="Overview of RAG platform architecture.",
    )
    db_session.add(chunk)
    db_session.commit()

    # 5. Create ChatSession linked to Organization & User
    chat_session = ChatSession(
        title="Technical Discussion",
        organization=org,
        user=user,
    )
    db_session.add(chat_session)
    db_session.commit()

    # 6. Create ChatMessage linked to ChatSession
    msg = ChatMessage(
        session=chat_session,
        role="user",
        content="What is the architecture?",
    )
    db_session.add(msg)
    db_session.commit()

    # Verify forward & reverse navigation
    assert user.organization.id == org.id
    assert org.users[0].id == user.id

    assert doc.organization.id == org.id
    assert org.documents[0].id == doc.id
    assert doc.uploader.id == user.id
    assert user.documents[0].id == doc.id

    assert chunk.document.id == doc.id
    assert doc.chunks[0].id == chunk.id

    assert chat_session.organization.id == org.id
    assert org.chat_sessions[0].id == chat_session.id
    assert chat_session.user.id == user.id
    assert user.chat_sessions[0].id == chat_session.id

    assert msg.session.id == chat_session.id
    assert chat_session.messages[0].id == msg.id


def test_document_cascade_deletes_chunks(db_session):
    """Deleting a document cascades and removes its document chunks."""
    org = Organization(name="Cascade Org", slug="cascade-org")
    user = User(
        name="Bob",
        email="bob@cascade.com",
        password="pass",
        role=UserRole.ADMIN,
        organization=org,
    )
    doc = Document(
        title="Doc 1",
        original_filename="d1.pdf",
        stored_filename="d1-uuid.pdf",
        file_path="/tmp/d1.pdf",
        file_size=500,
        organization=org,
        uploader=user,
    )
    chunk1 = DocumentChunk(document=doc, chunk_index=0, chunk_text="Chunk 1")
    chunk2 = DocumentChunk(document=doc, chunk_index=1, chunk_text="Chunk 2")

    db_session.add_all([org, user, doc, chunk1, chunk2])
    db_session.commit()

    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 2

    # Delete document
    db_session.delete(doc)
    db_session.commit()

    # Verify chunks were cascaded and removed
    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 0


def test_chat_session_cascade_deletes_messages(db_session):
    """Deleting a chat session cascades and removes its messages."""
    org = Organization(name="Chat Org", slug="chat-org")
    user = User(
        name="Charlie",
        email="charlie@chat.com",
        password="pass",
        role=UserRole.ADMIN,
        organization=org,
    )
    session = ChatSession(title="Chat Session", organization=org, user=user)
    msg1 = ChatMessage(session=session, role="user", content="Hello")
    msg2 = ChatMessage(session=session, role="assistant", content="Hi Charlie!")

    db_session.add_all([org, user, session, msg1, msg2])
    db_session.commit()

    assert db_session.query(ChatMessage).filter(ChatMessage.session_id == session.id).count() == 2

    # Delete session
    db_session.delete(session)
    db_session.commit()

    # Verify messages were cascaded and removed
    assert db_session.query(ChatMessage).filter(ChatMessage.session_id == session.id).count() == 0


def test_organization_cascade_deletes_dependents(db_session):
    """Deleting an organization cascades to delete its users, documents, and chat sessions."""
    org = Organization(name="Doomed Org", slug="doomed-org")
    user = User(
        name="Dave",
        email="dave@doomed.com",
        password="pass",
        role=UserRole.ADMIN,
        organization=org,
    )
    doc = Document(
        title="Doomed Doc",
        original_filename="doomed.pdf",
        stored_filename="doomed-uuid.pdf",
        file_path="/tmp/doomed.pdf",
        file_size=100,
        organization=org,
        uploader=user,
    )
    session = ChatSession(title="Doomed Session", organization=org, user=user)

    db_session.add_all([org, user, doc, session])
    db_session.commit()

    org_id = org.id
    user_id = user.id
    doc_id = doc.id
    session_id = session.id

    # Delete organization
    db_session.delete(org)
    db_session.commit()

    assert db_session.query(User).filter(User.id == user_id).first() is None
    assert db_session.query(Document).filter(Document.id == doc_id).first() is None
    assert db_session.query(ChatSession).filter(ChatSession.id == session_id).first() is None
