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
from schemas.organization import OrganizationUpdate
from crud.organization import (
    get_organization_by_id,
    update_organization,
    delete_organization,
    get_organizations,
)
from router.organization import (
    get_organization,
    get_all_organizations,
    update_org,
    delete_org,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create two test organizations
    org1 = Organization(id=1, name="Organization One", slug="org-one")
    org2 = Organization(id=2, name="Organization Two", slug="org-two")
    session.add_all([org1, org2])
    session.commit()

    # Create local admin in Org 1
    local_admin_org1 = User(
        id=1,
        name="Local Admin Org1",
        email="admin@org1.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=1,
    )

    # Create regular employee in Org 1
    employee_org1 = User(
        id=2,
        name="Employee Org1",
        email="employee@org1.com",
        password="hashedpassword",
        role=UserRole.EMPLOYEE,
        organization_id=1,
    )

    # Create local admin in Org 2
    local_admin_org2 = User(
        id=3,
        name="Local Admin Org2",
        email="admin@org2.com",
        password="hashedpassword",
        role=UserRole.ADMIN,
        organization_id=2,
    )

    # Create platform super admin (assigned to Org 1 for reference, but has super_admin role)
    platform_admin = User(
        id=4,
        name="Platform Super Admin",
        email="superadmin@platform.com",
        password="hashedpassword",
        role=UserRole.SUPER_ADMIN,
        organization_id=1,
    )

    session.add_all([local_admin_org1, employee_org1, local_admin_org2, platform_admin])
    session.commit()

    yield session
    session.close()


# -----------------------------------------------------------------------------
# 1. Local Admin: Own Organization Access
# -----------------------------------------------------------------------------

def test_local_admin_access_own_organization_success(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    org = get_organization(
        organization_id=1,
        db=db_session,
        current_user=admin,
    )
    assert org.id == 1
    assert org.name == "Organization One"


def test_local_admin_list_organizations_sees_only_own_org(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    orgs = get_all_organizations(
        db=db_session,
        current_user=admin,
    )
    assert len(orgs) == 1
    assert orgs[0].id == 1
    assert orgs[0].name == "Organization One"


def test_local_admin_update_own_organization_success(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    update_data = OrganizationUpdate(name="Organization One Renamed")
    updated = update_org(
        organization_id=1,
        organization_update=update_data,
        db=db_session,
        current_user=admin,
    )
    assert updated.name == "Organization One Renamed"


def test_local_admin_delete_own_organization_success(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    result = delete_org(
        organization_id=1,
        db=db_session,
        current_user=admin,
    )
    assert result == {"message": "Organization deleted successfully"}
    assert db_session.query(Organization).filter(Organization.id == 1).first() is None


# -----------------------------------------------------------------------------
# 2. Local Admin: Cross-Organization Restrictions (403 Forbidden)
# -----------------------------------------------------------------------------

def test_local_admin_access_another_organization_raises_403(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    with pytest.raises(HTTPException) as exc_info:
        get_organization(
            organization_id=2,  # Belongs to Org 2
            db=db_session,
            current_user=admin,  # From Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."


def test_local_admin_update_another_organization_raises_403(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    update_data = OrganizationUpdate(name="Malicious Takeover")
    with pytest.raises(HTTPException) as exc_info:
        update_org(
            organization_id=2,  # Belongs to Org 2
            organization_update=update_data,
            db=db_session,
            current_user=admin,  # From Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Verify Org 2 was not modified
    org2 = db_session.query(Organization).filter(Organization.id == 2).first()
    assert org2.name == "Organization Two"


def test_local_admin_delete_another_organization_raises_403(db_session):
    admin = db_session.query(User).filter(User.id == 1).first()
    with pytest.raises(HTTPException) as exc_info:
        delete_org(
            organization_id=2,  # Belongs to Org 2
            db=db_session,
            current_user=admin,  # From Org 1
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied."

    # Verify Org 2 was not deleted
    assert db_session.query(Organization).filter(Organization.id == 2).first() is not None


# -----------------------------------------------------------------------------
# 3. Platform Admin: Global Management Access
# -----------------------------------------------------------------------------

def test_platform_admin_can_list_all_organizations(db_session):
    platform_admin = db_session.query(User).filter(User.id == 4).first()
    orgs = get_all_organizations(
        db=db_session,
        current_user=platform_admin,
    )
    assert len(orgs) == 2
    org_ids = [org.id for org in orgs]
    assert 1 in org_ids
    assert 2 in org_ids


def test_platform_admin_can_access_any_organization(db_session):
    platform_admin = db_session.query(User).filter(User.id == 4).first()
    org2 = get_organization(
        organization_id=2,
        db=db_session,
        current_user=platform_admin,
    )
    assert org2.id == 2
    assert org2.name == "Organization Two"


def test_platform_admin_can_update_any_organization(db_session):
    platform_admin = db_session.query(User).filter(User.id == 4).first()
    update_data = OrganizationUpdate(name="Platform Updated Org Two")
    updated = update_org(
        organization_id=2,
        organization_update=update_data,
        db=db_session,
        current_user=platform_admin,
    )
    assert updated.name == "Platform Updated Org Two"


def test_platform_admin_can_delete_any_organization(db_session):
    platform_admin = db_session.query(User).filter(User.id == 4).first()
    result = delete_org(
        organization_id=2,
        db=db_session,
        current_user=platform_admin,
    )
    assert result == {"message": "Organization deleted successfully"}
    assert db_session.query(Organization).filter(Organization.id == 2).first() is None


# -----------------------------------------------------------------------------
# 4. Non-Admin (Employee) Restrictions
# -----------------------------------------------------------------------------

def test_employee_cannot_list_organizations(db_session):
    employee = db_session.query(User).filter(User.id == 2).first()
    with pytest.raises(HTTPException) as exc_info:
        get_all_organizations(
            db=db_session,
            current_user=employee,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


def test_employee_cannot_update_organization(db_session):
    employee = db_session.query(User).filter(User.id == 2).first()
    with pytest.raises(HTTPException) as exc_info:
        update_org(
            organization_id=1,
            organization_update=OrganizationUpdate(name="Employee Update"),
            db=db_session,
            current_user=employee,
        )
    assert exc_info.value.status_code == 403


def test_employee_cannot_delete_organization(db_session):
    employee = db_session.query(User).filter(User.id == 2).first()
    with pytest.raises(HTTPException) as exc_info:
        delete_org(
            organization_id=1,
            db=db_session,
            current_user=employee,
        )
    assert exc_info.value.status_code == 403
