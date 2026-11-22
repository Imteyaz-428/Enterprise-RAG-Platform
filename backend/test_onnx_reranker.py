import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.chat.reranking_service import RerankingService
from services.chat.retrieval_result import RetrievalResult


def _make_dummy_results(count: int = 5) -> list[RetrievalResult]:
    doc = SimpleNamespace(id=1, original_filename="test.pdf")
    return [
        RetrievalResult(
            chunk=SimpleNamespace(id=i, chunk_text=f"Chunk text number {i} with some content."),
            document=doc,
            score=1.0 / (i + 1),
        )
        for i in range(count)
    ]


def test_onnx_backend_selection(monkeypatch):
    """Test that onnx backend is selected via env or constructor."""
    monkeypatch.setenv("RERANKER_BACKEND", "onnx")
    svc = RerankingService()
    assert svc.backend == "onnx"

    svc_override = RerankingService(backend="onnx")
    assert svc_override.backend == "onnx"


def test_onnx_rerank_scoring_and_sorting():
    """Verify ONNX reranker successfully scores and reorders candidates."""
    svc = RerankingService(backend="onnx")
    results = [
        RetrievalResult(
            chunk=SimpleNamespace(id=0, chunk_text="Completely irrelevant astronomy data about galaxies."),
            document=SimpleNamespace(id=1, original_filename="test.pdf"),
            score=0.9,
        ),
        RetrievalResult(
            chunk=SimpleNamespace(id=1, chunk_text="Veloura operates 118 dark stores across eight metropolitan cities."),
            document=SimpleNamespace(id=1, original_filename="test.pdf"),
            score=0.5,
        ),
    ]

    reranked = svc.rerank(query="How many dark stores does Veloura operate?", results=results, top_k=2)

    assert len(reranked) == 2
    # The relevant chunk (id=1) must be ranked first
    assert reranked[0].chunk.id == 1
    assert reranked[1].chunk.id == 0


def test_onnx_batching_over_20():
    """Verify that candidate lists larger than 20 are scored in batches of at most 20."""
    svc = RerankingService(backend="onnx")
    results = _make_dummy_results(25)

    reranked = svc.rerank(query="test query for batching", results=results, top_k=5)

    assert len(reranked) == 5


def test_onnx_fail_open_on_error(monkeypatch):
    """Verify ONNX reranker fails open to the fused order upon any runtime error."""
    svc = RerankingService(backend="onnx")
    results = _make_dummy_results(5)

    with patch.object(svc, "_get_onnx_resources", side_effect=RuntimeError("ONNX session crash")):
        reranked = svc.rerank(query="test query", results=results, top_k=3)

        assert len(reranked) == 3
        # Should retain original fused order: 0, 1, 2
        assert [r.chunk.id for r in reranked] == [0, 1, 2]


def test_onnx_lazy_load_thread_safety():
    """Verify thread-safe lazy loading of ONNX session and tokenizer."""
    sessions = []

    def load_resources():
        session, tokenizer = RerankingService._get_onnx_resources()
        sessions.append(id(session))

    threads = [threading.Thread(target=load_resources) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All threads must share the exact same cached session instance
    assert len(sessions) == 5
    assert len(set(sessions)) == 1


def test_onnx_does_not_import_torch():
    """Verify that running ONNX reranker in a clean subprocess does not import torch."""
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "from types import SimpleNamespace; "
            "from services.chat.reranking_service import RerankingService; "
            "from services.chat.retrieval_result import RetrievalResult; "
            "svc = RerankingService(backend='onnx'); "
            "doc = SimpleNamespace(id=1, original_filename='test.pdf'); "
            "results = [RetrievalResult(chunk=SimpleNamespace(id=0, chunk_text='test text'), document=doc, score=1.0)]; "
            "svc.rerank(query='test', results=results, top_k=1); "
            "assert 'torch' not in sys.modules, f'torch was imported: {list(sys.modules.keys())}'"
        ),
    ]
    result = subprocess.run(
        cmd,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        env=dict(os.environ, PYTHONPATH="backend"),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ONNX reranking loaded torch: {result.stderr}"
