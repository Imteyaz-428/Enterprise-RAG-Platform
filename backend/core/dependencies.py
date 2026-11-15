from fastapi import HTTPException, status,Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dependencies.database import get_db
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
from models.user import User
from core.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login"
)

def get_current_user( token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        return user
        
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )



PLATFORM_ADMIN_ROLES = {"super_admin", "platform_admin"}


def is_platform_admin(user: User) -> bool:
    if not user or not user.role:
        return False
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role_val.lower() in PLATFORM_ADMIN_ROLES


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required"
        )
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val != "admin" and not is_platform_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user



def require_role(required_role: UserRole):

    def role_checker(current_user: User = Depends(get_current_user)):
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        req_val = required_role.value if hasattr(required_role, "value") else str(required_role)

        if role_val != req_val and not is_platform_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail=f"{req_val} access required"
            )

        return current_user

    return role_checker