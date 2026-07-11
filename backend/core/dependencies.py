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



def get_current_admin(current_user: User = Depends(get_current_user)):

    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user



def require_role(required_role: UserRole):

    def role_checker(current_user: User = Depends(get_current_user)):

        if current_user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"{required_role.value} access required"
            )

        return current_user

    return role_checker