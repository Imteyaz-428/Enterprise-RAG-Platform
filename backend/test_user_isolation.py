import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from models.organization import Organization
from models.user import User
from models.document import Document
from models.document_chunk import DocumentChunk
from core.enums import UserRole
from schemas.user import UserUpdate
from crud.user import get_user_by_id, update_user, delete_user
from router.user import update_existing_user, delete_existing_user, get_user


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create two test organizations
    org1 = Organization(id=1, name="Org One", slug="org-one")
    org2 = Organization(id=2, name="Org Two", slug="org-two")
    session.add_all([org1, org2])
    session.commit()

    # Create users in Org 1
    admin_org1 = User(
        id=1,
        name="Admin Org1",
        email="admin@org1.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=1,
    )
    user_org1 = User(
        id=2,
        name="Employee Org1",
        email="emp@org1.com",
        password="hashedpassword",
        role=UserRole.EMPLOYEE,
        organization_id=1,
    )

    # Create user in Org 2
    user_org2 = User(
        id=3,
        name="Employee Org2",
        email="emp@org2.com",
        password="hashedpassword",
        role=UserRole.EMPLOYEE,
        organization_id=2,
    )

    admin_org2 = User(
        id=4,
        name="Admin Org2",
        email="admin@org2.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=2,
    )

    session.add_all([admin_org1, user_org1, user_org2, admin_org2])
    session.commit()

    yield session
    session.close()


# -----------------------------------------------------------------------------
# 1. Same-organization tests
# -----------------------------------------------------------------------------

def test_same_org_get_user_success(db_session):
    user = get_user_by_id(db=db_session, user_id=2, organization_id=1)
    assert user is not None
    assert user.id == 2
    assert user.organization_id == 1


def test_same_org_update_user_success(db_session):
    update_data = UserUpdate(name="Updated Employee 1")
    updated = update_user(
        db=db_session,
        user_id=2,
        user_update=update_data,
        organization_id=1,
    )
    assert updated.name == "Updated Employee 1"
    assert updated.organization_id == 1


def test_same_org_delete_user_success(db_session):
    result = delete_user(db=db_session, user_id=2, organization_id=1)
    assert result == {"message": "User deleted successfully."}
    assert db_session.query(User).filter(User.id == 2).first() is None


# -----------------------------------------------------------------------------
# 2. Cross-organization update tests
# -----------------------------------------------------------------------------

def test_cross_org_update_attempt_in_crud_raises_403(db_session):
    update_data = UserUpdate(name="Malicious Name Change")
    with pytest.raises(HTTPException) as exc_info:
        update_user(
            db=db_session,
            user_id=3,  # Belongs to Org 2
            user_update=update_data,
            organization_id=1,  # Admin is from Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Verify user 3 in Org 2 was NOT modified
    user_org2 = db_session.query(User).filter(User.id == 3).first()
    assert user_org2.name == "Employee Org2"


def test_cross_org_update_attempt_in_router_raises_403(db_session):
    admin_org1 = db_session.query(User).filter(User.id == 1).first()
    update_data = UserUpdate(name="Malicious Router Update")

    with pytest.raises(HTTPException) as exc_info:
        update_existing_user(
            user_id=3,  # Target in Org 2
            user_update=update_data,
            db=db_session,
            current_user=admin_org1,  # Admin of Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."


# -----------------------------------------------------------------------------
# 3. Cross-organization deletion tests
# -----------------------------------------------------------------------------

def test_cross_org_delete_attempt_in_crud_raises_403(db_session):
    with pytest.raises(HTTPException) as exc_info:
        delete_user(
            db=db_session,
            user_id=3,  # Belongs to Org 2
            organization_id=1,  # Admin is from Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Verify user 3 was NOT deleted
    user_org2 = db_session.query(User).filter(User.id == 3).first()
    assert user_org2 is not None
    assert user_org2.id == 3


def test_cross_org_delete_attempt_in_router_raises_403(db_session):
    admin_org1 = db_session.query(User).filter(User.id == 1).first()

    with pytest.raises(HTTPException) as exc_info:
        delete_existing_user(
            user_id=3,  # Belongs to Org 2
            db=db_session,
            current_user=admin_org1,  # Admin of Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Verify user 3 was NOT deleted
    assert db_session.query(User).filter(User.id == 3).first() is not None


# -----------------------------------------------------------------------------
# 4. IDOR and Client Input Tampering Tests
# -----------------------------------------------------------------------------

def test_nonexistent_user_returns_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_user_by_id(db=db_session, user_id=999, organization_id=1)
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        update_user(
            db=db_session,
            user_id=999,
            user_update=UserUpdate(name="Ghost"),
            organization_id=1,
        )
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        delete_user(db=db_session, user_id=999, organization_id=1)
    assert exc_info.value.status_code == 404


def test_cannot_delete_self(db_session):
    admin_org1 = db_session.query(User).filter(User.id == 1).first()
    with pytest.raises(HTTPException) as exc_info:
        delete_existing_user(
            user_id=1,
            db=db_session,
            current_user=admin_org1,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "You cannot delete your own account."


def test_non_admin_cannot_update_other_user(db_session):
    emp_org1 = db_session.query(User).filter(User.id == 2).first()
    update_data = UserUpdate(name="Hacked Name")

    with pytest.raises(HTTPException) as exc_info:
        update_existing_user(
            user_id=1,  # Try updating admin
            user_update=update_data,
            db=db_session,
            current_user=emp_org1,  # Regular employee
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You can only update your own profile."
