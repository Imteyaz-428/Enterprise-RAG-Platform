import os
from pathlib import Path
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("SECRET_KEY"):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
SUPPORTED_ALGORITHMS = ["HS256", "HS384", "HS512"]

def validate_jwt_settings(secret_key: str = None, algorithm: str = None):
    """Validate SECRET_KEY (present, at least 32 chars) and ALGORITHM at startup, failing fast with a clear error."""
    key = secret_key if secret_key is not None else os.getenv("SECRET_KEY") or SECRET_KEY
    alg = algorithm if algorithm is not None else os.getenv("ALGORITHM") or ALGORITHM

    if not key or len(key) < 32:
        raise ValueError("SECRET_KEY must be set and at least 32 characters long.")

    if not alg or alg not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"ALGORITHM must be set and one of {SUPPORTED_ALGORITHMS}.")

def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt
