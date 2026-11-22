from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from crud.organization import (
    create_organization,
    get_organizations,
    get_organization_by_id,
    update_organization,
    delete_organization,
)
from core.dependencies import (
    get_current_user,
    is_platform_admin,
    require_platform_admin,
    has_role,
    UserRole,
)
from dependencies.database import get_db
from schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from models.user import User

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_org(
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    return create_organization(db, organization)


@router.get("/", response_model=list[OrganizationResponse])
def get_all_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if is_platform_admin(current_user):
        return get_organizations(db)

    if has_role(current_user, UserRole.ADMIN):
        return [get_organization_by_id(db, current_user.organization_id)]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_platform = is_platform_admin(current_user)

    if not is_platform and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return get_organization_by_id(
        db=db,
        organization_id=organization_id,
        user_organization_id=current_user.organization_id,
        is_platform_admin=is_platform,
    )


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_org(
    organization_id: int,
    organization_update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_platform = is_platform_admin(current_user)

    if not is_platform and not has_role(current_user, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    if not is_platform and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return update_organization(
        db=db,
        organization_id=organization_id,
        organization_update=organization_update,
        user_organization_id=current_user.organization_id,
        is_platform_admin=is_platform,
    )


@router.delete("/{organization_id}")
def delete_org(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_platform = is_platform_admin(current_user)

    if not is_platform and not has_role(current_user, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    if not is_platform and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return delete_organization(
        db=db,
        organization_id=organization_id,
        user_organization_id=current_user.organization_id,
        is_platform_admin=is_platform,
    )