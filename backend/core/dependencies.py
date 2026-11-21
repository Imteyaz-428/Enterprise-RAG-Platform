from typing import Union
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dependencies.database import get_db
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
from models.user import User
from core.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

# Role Hierarchy: SUPER_ADMIN > ADMIN > MANAGER > EMPLOYEE (where EMPLOYEE = standard User)
ROLE_HIERARCHY = {
    UserRole.EMPLOYEE: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}

PLATFORM_ADMIN_ROLES = {"super_admin", "platform_admin"}


def get_role_rank(role: Union[UserRole, str]) -> int:
    if isinstance(role, UserRole):
        return ROLE_HIERARCHY.get(role, 0)
    if isinstance(role, str):
        role_lower = role.lower()
        if role_lower in ("super_admin", "platform_admin", "superadmin"):
            return 4
        if role_lower == "admin":
            return 3
        if role_lower == "manager":
            return 2
        if role_lower in ("employee", "user"):
            return 1
    return 0


def has_role(user: User, minimum_role: Union[UserRole, str]) -> bool:
    if not user or not user.role:
        return False
    user_rank = get_role_rank(user.role)
    req_rank = get_role_rank(minimum_role)
    return user_rank >= req_rank


def is_platform_admin(user: User) -> bool:
    if not user or not user.role:
        return False
    return get_role_rank(user.role) >= 4


def is_super_admin(user: User) -> bool:
    return is_platform_admin(user)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        token_type = payload.get("type")
        if token_type == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: refresh token cannot be used as access token"
            )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: invalid subject format"
            )

        user = db.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required"
        )
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)):
    if not has_role(current_user, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_role(required_role: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)):
        if not has_role(current_user, required_role):
            req_val = required_role.value if hasattr(required_role, "value") else str(required_role)
            if req_val == "admin":
                msg = "Admin access required"
            elif req_val == "manager":
                msg = "Manager access required"
            elif req_val in ("super_admin", "platform_admin"):
                msg = "Platform administrator access required"
            else:
                msg = f"{req_val} access required"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=msg
            )
        return current_user

    return role_checker
