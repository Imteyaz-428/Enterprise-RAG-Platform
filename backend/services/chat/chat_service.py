from fastapi import HTTPException
from sqlalchemy.orm import Session
from crud.chat_session import get_user_sessions as get_user_sessions_db
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
from crud.chat_message import get_session_messages as get_session_messages_db
from crud.chat_session import delete_session
import json


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

        session, prompt, citations = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )

        answer = self.ai_service.generate_answer(
            prompt=prompt,
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
            "citations": citations,
        }

    def _generate_title(self,question: str,) -> str:

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
        
    def _prepare_chat(
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

        results = self.retrieval_service.retrieve(
            db=db,
            question=question,
            organization_id=organization_id,
        )

        citations = []
        vis = set()

        for result in results:

            key = (
                result.document.id,
                result.chunk.chunk_index,
            )

            if key in vis:
                continue

            vis.add(key)

            citations.append(
                {
                    "document": result.document.original_filename,
                    "chunk_index": result.chunk.chunk_index,
                }
            )

        prompt = self.prompt_service.build_prompt(
            history=history,
            chunks=results,
            question=question,
        )

        return session, prompt, citations
            
    def get_user_sessions(self, db: Session,organization_id: int, user_id: int):
        
        return get_user_sessions_db(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        
        
    def get_chat_session(
        self,
        db: Session,
        session_id: int,
        organization_id: int,
        user_id: int,
    ):
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

        messages = get_session_messages_db(
            db=db,
            session_id=session.id,
        )

        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "messages": messages,
        }
        
    def delete_chat_session(
        self,
        db: Session,
        session_id: int,
        organization_id: int,
        user_id: int,
    ):
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

        delete_session(
            db=db,
            session=session,
        )

        return {
            "message": "Chat deleted successfully."
        }
        
    def chat_stream(
        self,
        db: Session,
        question: str,
        organization_id: int,
        user_id: int,
        session_id: int | None = None,
    ):

        session, prompt, citations = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )

        yield (
            f"event: metadata\n"
            f"data: {json.dumps({'session_id': session.id, 'citations': citations})}\n\n"
        )

        tokens = []

        try:

            for token in self.ai_service.stream_answer(
                prompt=prompt,
            ):

                tokens.append(token)

                yield (
                    f"event: token\n"
                    f"data: {token}\n\n"
                )

        finally:

            if tokens:

                answer = "".join(tokens)

                save_message(
                    db=db,
                    session_id=session.id,
                    role="assistant",
                    content=answer,
                )

        yield (
            "event: done\n"
            "data: {}\n\n"
        )