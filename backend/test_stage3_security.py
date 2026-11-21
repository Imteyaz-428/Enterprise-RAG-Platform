import io
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt

from database.database import Base
from models import Organization, User, Document, DocumentChunk, ChatSession, ChatMessage
from core.enums import UserRole
from core.security import (
    create_access_token,
    create_refresh_token,
    validate_jwt_settings,
    SECRET_KEY,
    ALGORITHM,
    hash_password,
)
from core.dependencies import get_current_user, has_role, get_role_rank
from dependencies.database import get_db
from app import app
from schemas.user import UserUpdate, UserCreate
from schemas.auth import SignupRequest, RefreshTokenRequest
from router.document import upload_document, remove_document, get_document, list_documents
from router.user import (
    create_new_user,
    update_existing_user,
    delete_existing_user,
    get_user,
)
from router.organization import (
    get_organization,
    get_all_organizations,
    update_org,
    delete_org,
)
from schemas.organization import OrganizationUpdate


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Create two organizations
    org1 = Organization(id=1, name="Org One", slug="org-one")
    org2 = Organization(id=2, name="Org Two", slug="org-two")
    session.add_all([org1, org2])
    session.commit()

    # Create users with all roles
    super_admin = User(
        id=1,
        name="Super Admin",
        email="super@platform.com",
        password=hash_password("password123"),
        role=UserRole.SUPER_ADMIN,
        organization_id=1,
    )
    admin_org1 = User(
        id=2,
        name="Admin Org1",
        email="admin@org1.com",
        password=hash_password("password123"),
        role=UserRole.ADMIN,
        organization_id=1,
    )
    manager_org1 = User(
        id=3,
        name="Manager Org1",
        email="manager@org1.com",
        password=hash_password("password123"),
        role=UserRole.MANAGER,
        organization_id=1,
    )
    employee_org1 = User(
        id=4,
        name="Employee Org1",
        email="emp@org1.com",
        password=hash_password("password123"),
        role=UserRole.EMPLOYEE,
        organization_id=1,
    )
    admin_org2 = User(
        id=5,
        name="Admin Org2",
        email="admin@org2.com",
        password=hash_password("password123"),
        role=UserRole.ADMIN,
        organization_id=2,
    )
    employee_org2 = User(
        id=6,
        name="Employee Org2",
        email="emp@org2.com",
        password=hash_password("password123"),
        role=UserRole.EMPLOYEE,
        organization_id=2,
    )

    session.add_all([super_admin, admin_org1, manager_org1, employee_org1, admin_org2, employee_org2])
    session.commit()

    # Create test documents
    doc1 = Document(
        id=1,
        title="Doc 1",
        original_filename="doc1.pdf",
        stored_filename="doc1_uuid.pdf",
        file_path="/tmp/doc1.pdf",
        file_size=1024,
        organization_id=1,
        uploaded_by=3,
    )
    doc2 = Document(
        id=2,
        title="Doc 2",
        original_filename="doc2.pdf",
        stored_filename="doc2_uuid.pdf",
        file_path="/tmp/doc2.pdf",
        file_size=2048,
        organization_id=2,
        uploaded_by=5,
    )
    session.add_all([doc1, doc2])
    session.commit()

    yield session, TestingSession
    session.close()


@pytest.fixture
def client(db_session):
    session, TestingSession = db_session

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# 1. RBAC Hierarchy & Permissions
# =============================================================================

def test_role_hierarchy_ranks():
    """Verify SUPER_ADMIN > ADMIN > MANAGER > EMPLOYEE."""
    assert get_role_rank(UserRole.SUPER_ADMIN) > get_role_rank(UserRole.ADMIN)
    assert get_role_rank(UserRole.ADMIN) > get_role_rank(UserRole.MANAGER)
    assert get_role_rank(UserRole.MANAGER) > get_role_rank(UserRole.EMPLOYEE)
    assert get_role_rank("user") == get_role_rank(UserRole.EMPLOYEE)


def test_document_upload_role_hierarchy(db_session, monkeypatch):
    """Upload documents needs MANAGER or higher."""
    session, _ = db_session
    emp = session.query(User).filter_by(id=4).first()
    mgr = session.query(User).filter_by(id=3).first()
    admin = session.query(User).filter_by(id=2).first()
    super_admin = session.query(User).filter_by(id=1).first()

    class DummyFile:
        filename = "test.pdf"
        content_type = "application/pdf"
        size = 100
        file = io.BytesIO(b"%PDF-1.4 sample content")

    class DummyBgTasks:
        def add_task(self, *args, **kwargs):
            pass

    # EMPLOYEE -> 403 Forbidden
    from core.dependencies import require_role
    checker = require_role(UserRole.MANAGER)
    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=emp)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Manager access required"

    # MANAGER -> Allowed
    assert checker(current_user=mgr) == mgr

    # ADMIN -> Allowed (higher passes lower)
    assert checker(current_user=admin) == admin

    # SUPER_ADMIN -> Allowed
    assert checker(current_user=super_admin) == super_admin


def test_document_delete_role_hierarchy(db_session):
    """Delete documents needs MANAGER or higher and scoped to org."""
    session, _ = db_session
    emp = session.query(User).filter_by(id=4).first()
    mgr = session.query(User).filter_by(id=3).first()
    admin_org2 = session.query(User).filter_by(id=5).first()
    super_admin = session.query(User).filter_by(id=1).first()

    # EMPLOYEE calling remove_document -> 403
    from core.dependencies import require_role
    checker = require_role(UserRole.MANAGER)
    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=emp)
    assert exc_info.value.status_code == 403

    # Cross-org delete by admin in Org 2 on Org 1 doc -> 403
    with pytest.raises(HTTPException) as exc_info:
        remove_document(document_id=1, db=session, current_user=admin_org2)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # SUPER_ADMIN can delete across orgs
    result = remove_document(document_id=2, db=session, current_user=super_admin)
    assert result == {"message": "Document deleted successfully"}
    assert session.query(Document).filter_by(id=2).first() is None


def test_document_list_and_view_any_logged_in_user(db_session):
    """List and view documents needs any logged-in user."""
    session, _ = db_session
    emp = session.query(User).filter_by(id=4).first()
    admin_org2 = session.query(User).filter_by(id=5).first()
    super_admin = session.query(User).filter_by(id=1).first()

    # Employee can list and view documents in own org
    docs = list_documents(db=session, current_user=emp)
    assert len(docs) >= 1

    doc = get_document(document_id=1, db=session, current_user=emp)
    assert doc.id == 1

    # Employee or Admin from Org 2 cannot view Org 1 document -> 403
    with pytest.raises(HTTPException) as exc_info:
        get_document(document_id=1, db=session, current_user=admin_org2)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # SUPER_ADMIN can view Org 1 document even from outside
    doc_super = get_document(document_id=1, db=session, current_user=super_admin)
    assert doc_super.id == 1


def test_user_management_role_requirements(db_session):
    """Creating, changing, or deleting users and changing roles needs ADMIN."""
    session, _ = db_session
    emp = session.query(User).filter_by(id=4).first()
    mgr = session.query(User).filter_by(id=3).first()
    admin = session.query(User).filter_by(id=2).first()

    # EMPLOYEE or MANAGER cannot create user -> 403
    from core.dependencies import require_role
    admin_checker = require_role(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(current_user=emp)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"

    with pytest.raises(HTTPException) as exc_info:
        admin_checker(current_user=mgr)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"

    # EMPLOYEE cannot delete user -> 403
    with pytest.raises(HTTPException) as exc_info:
        delete_existing_user(user_id=3, db=session, current_user=emp)
    assert exc_info.value.status_code == 403

    # Cannot delete own account -> 400
    with pytest.raises(HTTPException) as exc_info:
        delete_existing_user(user_id=admin.id, db=session, current_user=admin)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "You cannot delete your own account."

    # Non-admin cannot change another user -> 403
    with pytest.raises(HTTPException) as exc_info:
        update_existing_user(user_id=2, user_update=UserUpdate(name="Hacked"), db=session, current_user=emp)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You can only update your own profile."

    # Non-admin cannot change their own role -> 403
    with pytest.raises(HTTPException) as exc_info:
        update_existing_user(user_id=emp.id, user_update=UserUpdate(role=UserRole.ADMIN), db=session, current_user=emp)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required to change user role."

    # Admin can change user in own org
    updated = update_existing_user(
        user_id=4,
        user_update=UserUpdate(name="Promoted Emp", role=UserRole.MANAGER),
        db=session,
        current_user=admin,
    )
    assert updated.name == "Promoted Emp"
    assert updated.role == UserRole.MANAGER


def test_cross_org_user_management(db_session):
    """Admin cannot manage users across organizations; only SUPER_ADMIN can."""
    session, _ = db_session
    admin_org1 = session.query(User).filter_by(id=2).first()
    super_admin = session.query(User).filter_by(id=1).first()

    # Admin Org 1 tries to view user in Org 2 -> 403
    with pytest.raises(HTTPException) as exc_info:
        get_user(user_id=5, db=session, current_user=admin_org1)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Admin Org 1 tries to update user in Org 2 -> 403
    with pytest.raises(HTTPException) as exc_info:
        update_existing_user(user_id=5, user_update=UserUpdate(name="Cross Org"), db=session, current_user=admin_org1)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Admin Org 1 tries to delete user in Org 2 -> 403
    with pytest.raises(HTTPException) as exc_info:
        delete_existing_user(user_id=5, db=session, current_user=admin_org1)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # SUPER_ADMIN can view and update across organizations
    u = get_user(user_id=5, db=session, current_user=super_admin)
    assert u.id == 5


# =============================================================================
# 2. Auth Hardening (Startup Validation, Refresh Flow, Signup Validation)
# =============================================================================

def test_startup_validation_fast_fail():
    """validate_jwt_settings validates SECRET_KEY (>= 32 chars) and ALGORITHM."""
    # Key too short (< 32 chars) -> raises ValueError
    with pytest.raises(ValueError) as exc:
        validate_jwt_settings(secret_key="shortkey", algorithm="HS256")
    assert "at least 32 characters" in str(exc.value)

    # Missing key -> raises ValueError
    with pytest.raises(ValueError) as exc:
        validate_jwt_settings(secret_key="", algorithm="HS256")
    assert "SECRET_KEY must be set" in str(exc.value)

    # Invalid algorithm -> raises ValueError
    with pytest.raises(ValueError) as exc:
        validate_jwt_settings(secret_key="a" * 32, algorithm="INVALID_ALG")
    assert "ALGORITHM must be set and one of" in str(exc.value)

    # Valid settings -> passes without error
    validate_jwt_settings(secret_key="a" * 32, algorithm="HS256")


def test_refresh_token_creation_and_rejection(db_session):
    """Access tokens get type='access'; refresh tokens get type='refresh'.
    get_current_user must reject refresh tokens."""
    session, _ = db_session
    user = session.query(User).filter_by(id=2).first()

    access_tok = create_access_token({"sub": str(user.id)})
    refresh_tok = create_refresh_token({"sub": str(user.id)})

    # Decode and check claims
    access_claims = jwt.decode(access_tok, SECRET_KEY, algorithms=[ALGORITHM])
    assert access_claims["type"] == "access"

    refresh_claims = jwt.decode(refresh_tok, SECRET_KEY, algorithms=[ALGORITHM])
    assert refresh_claims["type"] == "refresh"

    # get_current_user accepts access token
    current_u = get_current_user(token=access_tok, db=session)
    assert current_u.id == user.id

    # get_current_user rejects refresh token with 401
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=refresh_tok, db=session)
    assert exc_info.value.status_code == 401
    assert "refresh token cannot be used as access token" in exc_info.value.detail


def test_refresh_endpoint_flow(client, db_session):
    """POST /auth/refresh returns a new access token when given a valid refresh token."""
    session, _ = db_session
    user = session.query(User).filter_by(id=2).first()
    refresh_tok = create_refresh_token({"sub": str(user.id)})

    # Valid refresh token returns new access token
    res = client.post("/auth/refresh", json={"refresh_token": refresh_tok})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify newly issued access token is valid and has type="access"
    new_token = data["access_token"]
    payload = jwt.decode(new_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["type"] == "access"
    assert payload["sub"] == str(user.id)

    # Passing an access token to /auth/refresh fails with 401
    access_tok = create_access_token({"sub": str(user.id)})
    res_bad = client.post("/auth/refresh", json={"refresh_token": access_tok})
    assert res_bad.status_code == 401
    assert "refresh token expected" in res_bad.json()["detail"]


def test_signup_validation_422(client):
    """SignupRequest enforces password >= 8 chars and slug pattern; returns 422, never 500."""
    # Password < 8 characters -> 422
    res1 = client.post(
        "/auth/signup",
        json={
            "organization_name": "Valid Org",
            "organization_slug": "valid-slug",
            "name": "Valid User",
            "email": "valid@example.com",
            "password": "short",
        },
    )
    assert res1.status_code == 422

    # Invalid slug (uppercase / special symbols) -> 422
    res2 = client.post(
        "/auth/signup",
        json={
            "organization_name": "Valid Org",
            "organization_slug": "INVALID_SLUG!!",
            "name": "Valid User",
            "email": "valid2@example.com",
            "password": "securepassword123",
        },
    )
    assert res2.status_code == 422

    # Short name -> 422
    res3 = client.post(
        "/auth/signup",
        json={
            "organization_name": "V",
            "organization_slug": "valid-slug",
            "name": "Valid User",
            "email": "valid3@example.com",
            "password": "securepassword123",
        },
    )
    assert res3.status_code == 422

    # Valid signup -> 200 with tokens
    res_valid = client.post(
        "/auth/signup",
        json={
            "organization_name": "Success Org",
            "organization_slug": "success-org",
            "name": "Admin User",
            "email": "admin@success.com",
            "password": "securepassword123",
        },
    )
    assert res_valid.status_code == 200
    token_data = res_valid.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data


# =============================================================================
# 3. Deprecated Endpoints & Delete Response Shapes
# =============================================================================

def test_deprecated_routes_still_work(client, db_session):
    """Deprecated /users/login and /users/me still work."""
    session, _ = db_session
    user = session.query(User).filter_by(id=2).first()

    # /users/login
    res_login = client.post(
        "/users/login",
        data={"username": "admin@org1.com", "password": "password123"},
    )
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data

    # /users/me
    token = token_data["access_token"]
    res_me = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "admin@org1.com"


def test_delete_endpoints_uniform_response_shape(db_session):
    """Verify delete endpoints return uniform shape {'message': str}."""
    session, _ = db_session
    super_admin = session.query(User).filter_by(id=1).first()

    # Document delete
    doc_res = remove_document(document_id=1, db=session, current_user=super_admin)
    assert isinstance(doc_res, dict)
    assert "message" in doc_res

    # User delete
    user_res = delete_existing_user(user_id=4, db=session, current_user=super_admin)
    assert isinstance(user_res, dict)
    assert "message" in user_res

    # Organization delete
    org_res = delete_org(organization_id=2, db=session, current_user=super_admin)
    assert isinstance(org_res, dict)
    assert "message" in org_res
