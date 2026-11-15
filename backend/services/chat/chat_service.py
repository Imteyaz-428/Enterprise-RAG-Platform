import hashlib
import json
from typing import Any, Dict, List, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session

from crud.chat_message import (
    get_recent_messages,
    get_session_messages as get_session_messages_db,
    save_message,
)
from crud.chat_session import (
    create_session,
    delete_session,
    get_session,
    get_user_sessions as get_user_sessions_db,
)
from models.chat_session import ChatSession
from services.ai.ai_services import AIService
from services.cache.redis_service import RedisService
from services.chat.prompt_service import PromptService
from services.chat.retrieval_service import RetrievalService
from utils.logger import logger

MAX_TITLE_LENGTH = 50


class ChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        prompt_service: PromptService | None = None,
        ai_service: AIService | None = None,
        redis: RedisService | None = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.prompt_service = prompt_service or PromptService()
        self.ai_service = ai_service or AIService()
        self.redis = redis or RedisService()

    def chat(
        self,
        db: Session,
        question: str,
        organization_id: int,
        user_id: int,
        session_id: int | None = None,
    ) -> Dict[str, Any]:
        """
        Executes a synchronous, non-streaming chat request:
        1. Prepares session, conversation history, document retrieval, citations, and prompt.
        2. Checks Redis cache for exact question hit within the tenant.
        3. If cache miss, generates answer via AI provider fallback architecture.
        4. Saves assistant message to database and caches result in Redis.
        5. Returns structured ChatResponse dict.
        """
        session, prompt, citations = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )
        cache_key = self._get_cache_key(
            organization_id=organization_id,
            question=question,
        )

        try:
            cached = self.redis.get(cache_key)
        except Exception as e:
            logger.warning(f"Redis get failed in chat(): {e}")
            cached = None

        if cached and isinstance(cached, dict) and "answer" in cached and "citations" in cached:
            logger.info(f"Redis Cache Hit for session {session.id}")
            save_message(
                db=db,
                session_id=session.id,
                role="assistant",
                content=cached["answer"],
                citations=cached["citations"],
            )
            return {
                "session_id": session.id,
                "answer": cached["answer"],
                "citations": cached["citations"],
            }

        logger.info(f"Redis Cache Miss for session {session.id}, generating answer via AI")
        try:
            answer = self.ai_service.generate_answer(
                prompt=prompt,
            )
        except Exception as e:
            safe_err = self.ai_service._sanitize_error(str(e))
            logger.error(f"AI generation failed in chat(): {safe_err}")
            raise HTTPException(
                status_code=503,
                detail="AI service is currently unavailable. Please try again later.",
            )

        save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=answer,
            citations=citations,
        )

        response = {
            "answer": answer,
            "citations": citations,
        }

        try:
            self.redis.set(
                cache_key,
                response,
            )
        except Exception as e:
            logger.warning(f"Redis set failed in chat(): {e}")

        return {
            "session_id": session.id,
            **response,
        }

    def _generate_title(self, question: str) -> str:
        cleaned = question.strip()
        return cleaned[:MAX_TITLE_LENGTH] if cleaned else "New Chat"

    def _get_cache_key(self, organization_id: int, question: str) -> str:
        digest = hashlib.sha256(question.strip().lower().encode()).hexdigest()
        return f"cache:{organization_id}:{digest}"

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
    ) -> Tuple[ChatSession, str, List[Dict[str, Any]]]:
        session = self._get_or_create_session(
            db=db,
            session_id=session_id,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Fetch previous conversation history before saving current user question
        history = get_recent_messages(
            db=db,
            session_id=session.id,
        )

        # Persist user question
        save_message(
            db=db,
            session_id=session.id,
            role="user",
            content=question,
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

    def get_user_sessions(self, db: Session, organization_id: int, user_id: int):
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
        """
        Executes a streaming SSE chat request:
        1. Emits event: metadata (session_id, citations)
        2. Emits event: token (iteratively for each token)
        3. Persists complete assistant message and writes to cache
        4. Emits event: done
        5. If failure occurs before or during token generation, emits event: error followed by event: done.
        """
        session, prompt, citations = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )
        cache_key = self._get_cache_key(
            organization_id=organization_id,
            question=question,
        )

        try:
            cached = self.redis.get(cache_key)
        except Exception as e:
            logger.warning(f"Redis get failed in chat_stream(): {e}")
            cached = None

        if cached and isinstance(cached, dict) and "answer" in cached and "citations" in cached:
            logger.info(f"Redis Cache Hit in stream for session {session.id}")
            save_message(
                db=db,
                session_id=session.id,
                role="assistant",
                content=cached["answer"],
                citations=cached["citations"],
            )

            yield (
                f"event: metadata\n"
                f"data: {json.dumps({'session_id': session.id, 'citations': cached['citations']})}\n\n"
            )

            for token in cached["answer"].split(" "):
                yield (
                    f"event: token\n"
                    f"data: {token} \n\n"
                )

            yield (
                "event: done\n"
                "data: {}\n\n"
            )
            return

        logger.info(f"Redis Cache Miss in stream for session {session.id}")

        yield (
            f"event: metadata\n"
            f"data: {json.dumps({'session_id': session.id, 'citations': citations})}\n\n"
        )

        tokens = []
        completed_successfully = False

        try:
            for token in self.ai_service.stream_answer(
                prompt=prompt,
            ):
                tokens.append(token)
                yield (
                    f"event: token\n"
                    f"data: {token}\n\n"
                )
            completed_successfully = True
        except Exception as e:
            safe_err = self.ai_service._sanitize_error(str(e))
            logger.error(f"Streaming error in chat_stream: {safe_err}")

            # Terminal error event: no token event is emitted after this
            yield (
                f"event: error\n"
                f"data: {json.dumps({'error': 'AI provider generation failed. Please try again later.'})}\n\n"
            )
            yield (
                "event: done\n"
                "data: {}\n\n"
            )
            return
        finally:
            if tokens and completed_successfully:
                answer = "".join(tokens)
                save_message(
                    db=db,
                    session_id=session.id,
                    role="assistant",
                    content=answer,
                    citations=citations,
                )
                try:
                    self.redis.set(
                        cache_key,
                        {
                            "answer": answer,
                            "citations": citations,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Redis set failed in chat_stream(): {e}")

        yield (
            "event: done\n"
            "data: {}\n\n"
        )

    def check_providers_health(self):
        """Delegates provider health check to AIService."""
        return self.ai_service.check_providers_health()
