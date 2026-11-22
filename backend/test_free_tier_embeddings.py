import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
import voyageai

import utils.embedding as embedding_module
from utils.embedding import (
    estimate_tokens,
    generate_embedding,
    generate_embeddings,
    reset_rate_limit_state,
    set_rate_limit_clock,
    split_chunks_into_batches,
)


@pytest.fixture(autouse=True)
def cleanup_embedding_state():
    yield
    reset_rate_limit_state()


def test_token_estimation_and_batching():
    """Verify chunks are split into batches of at most EMBED_BATCH_TOKENS (len(text)/3)."""
    # 3000 chars = 1000 tokens each
    chunks = [
        SimpleNamespace(page_content="a" * 3000, metadata={})
        for _ in range(10)
    ]
    # Total tokens = 10,000. With max_tokens = 6000, should produce 2 batches (6 chunks and 4 chunks)
    batches = split_chunks_into_batches(chunks, max_tokens=6000)
    assert len(batches) == 2
    assert len(batches[0]) == 6
    assert len(batches[1]) == 4


def test_voyage_min_interval_pacing_with_fake_clock(monkeypatch):
    """Verify consecutive Voyage calls are spaced apart by at least VOYAGE_MIN_INTERVAL_SECONDS."""
    monkeypatch.setenv("VOYAGE_MIN_INTERVAL_SECONDS", "20")

    fake_time = 100.0
    sleeps = []

    def fake_clock():
        return fake_time

    def fake_sleep(duration):
        nonlocal fake_time
        sleeps.append(duration)
        fake_time += duration

    set_rate_limit_clock(fake_clock, fake_sleep)

    mock_response = SimpleNamespace(embeddings=[[0.1, 0.2]])

    with patch.object(embedding_module.client, "embed", return_value=mock_response) as mock_embed:
        # Call 1: at t=100.0 -> no sleep needed
        generate_embedding("query 1")
        assert len(sleeps) == 0

        # Advance clock by 5s (t=105.0)
        fake_time = 105.0

        # Call 2: at t=105.0 -> elapsed 5s < 20s -> sleep 15s
        generate_embedding("query 2")
        assert len(sleeps) == 1
        assert sleeps[0] == 15.0

        # Advance clock by 30s (t=150.0) -> elapsed 30s >= 20s -> no sleep
        fake_time = 150.0
        generate_embedding("query 3")
        assert len(sleeps) == 1


def test_query_embedding_retry_on_429_success():
    """Query embedding retries once after 5s on 429 and returns embedding if successful."""
    fake_time = 0.0
    sleeps = []

    def fake_clock():
        return fake_time

    def fake_sleep(duration):
        nonlocal fake_time
        sleeps.append(duration)
        fake_time += duration

    set_rate_limit_clock(fake_clock, fake_sleep)

    mock_resp = SimpleNamespace(embeddings=[[0.5, 0.6, 0.7]])
    rate_err = voyageai.error.RateLimitError("Rate limit exceeded 429")

    with patch.object(embedding_module.client, "embed", side_effect=[rate_err, mock_resp]) as mock_embed:
        result = generate_embedding("sample question")

        assert result == [0.5, 0.6, 0.7]
        assert mock_embed.call_count == 2
        # Must have slept for 5s before retrying
        assert 5.0 in sleeps


def test_query_embedding_retry_on_429_exhausted_raises_503():
    """Query embedding raises HTTP 503 if retry after 5s still fails with 429."""
    fake_time = 0.0
    sleeps = []

    def fake_clock():
        return fake_time

    def fake_sleep(duration):
        nonlocal fake_time
        sleeps.append(duration)
        fake_time += duration

    set_rate_limit_clock(fake_clock, fake_sleep)

    rate_err = voyageai.error.RateLimitError("Rate limit exceeded 429")

    with patch.object(embedding_module.client, "embed", side_effect=[rate_err, rate_err]) as mock_embed:
        with pytest.raises(HTTPException) as exc_info:
            generate_embedding("sample question")

        assert exc_info.value.status_code == 503
        assert "Search is busy, please retry in a few seconds" in exc_info.value.detail
        assert mock_embed.call_count == 2
        assert 5.0 in sleeps


def test_query_embedding_non_429_fails_immediately():
    """Non-429 errors (e.g. auth, validation) fail immediately without 5s retry."""
    auth_err = voyageai.error.AuthenticationError("Invalid API key 401")

    with patch.object(embedding_module.client, "embed", side_effect=auth_err) as mock_embed:
        with pytest.raises(voyageai.error.AuthenticationError):
            generate_embedding("sample question")

        assert mock_embed.call_count == 1


def test_document_processor_retry_on_429_success(monkeypatch):
    """Ingestion retries on 429 with exponential backoff up to 5 times and succeeds."""
    from services.background.document_processor import process_document

    mock_chunks = [
        SimpleNamespace(page_content="Sample text content for chunk 1", metadata={"page_number": 1}),
        SimpleNamespace(page_content="Sample text content for chunk 2", metadata={"page_number": 1}),
    ]

    mock_doc = SimpleNamespace(
        id=10,
        organization_id=1,
        status="pending",
        error_message=None,
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    rate_err = voyageai.error.RateLimitError("Rate limit exceeded 429")
    success_embeddings = [[0.1, 0.2], [0.3, 0.4]]

    # Fails 2 times with 429, then succeeds on 3rd attempt
    mock_generate = MagicMock(side_effect=[rate_err, rate_err, success_embeddings])

    with patch("services.background.document_processor.SessionLocal", return_value=mock_db), \
         patch("services.background.document_processor.get_document_by_id", return_value=mock_doc), \
         patch("services.background.document_processor.extract_documents_from_pdf", return_value=[SimpleNamespace(page_content="Test PDF content")]), \
         patch("services.background.document_processor.strip_repeated_headers_and_footers", return_value=[SimpleNamespace(page_content="Test PDF content")]), \
         patch("services.background.document_processor.split_documents", return_value=mock_chunks), \
         patch("services.background.document_processor.generate_embeddings", mock_generate), \
         patch("time.sleep"):  # fast-forward retries

        process_document(document_id=10, file_path="dummy.pdf")

        assert mock_doc.status == "completed"
        assert mock_doc.error_message is None
        assert mock_generate.call_count == 3
        mock_db.commit.assert_called()


def test_document_processor_retry_on_429_exhausted(monkeypatch):
    """Ingestion sets error_message only after all 5 retries are exhausted."""
    from services.background.document_processor import process_document

    mock_chunks = [
        SimpleNamespace(page_content="Sample text content for chunk 1", metadata={"page_number": 1}),
    ]

    mock_doc = SimpleNamespace(
        id=20,
        organization_id=1,
        status="pending",
        error_message=None,
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    rate_err = voyageai.error.RateLimitError("Rate limit exceeded 429")
    mock_generate = MagicMock(side_effect=rate_err)

    with patch("services.background.document_processor.SessionLocal", return_value=mock_db), \
         patch("services.background.document_processor.get_document_by_id", return_value=mock_doc), \
         patch("services.background.document_processor.extract_documents_from_pdf", return_value=[SimpleNamespace(page_content="Test PDF content")]), \
         patch("services.background.document_processor.strip_repeated_headers_and_footers", return_value=[SimpleNamespace(page_content="Test PDF content")]), \
         patch("services.background.document_processor.split_documents", return_value=mock_chunks), \
         patch("services.background.document_processor.generate_embeddings", mock_generate), \
         patch("services.background.document_processor.update_document_status") as mock_update_status, \
         patch("time.sleep"):

        process_document(document_id=20, file_path="dummy.pdf")

        # Must have attempted 5 times before failing
        assert mock_generate.call_count == 5
        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["status"] == "failed"
        assert "429" in call_kwargs["error_message"] or "Rate limit" in call_kwargs["error_message"]
