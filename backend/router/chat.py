from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from dependencies.database import get_db
from models.user import User
from schemas.chat import ChatRequest, ChatResponse
from schemas.chat_session import ChatSessionListResponse,ChatSessionDetailResponse
from services.chat.chat_service import ChatService
from schemas.chat_session import MessageResponse
from fastapi.responses import StreamingResponse

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

@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    stream = chat_service.chat_stream(
        db=db,
        question=request.question,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        session_id=request.session_id,
    )

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
    )

@router.get(
    "/sessions",
    response_model=List[ChatSessionListResponse],
)
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.get_user_sessions(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    
    
@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
)
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.get_chat_session(
        db=db,
        session_id=session_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    
@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.delete_chat_session(
        db=db,
        session_id=session_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )