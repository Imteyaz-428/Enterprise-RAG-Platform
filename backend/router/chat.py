from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependencies.database import get_db
from core.dependencies import get_current_user
from crud.chat import generate_rag_answer
from models.user import User
from schemas.chat import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("", response_model=ChatResponse)
def chat_with_document(request: ChatRequest,db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    return generate_rag_answer(
        db=db,
        current_user=current_user,
        document_id=request.document_id,
        question=request.question
    )