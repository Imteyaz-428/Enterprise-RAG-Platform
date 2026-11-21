import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from langchain_core.documents import Document as LCDocument

from database.database import Base
from models import Organization, User, Document, DocumentChunk
from core.enums import UserRole
from core.dependencies import get_current_user
from dependencies.database import get_db
from app import app
from crud.document import delete_document, get_document_by_id
from crud.document_chunk import search_similar_chunks, search_keyword_chunks
from utils.chunker import strip_repeated_headers_and_footers
from services.background.document_processor import process_document


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    org1 = Organization(id=1, name="Org One", slug="org-one")
    org2 = Organization(id=2, name="Org Two", slug="org-two")
    user1 = User(
        id=1,
        name="User One",
        email="user1@org1.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=1,
    )
    user2 = User(
        id=2,
        name="User Two",
        email="user2@org2.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=2,
    )
    session.add_all([org1, org2, user1, user2])
    session.commit()

    yield session, TestingSessionLocal

    session.close()


# -------------------------------------------------------------------------
# Test 1: Magic-byte rejection
# -------------------------------------------------------------------------

def test_magic_byte_rejection(test_db):
    session, TestingSessionLocal = test_db
    user1 = session.query(User).filter_by(id=1).first()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        return user1

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)

    # 1. Non-PDF magic bytes (starts with text, not %PDF-)
    fake_pdf = io.BytesIO(b"NOT_A_PDF_MAGIC_BYTES_HERE")
    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Invalid PDF" in response.json()["detail"] or "magic bytes" in response.json()["detail"].lower()

    # 2. Valid PDF magic bytes
    valid_pdf = io.BytesIO(b"%PDF-1.4\nTest valid content for upload testing.")
    with patch("router.document.process_document"):
        response = client.post(
            "/documents/upload",
            files={"file": ("valid.pdf", valid_pdf, "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["file_hash"] is not None

    app.dependency_overrides.clear()


# -------------------------------------------------------------------------
# Test 2: Duplicate hash -> 409 only within same organization
# -------------------------------------------------------------------------

def test_duplicate_hash_conflict_within_same_org_only(test_db):
    session, TestingSessionLocal = test_db
    user1 = session.query(User).filter_by(id=1).first()
    user2 = session.query(User).filter_by(id=2).first()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    pdf_content = b"%PDF-1.4\nUnique document content for deduplication test."

    # Upload as User 1 (Org 1) -> Success
    app.dependency_overrides[get_current_user] = lambda: user1
    with patch("router.document.process_document"):
        resp1 = client.post(
            "/documents/upload",
            files={"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
    assert resp1.status_code == 200

    # Upload same file again as User 1 (Org 1) -> 409 Conflict
    with patch("router.document.process_document"):
        resp2 = client.post(
            "/documents/upload",
            files={"file": ("doc_dup.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
    assert resp2.status_code == 409
    assert "already exists in your organization" in resp2.json()["detail"].lower()

    # Upload same file as User 2 (Org 2) -> Allowed (200 OK)
    app.dependency_overrides[get_current_user] = lambda: user2
    with patch("router.document.process_document"):
        resp3 = client.post(
            "/documents/upload",
            files={"file": ("doc_org2.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
    assert resp3.status_code == 200

    app.dependency_overrides.clear()


# -------------------------------------------------------------------------
# Test 3: Failure leaves no partial chunks and sets error_message
# -------------------------------------------------------------------------

def test_failure_leaves_no_partial_chunks_and_sets_error_message(test_db):
    session, TestingSessionLocal = test_db

    # Create document
    doc = Document(
        id=99,
        title="Failing Doc",
        original_filename="fail.pdf",
        stored_filename="fail.pdf",
        file_path="/tmp/nonexistent_fail.pdf",
        file_size=123,
        file_hash="test_fail_hash",
        organization_id=1,
        uploaded_by=1,
        status="processing",
    )
    session.add(doc)
    session.commit()

    # Insert a partial chunk to verify it gets cleaned up
    partial_chunk = DocumentChunk(
        document_id=doc.id,
        organization_id=1,
        chunk_index=0,
        chunk_text="Partial chunk that should be deleted",
    )
    session.add(partial_chunk)
    session.commit()

    assert session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 1

    # Mock extract_documents_from_pdf to simulate an unexpected error
    with patch("services.background.document_processor.SessionLocal", TestingSessionLocal):
        with patch("services.background.document_processor.extract_documents_from_pdf", side_effect=RuntimeError("Corrupt PDF stream error")):
            process_document(document_id=doc.id, file_path="/tmp/nonexistent_fail.pdf")

    # Refresh document
    session.expire_all()
    updated_doc = session.query(Document).filter(Document.id == doc.id).first()

    assert updated_doc.status == "failed"
    assert updated_doc.error_message is not None
    assert "Corrupt PDF stream error" in updated_doc.error_message
    # No stack traces or secrets
    assert "Traceback" not in updated_doc.error_message

    # Ensure no partial chunks remain
    assert session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 0


# -------------------------------------------------------------------------
# Test 4: Header & footer stripping
# -------------------------------------------------------------------------

def test_header_and_footer_stripping():
    # 4 pages:
    # "CONFIDENTIAL REPORT" at top of all 4 pages (100% >= 50%, 4 >= 3) -> stripped
    # "Page Footer 2026" at bottom of 3 pages (75% >= 50%, 3 >= 3) -> stripped
    # "Special Footer" at bottom of page 4 (25% < 50%, 1 < 3) -> kept
    # "Middle unique text" -> kept
    docs = [
        LCDocument(
            page_content="CONFIDENTIAL REPORT\nPage 1 body paragraph.\nPage Footer 2026",
            metadata={"page": 1},
        ),
        LCDocument(
            page_content="CONFIDENTIAL REPORT\nPage 2 body paragraph.\nPage Footer 2026",
            metadata={"page": 2},
        ),
        LCDocument(
            page_content="CONFIDENTIAL REPORT\nPage 3 body paragraph.\nPage Footer 2026",
            metadata={"page": 3},
        ),
        LCDocument(
            page_content="CONFIDENTIAL REPORT\nPage 4 body paragraph.\nSpecial Footer",
            metadata={"page": 4},
        ),
    ]

    cleaned = strip_repeated_headers_and_footers(docs)

    assert len(cleaned) == 4
    for i in range(3):
        assert "CONFIDENTIAL REPORT" not in cleaned[i].page_content
        assert "Page Footer 2026" not in cleaned[i].page_content
        assert f"Page {i+1} body paragraph." in cleaned[i].page_content

    # Page 4 should have header stripped, but Special Footer preserved
    assert "CONFIDENTIAL REPORT" not in cleaned[3].page_content
    assert "Special Footer" in cleaned[3].page_content
    assert "Page 4 body paragraph." in cleaned[3].page_content

    # Test less than 3 pages: nothing should be stripped
    short_docs = [
        LCDocument(page_content="HEADER\nBody 1\nFOOTER"),
        LCDocument(page_content="HEADER\nBody 2\nFOOTER"),
    ]
    cleaned_short = strip_repeated_headers_and_footers(short_docs)
    assert cleaned_short[0].page_content == "HEADER\nBody 1\nFOOTER"
    assert cleaned_short[1].page_content == "HEADER\nBody 2\nFOOTER"


# -------------------------------------------------------------------------
# Test 5: File removed on delete (and missing file ignored with warning)
# -------------------------------------------------------------------------

def test_file_removed_on_delete(test_db):
    session, _ = test_db

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"%PDF-1.4 dummy content")
        temp_path = tf.name

    assert os.path.exists(temp_path)

    doc = Document(
        id=200,
        title="Delete Test Doc",
        original_filename="del.pdf",
        stored_filename="del.pdf",
        file_path=temp_path,
        file_size=100,
        file_hash="del_hash_1",
        organization_id=1,
        uploaded_by=1,
        status="completed",
    )
    session.add(doc)
    session.commit()

    # Delete document
    delete_document(session, doc)

    # Verify file is deleted on disk
    assert not os.path.exists(temp_path)
    assert session.query(Document).filter(Document.id == 200).first() is None

    # Deleting a document with a non-existent file ignores missing file and logs warning
    doc_missing = Document(
        id=201,
        title="Missing File Doc",
        original_filename="missing.pdf",
        stored_filename="missing.pdf",
        file_path="/tmp/this_file_does_not_exist_xyz_123.pdf",
        file_size=100,
        file_hash="del_hash_2",
        organization_id=1,
        uploaded_by=1,
        status="completed",
    )
    session.add(doc_missing)
    session.commit()

    # Must not raise an error
    delete_document(session, doc_missing)
    assert session.query(Document).filter(Document.id == 201).first() is None


# -------------------------------------------------------------------------
# Test 6: Retrieval never returns another organization's chunk
# -------------------------------------------------------------------------

def test_retrieval_never_returns_another_org_chunk(test_db):
    session, _ = test_db

    # Org 1: Completed doc
    doc1 = Document(
        id=301,
        title="Org 1 Doc",
        original_filename="org1.pdf",
        stored_filename="org1.pdf",
        file_path="/tmp/org1.pdf",
        file_size=100,
        organization_id=1,
        uploaded_by=1,
        status="completed",
    )
    # Org 2: Completed doc
    doc2 = Document(
        id=302,
        title="Org 2 Doc",
        original_filename="org2.pdf",
        stored_filename="org2.pdf",
        file_path="/tmp/org2.pdf",
        file_size=100,
        organization_id=2,
        uploaded_by=2,
        status="completed",
    )
    # Org 1: Incomplete (processing) doc
    doc3 = Document(
        id=303,
        title="Org 1 Processing Doc",
        original_filename="org1_proc.pdf",
        stored_filename="org1_proc.pdf",
        file_path="/tmp/org1_proc.pdf",
        file_size=100,
        organization_id=1,
        uploaded_by=1,
        status="processing",
    )

    session.add_all([doc1, doc2, doc3])
    session.commit()

    # Chunks
    chunk1 = DocumentChunk(
        id=401,
        document_id=doc1.id,
        organization_id=1,
        chunk_index=0,
        chunk_text="Content for org 1",
        embedding=[0.1] * 1024,
    )
    chunk2 = DocumentChunk(
        id=402,
        document_id=doc2.id,
        organization_id=2,
        chunk_index=0,
        chunk_text="Content for org 2",
        embedding=[0.1] * 1024,
    )
    chunk3 = DocumentChunk(
        id=403,
        document_id=doc3.id,
        organization_id=1,
        chunk_index=0,
        chunk_text="Content for org 1 uncompleted",
        embedding=[0.1] * 1024,
    )

    session.add_all([chunk1, chunk2, chunk3])
    session.commit()

    from pgvector.sqlalchemy import Vector
    from sqlalchemy import literal

    with patch.object(Vector.comparator_factory, "cosine_distance", return_value=literal(0.05)):
        results = search_similar_chunks(
            db=session,
            organization_id=1,
            query_embedding=[0.1] * 1024,
            top_k=10,
        )

    retrieved_chunk_ids = [c.id for c, _, _ in results]
    retrieved_org_ids = [c.organization_id for c, _, _ in results]

    # Verify Chunk 1 returned
    assert 401 in retrieved_chunk_ids
    # Verify Chunk 2 (Org 2) is NEVER returned
    assert 402 not in retrieved_chunk_ids
    # Verify Chunk 3 (processing doc) is NEVER returned
    assert 403 not in retrieved_chunk_ids
    # All retrieved chunks belong strictly to Org 1
    assert all(org_id == 1 for org_id in retrieved_org_ids)
