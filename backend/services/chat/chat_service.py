from fastapi import HTTPException
from sqlalchemy.orm import Session

from crud.chat_message import (
    get_recent_messages,
    save_message,
)
from crud.chat_session import (
    create_session,
    get_session,
)
from models.chat_session import ChatSession
from services.ai.ai_services import AIService
from services.chat.prompt_service import PromptService
from services.chat.retrieval_service import RetrievalService


MAX_TITLE_LENGTH = 50


class ChatService:

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        prompt_service: PromptService | None = None,
        ai_service: AIService | None = None,
    ):
        self.retrieval_service = (
            retrieval_service or RetrievalService()
        )

        self.prompt_service = (
            prompt_service or PromptService()
        )

        self.ai_service = (
            ai_service or AIService()
        )

    def chat(
        self,
        db: Session,
        question: str,
        organization_id: int,
        user_id: int,
        session_id: int | None = None,
    ):

        session = self._get_or_create_session(
            db=db,
            session_id=session_id,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
        )

        save_message(
            db=db,
            session_id=session.id,
            role="user",
            content=question,
        )

        history = get_recent_messages(
            db=db,
            session_id=session.id,
        )

        chunks = self.retrieval_service.retrieve(
            db=db,
            question=question,
            organization_id=organization_id,
        )

        prompt = self.prompt_service.build_prompt(
            history=history,
            chunks=chunks,
            question=question,
        )

        answer = self.ai_service.generate_answer(
            prompt=prompt
        )

        save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=answer,
        )

        return {
            "session_id": session.id,
            "answer": answer,
        }

    def _generate_title(
        self,
        question: str,
    ) -> str:

        return question.strip()[:MAX_TITLE_LENGTH]

    def _get_or_create_session(
        self,
        db: Session,
        session_id: int | None,
        question: str,
        organization_id: int,
        user_id: int,
    ) -> ChatSession:

        if session_id is not None:

            session = get_session(
                db=db,
                session_id=session_id,
                organization_id=organization_id,
                user_id=user_id,
            )

            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail="Chat session not found or you do not have permission to access it.",
                )

            return session

        return create_session(
            db=db,
            title=self._generate_title(question),
            organization_id=organization_id,
            user_id=user_id,
        )