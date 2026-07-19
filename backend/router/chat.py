from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from dependencies.database import get_db
from models.user import User
from schemas.chat import ChatRequest, ChatResponse
from services.chat.chat_service import ChatService

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

chat_service = ChatService()


@router.post(
    "",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.chat(
        db=db,
        question=request.question,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        session_id=request.session_id,
    )