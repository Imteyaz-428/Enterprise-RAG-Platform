from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import Base, engine
from core.errors import setup_error_handlers
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
