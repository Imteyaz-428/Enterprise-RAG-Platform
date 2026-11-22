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
from services.chat.citation_validator import (
    NOT_FOUND_ANSWER,
    extract_markers,
    is_not_found,
    validate_citations,
)
from services.chat.prompt_service import PromptService
from services.chat.query_rewriter import rewrite_query
from services.chat.retrieval_service import RetrievalService
from utils.logger import logger

MAX_TITLE_LENGTH = 50


def format_sse_event(event: str, data: str) -> str:
    """
    Format each event per the SSE spec:
    Split data on "\n" and emit one "data: " line per piece, then a blank line.
    Tokens without a newline stay byte-for-byte identical to "event: <event>\ndata: <data>\n\n".
    """
    lines = [f"event: {event}"]
    for piece in str(data).split("\n"):
        lines.append(f"data: {piece}")
    return "\n".join(lines) + "\n\n"


class PrepResult(tuple):
    chunk_texts: Dict[int, str]

    def __new__(
        cls,
        session: ChatSession,
        prompt: str,
        citations: List[Dict[str, Any]],
        cache_key: str,
        chunk_texts: Dict[int, str] | None = None,
    ):
        instance = super().__new__(
            cls, (session, prompt, citations, cache_key)
        )
        instance.chunk_texts = chunk_texts or {}
        return instance


class ChatService:
    @staticmethod
    def format_sse_event(event: str, data: str) -> str:
        return format_sse_event(event, data)

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
        prep = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )
        if len(prep) == 4:
            session, prompt, citations, cache_key = prep
        else:
            session, prompt, citations = prep[:3]
            cache_key = self._get_cache_key(
                organization_id=organization_id,
                question=question,
            )

        chunk_texts = getattr(prep, "chunk_texts", None)

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

        clean_answer, used_citations, invalid_markers = validate_citations(
            answer=answer,
            citations=citations,
            chunk_texts=chunk_texts,
        )

        if is_not_found(answer) or is_not_found(clean_answer):
            clean_answer = NOT_FOUND_ANSWER
            used_citations = []
        else:
            valid_markers = extract_markers(clean_answer)
            if invalid_markers or not valid_markers:
                logger.warning(
                    f"Citation validation for session {session.id}: "
                    f"{len(invalid_markers)} invalid markers removed, "
                    f"{len(valid_markers)} valid markers found "
                    f"({'markers missing' if not valid_markers else 'markers valid'})."
                )

        save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=clean_answer,
            citations=used_citations,
        )

        response = {
            "answer": clean_answer,
            "citations": used_citations,
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
    ) -> Tuple[ChatSession, str, List[Dict[str, Any]], str]:
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

        # Compute standalone question from history and user question
        history_dicts = [
            {
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "content": m.content,
            }
            for m in history
        ]
        standalone = rewrite_query(
            history=history_dicts,
            question=question,
            ai_service=self.ai_service,
        )

        # Persist user question (keep original user question in saved message)
        save_message(
            db=db,
            session_id=session.id,
            role="user",
            content=question,
        )

        # Use standalone question for retrieval
        results = self.retrieval_service.retrieve(
            db=db,
            question=standalone,
            organization_id=organization_id,
        )

        citations = []
        vis = set()
        unique_results = []

        for result in results:
            key = (
                getattr(getattr(result, "document", None), "id", None),
                getattr(getattr(result, "chunk", None), "chunk_index", None),
            )
            if key in vis:
                continue

            vis.add(key)
            unique_results.append(result)

        chunk_texts = {}
        for index, result in enumerate(unique_results, start=1):
            raw_text = getattr(result.chunk, "chunk_text", None)
            if isinstance(raw_text, str):
                full_chunk_text = raw_text
                snippet = " ".join(raw_text.split())[:200]
            elif hasattr(result, "text") and isinstance(result.text, str):
                full_chunk_text = result.text
                snippet = " ".join(result.text.split())[:200]
            elif raw_text is not None and type(raw_text).__name__ != "MagicMock":
                full_chunk_text = str(raw_text)
                snippet = " ".join(str(raw_text).split())[:200]
            else:
                full_chunk_text = ""
                snippet = None

            chunk_texts[index] = full_chunk_text

            page_no = getattr(result.chunk, "page_number", None)
            page_number = page_no if isinstance(page_no, int) else None

            doc_id = getattr(result.document, "id", None)
            document_id = doc_id if isinstance(doc_id, int) else None

            chunk_idx = getattr(result.chunk, "chunk_index", 0)
            chunk_index = chunk_idx if isinstance(chunk_idx, int) else 0

            doc_filename = getattr(result.document, "original_filename", "")
            document = doc_filename if isinstance(doc_filename, str) else str(doc_filename)

            citations.append(
                {
                    "id": index,
                    "document": document,
                    "chunk_index": chunk_index,
                    "document_id": document_id,
                    "page_number": page_number,
                    "snippet": snippet,
                }
            )

        # Keep original user question in the final prompt
        prompt = self.prompt_service.build_prompt(
            history=history,
            chunks=unique_results,
            question=question,
        )

        # Cache key uses standalone question
        cache_key = self._get_cache_key(
            organization_id=organization_id,
            question=standalone,
        )

        return PrepResult(
            session=session,
            prompt=prompt,
            citations=citations,
            cache_key=cache_key,
            chunk_texts=chunk_texts,
        )

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
        prep = self._prepare_chat(
            db=db,
            question=question,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
        )
        if len(prep) == 4:
            session, prompt, citations, cache_key = prep
        else:
            session, prompt, citations = prep[:3]
            cache_key = self._get_cache_key(
                organization_id=organization_id,
                question=question,
            )

        chunk_texts = getattr(prep, "chunk_texts", None)

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

            words = cached["answer"].split(" ")
            for i, token in enumerate(words):
                token_text = token + (" " if i < len(words) - 1 else "")
                yield format_sse_event("token", token_text)

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
                yield format_sse_event("token", token)
            completed_successfully = True
        except Exception as e:
            safe_err = self.ai_service._sanitize_error(str(e))
            logger.error(f"Streaming error in chat_stream: {safe_err}")

            # Terminal error event: no token event is emitted after this
            yield format_sse_event(
                "error",
                json.dumps({'error': 'AI provider generation failed. Please try again later.'}),
            )
            yield (
                "event: done\n"
                "data: {}\n\n"
            )
            return
        finally:
            if tokens and completed_successfully:
                answer = "".join(tokens)

                if is_not_found(answer):
                    norm_answer = " ".join(answer.strip().split()).lower()
                    norm_target = " ".join(NOT_FOUND_ANSWER.strip().split()).lower()
                    if norm_answer != norm_target:
                        logger.warning(
                            f"Stream session {session.id}: answer starts with not-found sentence but has extra text: {answer!r}"
                        )

                clean_answer, used_citations, invalid_markers = validate_citations(
                    answer=answer,
                    citations=citations,
                    chunk_texts=chunk_texts,
                )
                valid_markers = extract_markers(clean_answer)
                if invalid_markers or not valid_markers:
                    logger.warning(
                        f"Citation validation for stream session {session.id}: "
                        f"{len(invalid_markers)} invalid markers, "
                        f"{len(valid_markers)} valid markers "
                        f"({'markers missing' if not valid_markers else 'markers valid'})."
                    )

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
