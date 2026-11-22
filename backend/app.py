from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.database import Base, engine
from core.errors import setup_error_handlers
from core.security import validate_jwt_settings
from services.cache.redis_service import RedisService
from utils.logger import logger

from router.organization import router as organization_router
from router.user import router as user_router
from router.document import router as document_router
from router.chat import router as chat_router
from router.auth import router as auth_router

# Ensure models are imported so Base.metadata knows about them
import models.organization
import models.user
import models.document
import models.document_chunk
import models.chat_session
import models.chat_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate SECRET_KEY and ALGORITHM at startup, failing fast
    validate_jwt_settings()
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"Database schema initialization on startup skipped or failed: {e}")
    yield


app = FastAPI(
    title="Enterprise RAG Platform API",
    lifespan=lifespan,
)

setup_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://enterprise-rag-platform-three.vercel.app",
    ],
    allow_origin_regex=r"https://enterprise-rag-platform.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(organization_router)
app.include_router(user_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(auth_router)


@app.get("/")
def hello():
    return {"message": "hello world"}


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: no dependencies, always returns 200."""
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check(response: Response):
    """
    Readiness probe:
    - Checks DB connectivity with SELECT 1 (DB down -> 503).
    - Checks Redis connectivity via ping (Redis down -> 200 with redis='degraded').
    """
    # 1. Database check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness DB probe failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "unhealthy",
            "redis": "unknown",
        }

    # 2. Redis check
    try:
        redis_service = RedisService()
        redis_ok = redis_service.ping()
    except Exception as e:
        logger.warning(f"Readiness Redis probe failed: {e}")
        redis_ok = False

    if not redis_ok:
        return {
            "status": "degraded",
            "database": "healthy",
            "redis": "degraded",
        }

    return {
        "status": "healthy",
        "database": "healthy",
        "redis": "healthy",
    }
