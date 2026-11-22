import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.chat.reranking_service import RerankingService
from services.chat.retrieval_result import RetrievalResult


def _make_dummy_results(count: int = 5) -> list[RetrievalResult]:
    doc = SimpleNamespace(id=1, original_filename="test.pdf")
    return [
        RetrievalResult(
            chunk=SimpleNamespace(id=i, chunk_text=f"Chunk text {i}"),
            document=doc,
            score=1.0 / (i + 1),
        )
        for i in range(count)
    ]


def test_import_reranking_service_does_not_import_torch():
    """Verify that importing reranking_service and instantiating it does not import torch."""
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "from services.chat.reranking_service import RerankingService; "
            "svc = RerankingService(); "
            "assert 'torch' not in sys.modules, f'torch imported: {sys.modules.get(\"torch\")}'"
        ),
    ]
    result = subprocess.run(
        cmd,
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Importing RerankingService loaded torch: {result.stderr}"


def test_backend_selection_from_env(monkeypatch):
    """Test that RERANKER_BACKEND env variable selects the active backend."""
    monkeypatch.setenv("RERANKER_BACKEND", "voyage")
    svc_voyage = RerankingService()
    assert svc_voyage.backend == "voyage"

    monkeypatch.setenv("RERANKER_BACKEND", "none")
    svc_none = RerankingService()
    assert svc_none.backend == "none"

    monkeypatch.setenv("RERANKER_BACKEND", "local")
    svc_local = RerankingService()
    assert svc_local.backend == "local"

    # Constructor override takes precedence over env
    svc_override = RerankingService(backend="none")
    assert svc_override.backend == "none"


def test_none_ordering():
    """'none' backend returns fused candidates truncated to top_k in original order."""
    results = _make_dummy_results(10)
    svc = RerankingService(backend="none")

    reranked = svc.rerank(query="test query", results=results, top_k=3)

    assert len(reranked) == 3
    assert reranked[0].chunk.id == 0
    assert reranked[1].chunk.id == 1
    assert reranked[2].chunk.id == 2


def test_voyage_reranker_success(monkeypatch):
    """'voyage' backend calls Voyage API and reorders candidate results."""
    monkeypatch.setenv("VOYAGE_API_KEY", "mock-voyage-key")
    monkeypatch.setenv("VOYAGE_RERANK_MODEL", "rerank-2")

    results = _make_dummy_results(4)
    # Reorder to indices: 2, 0, 3, 1
    mock_response = SimpleNamespace(
        results=[
            SimpleNamespace(index=2, relevance_score=0.95),
            SimpleNamespace(index=0, relevance_score=0.80),
            SimpleNamespace(index=3, relevance_score=0.60),
            SimpleNamespace(index=1, relevance_score=0.40),
        ]
    )

    mock_client = MagicMock()
    mock_client.rerank.return_value = mock_response

    with patch("voyageai.Client", return_value=mock_client) as mock_client_cls:
        svc = RerankingService(backend="voyage")
        reranked = svc.rerank(query="sample query", results=results, top_k=2)

        # Verify voyageai.Client initialization with 8s timeout and api key
        mock_client_cls.assert_called_once_with(api_key="mock-voyage-key", timeout=8.0)

        # Verify client.rerank call arguments
        mock_client.rerank.assert_called_once_with(
            query="sample query",
            documents=["Chunk text 0", "Chunk text 1", "Chunk text 2", "Chunk text 3"],
            model="rerank-2",
            top_k=2,
        )

        assert len(reranked) == 2
        assert reranked[0].chunk.id == 2
        assert reranked[1].chunk.id == 0


def test_voyage_reranker_fail_open_timeout(monkeypatch):
    """Voyage timeout fails open to fused order truncated to top_k without raising."""
    monkeypatch.setenv("VOYAGE_API_KEY", "mock-voyage-key")
    results = _make_dummy_results(5)

    mock_client = MagicMock()
    mock_client.rerank.side_effect = TimeoutError("Request timed out after 8 seconds")

    with patch("voyageai.Client", return_value=mock_client):
        svc = RerankingService(backend="voyage")
        reranked = svc.rerank(query="query", results=results, top_k=3)

        assert len(reranked) == 3
        # Must retain original fused order
        assert [r.chunk.id for r in reranked] == [0, 1, 2]


def test_voyage_reranker_fail_open_rate_limit(monkeypatch):
    """Voyage rate limit error fails open without raising."""
    monkeypatch.setenv("VOYAGE_API_KEY", "mock-voyage-key")
    results = _make_dummy_results(5)

    mock_client = MagicMock()
    mock_client.rerank.side_effect = Exception("Rate limit exceeded 429")

    with patch("voyageai.Client", return_value=mock_client):
        svc = RerankingService(backend="voyage")
        reranked = svc.rerank(query="query", results=results, top_k=3)

        assert len(reranked) == 3
        assert [r.chunk.id for r in reranked] == [0, 1, 2]


def test_voyage_reranker_fail_open_network_error(monkeypatch):
    """Voyage network error fails open without raising."""
    monkeypatch.setenv("VOYAGE_API_KEY", "mock-voyage-key")
    results = _make_dummy_results(5)

    mock_client = MagicMock()
    mock_client.rerank.side_effect = ConnectionError("Failed to establish network connection")

    with patch("voyageai.Client", return_value=mock_client):
        svc = RerankingService(backend="voyage")
        reranked = svc.rerank(query="query", results=results, top_k=3)

        assert len(reranked) == 3
        assert [r.chunk.id for r in reranked] == [0, 1, 2]


def test_voyage_reranker_fail_open_bad_response(monkeypatch):
    """Voyage bad or malformed response fails open without raising."""
    monkeypatch.setenv("VOYAGE_API_KEY", "mock-voyage-key")
    results = _make_dummy_results(5)

    mock_client = MagicMock()
    mock_client.rerank.return_value = None

    with patch("voyageai.Client", return_value=mock_client):
        svc = RerankingService(backend="voyage")
        reranked = svc.rerank(query="query", results=results, top_k=3)

        assert len(reranked) == 3
        assert [r.chunk.id for r in reranked] == [0, 1, 2]


def test_reranker_empty_results():
    """Empty candidate results returns empty list immediately."""
    svc = RerankingService(backend="voyage")
    assert svc.rerank(query="query", results=[], top_k=5) == []


def test_unknown_backend_fails_open():
    """An unknown backend fails open to fused order."""
    results = _make_dummy_results(5)
    svc = RerankingService(backend="unknown_backend")
    reranked = svc.rerank(query="query", results=results, top_k=3)
    assert len(reranked) == 3
    assert [r.chunk.id for r in reranked] == [0, 1, 2]
