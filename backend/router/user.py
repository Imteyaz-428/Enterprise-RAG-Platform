from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.dependencies import (
    get_current_user,
    require_role,
    has_role,
    is_platform_admin,
    UserRole,
)
from dependencies.database import get_db
from crud.user import (
    create_user,
    get_users,
    get_user_by_id,
    update_user,
    delete_user,
    change_password,
)
from schemas.user import UserCreate, UserResponse, UserUpdate, ChangePassword
from schemas.auth import Token
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN))
):
    if not has_role(current_admin, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return create_user(
        db=db,
        user=user,
        organization_id=current_admin.organization_id
    )


@router.get("/", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN))
):
    if not has_role(current_admin, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return get_users(
        db=db,
        organization_id=current_admin.organization_id
    )


@router.put("/change-password", status_code=status.HTTP_200_OK)
def update_password(
    data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_password(
        db=db,
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_existing_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    is_platform = is_platform_admin(current_user)
    is_admin = has_role(current_user, UserRole.ADMIN)

    # Scoped to caller's own organization unless platform admin (super_admin)
    if not is_platform and target_user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    # Creating, changing or deleting users and changing roles needs ADMIN
    # A non-admin user may only update their own profile, and cannot change roles
    if not is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile."
        )

    if not is_admin and user_update.role is not None and user_update.role != target_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to change user role."
        )

    return update_user(
        db=db,
        user_id=user_id,
        user_update=user_update,
        organization_id=None if is_platform else current_user.organization_id,
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_existing_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    if not has_role(current_user, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    is_platform = is_platform_admin(current_user)
    if not is_platform and target_user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return delete_user(
        db=db,
        user_id=user_id,
        organization_id=None if is_platform else current_user.organization_id,
    )


@router.post("/login", response_model=Token, deprecated=True, include_in_schema=False)
def deprecated_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    from router.auth import login as auth_login
    return auth_login(form_data=form_data, db=db)


@router.get("/me", response_model=UserResponse, deprecated=True, include_in_schema=False)
def deprecated_get_me(current_user: User = Depends(get_current_user)):
    from router.auth import get_me as auth_get_me
    return auth_get_me(current_user=current_user)


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    is_platform = is_platform_admin(current_user)
    if not is_platform and target_user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return get_user_by_id(
        db=db,
        user_id=user_id,
        organization_id=None if is_platform else current_user.organization_id,
    )




