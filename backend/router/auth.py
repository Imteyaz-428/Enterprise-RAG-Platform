from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from core.security import create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM
from core.dependencies import get_current_user
from dependencies.database import get_db
from crud.user import authenticate_user
from crud.auth import signup
from schemas.user import UserResponse
from schemas.auth import Token, RefreshTokenRequest, SignupRequest
from models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/signup", response_model=Token)
def signup_user(
    data: SignupRequest,
    db: Session = Depends(get_db)
):
    return signup(
        db=db,
        data=data
    )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(
        db,
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "email": user.email,
            "organization_id": user.organization_id
        }
    )
    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            data.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token expected"
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

    new_access_token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "email": user.email,
            "organization_id": user.organization_id
        }
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

