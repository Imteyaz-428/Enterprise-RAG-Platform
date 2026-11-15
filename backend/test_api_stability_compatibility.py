import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from models.organization import Organization
from models.user import User
from models.document import Document
from core.enums import UserRole
from router.document import router as document_router, get_document
from services.chat.reranking_service import get_optimal_device, RerankingService
from services.chat.retrieval_result import RetrievalResult
from types import SimpleNamespace


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[Organization.__table__, User.__table__, Document.__table__],
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test organizations
    org1 = Organization(id=1, name="Org One", slug="org-one")
    org2 = Organization(id=2, name="Org Two", slug="org-two")
    session.add_all([org1, org2])
    session.commit()

    # Create users
    user_org1 = User(
        id=1,
        name="User Org 1",
        email="user1@org1.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=1,
    )
    user_org2 = User(
        id=2,
        name="User Org 2",
        email="user2@org2.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=2,
    )
    session.add_all([user_org1, user_org2])
    session.commit()

    # Create documents
    doc_org1 = Document(
        id=10,
        title="Doc 10 Title",
        original_filename="doc10.pdf",
        stored_filename="uuid-doc10.pdf",
        file_path="/tmp/doc10.pdf",
        file_size=1024,
        organization_id=1,
        uploaded_by=1,
        status="completed",
    )
    doc_org2 = Document(
        id=20,
        title="Doc 20 Title",
        original_filename="doc20.pdf",
        stored_filename="uuid-doc20.pdf",
        file_path="/tmp/doc20.pdf",
        file_size=2048,
        organization_id=2,
        uploaded_by=2,
        status="completed",
    )
    session.add_all([doc_org1, doc_org2])
    session.commit()

    yield session
    session.close()


# -----------------------------------------------------------------------------
# ISSUE #3: Duplicate GET /documents/{id} Tests
# -----------------------------------------------------------------------------

def test_get_document_existing_success(db_session):
    user1 = db_session.query(User).filter(User.id == 1).first()
    doc = get_document(document_id=10, db=db_session, current_user=user1)
    assert doc is not None
    assert doc.id == 10
    assert doc.title == "Doc 10 Title"
    assert doc.organization_id == 1


def test_get_document_nonexistent_returns_404(db_session):
    user1 = db_session.query(User).filter(User.id == 1).first()
    with pytest.raises(HTTPException) as exc_info:
        get_document(document_id=9999, db=db_session, current_user=user1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found."


def test_get_document_cross_organization_returns_403(db_session):
    user1 = db_session.query(User).filter(User.id == 1).first()
    # User 1 tries to access Doc 20 (belongs to Org 2)
    with pytest.raises(HTTPException) as exc_info:
        get_document(document_id=20, db=db_session, current_user=user1)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."


def test_no_conflicting_duplicate_route_on_document_router():
    # Inspect route registration on document_router
    get_doc_routes = [
        route for route in document_router.routes
        if hasattr(route, "path") and route.path == "/documents/{document_id}" and "GET" in route.methods
    ]
    # Ensure exactly 1 handler is registered for GET /documents/{document_id}
    assert len(get_doc_routes) == 1
    assert get_doc_routes[0].endpoint.__name__ == "get_document"


# -----------------------------------------------------------------------------
# ISSUE #4: Dynamic Device Selection & CrossEncoder Tests
# -----------------------------------------------------------------------------

def test_get_optimal_device_mps():
    with patch("torch.backends.mps.is_available", return_value=True):
        assert get_optimal_device() == "mps"


def test_get_optimal_device_cuda():
    with patch("torch.backends.mps.is_available", return_value=False), \
         patch("torch.cuda.is_available", return_value=True):
        assert get_optimal_device() == "cuda"


def test_get_optimal_device_cpu():
    with patch("torch.backends.mps.is_available", return_value=False), \
         patch("torch.cuda.is_available", return_value=False):
        assert get_optimal_device() == "cpu"


def test_reranker_service_explicit_device_cpu():
    service = RerankingService(device="cpu")
    assert service.device == "cpu"


def test_reranker_service_rerank_accuracy_on_cpu():
    service = RerankingService(device="cpu")
    query = "What is static analysis?"

    doc = SimpleNamespace(id=1, original_filename="code.pdf")
    chunk_relevant = SimpleNamespace(
        id=101,
        chunk_text="Static code analysis inspects source code for security flaws without executing the program.",
    )
    chunk_irrelevant = SimpleNamespace(
        id=102,
        chunk_text="A chocolate cake recipe requires flour, cocoa powder, sugar and eggs.",
    )

    results = [
        RetrievalResult(chunk=chunk_irrelevant, document=doc, score=0.9),
        RetrievalResult(chunk=chunk_relevant, document=doc, score=0.1),
    ]

    reranked = service.rerank(query=query, results=results, top_k=2)

    assert len(reranked) == 2
    # The relevant chunk must be ranked first after reranking
    assert reranked[0].chunk.id == 101
    assert reranked[1].chunk.id == 102
