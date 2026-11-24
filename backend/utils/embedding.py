import os
import threading
import time
from typing import Callable, List
from dotenv import load_dotenv
from fastapi import HTTPException
import voyageai

from services.ai.config import (
    VOYAGE_MIN_INTERVAL_SECONDS,
    EMBED_BATCH_TOKENS,
)
from utils.logger import logger

load_dotenv()


class _LazyVoyageClient:
    """Lazy Voyage AI client that defers initialization until first use."""

    def __init__(self):
        self._real_client = None
        self._cached_api_key = None

    def _get_client(self) -> voyageai.Client:
        current_key = os.getenv("VOYAGE_API_KEY")
        if not current_key:
            raise ValueError(
                "VOYAGE_API_KEY is not configured. Please set the VOYAGE_API_KEY environment variable to generate embeddings."
            )
        if self._real_client is None or self._cached_api_key != current_key:
            self._real_client = voyageai.Client(api_key=current_key)
            self._cached_api_key = current_key
        return self._real_client

    def embed(self, *args, **kwargs):
        return self._get_client().embed(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._get_client(), name)


client = _LazyVoyageClient()

_rate_limit_lock = threading.Lock()
_last_call_time: float = 0.0

# Injectable clock and sleep for testing with a fake clock
_clock_fn: Callable[[], float] = time.monotonic
_sleep_fn: Callable[[float], None] = time.sleep


def set_rate_limit_clock(clock: Callable[[], float], sleep: Callable[[float], None]) -> None:
    """Injectable fake clock and sleep function for unit testing."""
    global _clock_fn, _sleep_fn
    _clock_fn = clock
    _sleep_fn = sleep


def reset_rate_limit_state() -> None:
    """Reset rate limiter state (useful in test teardown)."""
    global _last_call_time, _clock_fn, _sleep_fn
    _last_call_time = 0.0
    _clock_fn = time.monotonic
    _sleep_fn = time.sleep


def _wait_for_rate_limit() -> None:
    """
    Process-wide lock that keeps consecutive Voyage calls at least
    VOYAGE_MIN_INTERVAL_SECONDS apart when the env variable is > 0.
    """
    global _last_call_time
    try:
        min_interval = float(os.getenv("VOYAGE_MIN_INTERVAL_SECONDS", str(VOYAGE_MIN_INTERVAL_SECONDS)))
    except (ValueError, TypeError):
        min_interval = 0.0

    if min_interval <= 0:
        return

    with _rate_limit_lock:
        now = _clock_fn()
        elapsed = now - _last_call_time
        if _last_call_time > 0 and elapsed < min_interval:
            wait_time = min_interval - elapsed
            _sleep_fn(wait_time)
            now = _clock_fn()
        _last_call_time = now


def is_429_error(exc: BaseException) -> bool:
    """Check if exception represents a 429 rate limit error."""
    if isinstance(exc, voyageai.error.RateLimitError):
        return True
    status_code = getattr(exc, "status_code", getattr(exc, "code", None))
    if status_code is not None:
        try:
            if int(status_code) == 429:
                return True
        except (ValueError, TypeError):
            pass
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg


def estimate_tokens(text: str) -> int:
    """Estimate tokens as len(text) / 3."""
    return max(1, int(len(text) / 3))


def split_chunks_into_batches(
    chunks: list,
    max_tokens: int | None = None,
) -> list[list]:
    """
    Split chunks into batches of at most EMBED_BATCH_TOKENS (default 6000),
    estimating tokens as len(text) / 3.
    """
    if not chunks:
        return []

    if max_tokens is None:
        try:
            max_tokens = int(os.getenv("EMBED_BATCH_TOKENS", str(EMBED_BATCH_TOKENS)))
        except (ValueError, TypeError):
            max_tokens = 6000

    batches = []
    current_batch = []
    current_tokens = 0

    for chunk in chunks:
        text = chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
        tokens = int(len(text) / 3)
        if current_batch and (current_tokens + tokens > max_tokens):
            batches.append(current_batch)
            current_batch = [chunk]
            current_tokens = tokens
        else:
            current_batch.append(chunk)
            current_tokens += tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts.
    Used during document upload.
    Enforces VOYAGE_MIN_INTERVAL_SECONDS spacing between consecutive calls.
    """
    if not texts:
        return []

    _wait_for_rate_limit()
    response = client.embed(
        texts,
        model="voyage-3-large",
    )
    return response.embeddings


def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single query.
    Used during semantic search.
    Enforces VOYAGE_MIN_INTERVAL_SECONDS, retries once after 5 s on 429,
    then raises HTTP 503 "Search is busy, please retry in a few seconds".
    """
    _wait_for_rate_limit()
    try:
        response = client.embed(
            [text],
            model="voyage-3-large",
        )
        return response.embeddings[0]
    except Exception as e:
        if not is_429_error(e):
            raise

        logger.warning("Voyage 429 rate limit encountered during query embedding. Retrying once after 5s...")
        _sleep_fn(5.0)
        _wait_for_rate_limit()
        try:
            response = client.embed(
                [text],
                model="voyage-3-large",
            )
            return response.embeddings[0]
        except Exception as retry_err:
            if is_429_error(retry_err):
                raise HTTPException(
                    status_code=503,
                    detail="Search is busy, please retry in a few seconds",
                ) from retry_err
            raise
