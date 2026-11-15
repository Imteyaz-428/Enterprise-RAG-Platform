from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.organization import Organization
from schemas.organization import OrganizationCreate,OrganizationUpdate


def create_organization(db: Session, organization: OrganizationCreate):

    db_organization = Organization(

        name=organization.name,

        slug=organization.slug

    )

    db.add(db_organization)

    db.flush()

    db.refresh(db_organization)

    return db_organization

def get_organizations(db: Session):
    return db.query(Organization).all()


def get_organization_by_id(
    db: Session,
    organization_id: int,
    user_organization_id: int | None = None,
    is_platform_admin: bool = False,
):
    if not is_platform_admin and user_organization_id is not None and user_organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return organization


def update_organization(
    db: Session,
    organization_id: int,
    organization_update: OrganizationUpdate,
    user_organization_id: int | None = None,
    is_platform_admin: bool = False,
):
    if not is_platform_admin and user_organization_id is not None and user_organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    update_data = organization_update.model_dump(exclude_unset=True)
    update_data.pop("id", None)

    for key, val in update_data.items():
        setattr(organization, key, val)

    db.commit()
    db.refresh(organization)
    return organization


def delete_organization(
    db: Session,
    organization_id: int,
    user_organization_id: int | None = None,
    is_platform_admin: bool = False,
):
    if not is_platform_admin and user_organization_id is not None and user_organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    organization = db.query(Organization).filter(Organization.id == organization_id).first()

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    db.delete(organization)
    db.commit()

    return {
        "message": "Organization deleted successfully"
    }