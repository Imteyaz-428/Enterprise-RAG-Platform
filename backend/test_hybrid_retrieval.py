
from types import SimpleNamespace

from crud.document_chunk import reciprocal_rank_fusion


def test_rrf_combines_duplicate_chunks():
    document = SimpleNamespace(id=1)

    chunk1 = SimpleNamespace(id=101)
    chunk2 = SimpleNamespace(id=102)
    chunk3 = SimpleNamespace(id=103)

    vector_results = [
        (chunk1, document, 0.1),
        (chunk2, document, 0.2),
    ]

    keyword_results = [
        (chunk1, document, 0.8),
        (chunk3, document, 0.9),
    ]

    results = reciprocal_rank_fusion(
        vector_results,
        keyword_results,
        top_k=3,
    )

    assert len(results) == 3
    assert results[0][0].id == 101
    assert results[0][2] > results[1][2]


def test_rrf_respects_top_k():
    document = SimpleNamespace(id=1)

    vector_results = [
        (SimpleNamespace(id=i), document, 0.1)
        for i in range(1, 6)
    ]

    results = reciprocal_rank_fusion(
        vector_results,
        [],
        top_k=2,
    )

    assert len(results) == 2


def test_rrf_handles_empty_results():
    results = reciprocal_rank_fusion([], [])

    assert results == []
