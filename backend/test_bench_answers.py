import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from eval.bench_answers import (
    build_citations_and_chunk_texts,
    evaluate_single_answer,
    load_dataset,
    norm,
    run_benchmark,
    summarize_answers,
)
from services.chat.prompt_service import PromptService


def test_scope_safe_prompt_rule():
    prompt_service = PromptService()
    prompt = prompt_service.build_prompt([], [], "What was the revenue?")
    assert "do not combine or reinterpret figures" in prompt.lower()
    assert "if the question asks about a specific year, entity or scope" in prompt.lower()



def test_norm():
    assert norm("  Hello   WORLD! \n\t ") == "hello world!"
    assert norm("") == ""
    assert norm(None) == ""
    assert norm("1,510") == "1,510"


def test_load_dataset(tmp_path: Path):
    sample_file = tmp_path / "test.jsonl"
    sample_file.write_text(
        '# A comment\n{"id": "q1", "question": "What is A?", "answerable": true}\n\n{"id": "q2", "question": "What is B?", "answerable": false}\n'
    )
    items = load_dataset(sample_file)
    assert len(items) == 2
    assert items[0]["id"] == "q1"
    assert items[1]["id"] == "q2"


def test_build_citations_and_chunk_texts():
    # Mock retrieval results
    doc1 = MagicMock(id=1, original_filename="doc1.pdf")
    chunk1 = MagicMock(chunk_index=0, page_number=1, chunk_text="Chunk one content about revenue.")

    doc2 = MagicMock(id=1, original_filename="doc1.pdf")
    chunk2 = MagicMock(chunk_index=0, page_number=1, chunk_text="Duplicate chunk.")

    doc3 = MagicMock(id=2, original_filename="doc2.pdf")
    chunk3 = MagicMock(chunk_index=1, page_number=5, chunk_text="Chunk two content about profits.")

    r1 = MagicMock(document=doc1, chunk=chunk1)
    r2 = MagicMock(document=doc2, chunk=chunk2)  # Duplicate of r1
    r3 = MagicMock(document=doc3, chunk=chunk3)

    citations, chunk_texts, unique_results = build_citations_and_chunk_texts([r1, r2, r3])

    assert len(unique_results) == 2
    assert len(citations) == 2
    assert citations[0]["id"] == 1
    assert citations[0]["document"] == "doc1.pdf"
    assert citations[0]["page_number"] == 1
    assert citations[1]["id"] == 2
    assert citations[1]["document"] == "doc2.pdf"
    assert citations[1]["page_number"] == 5

    assert chunk_texts[1] == "Chunk one content about revenue."
    assert chunk_texts[2] == "Chunk two content about profits."


def test_evaluate_single_answer_answerable_supported():
    item = {
        "id": "q-01",
        "question": "What was the revenue in 2024?",
        "answerable": True,
        "must_contain_any": ["revenue of 500 million"],
    }
    citations = [
        {"id": 1, "document": "report.pdf", "page_number": 2, "snippet": "revenue of 500 million in 2024"},
    ]
    chunk_texts = {
        1: "In 2024, the company generated revenue of 500 million.",
    }
    raw_answer = "The revenue in 2024 was 500 million [1]."

    row = evaluate_single_answer(item, raw_answer, citations, chunk_texts, latency_ms=120.5)

    assert row["id"] == "q-01"
    assert row["answerable"] is True
    assert row["is_refusal"] is False
    assert row["answered_with_citation"] is True
    assert row["total_citations"] == 1
    assert row["supported_citations"] == 1
    assert row["citation_details"][0]["has_anchor"] is True
    assert row["latency_ms"] == 120.5


def test_evaluate_single_answer_answerable_refusal():
    item = {
        "id": "q-02",
        "question": "What was the revenue in 2024?",
        "answerable": True,
        "must_contain_any": ["500 million"],
    }
    citations = [{"id": 1, "document": "report.pdf", "page_number": 2, "snippet": "some text"}]
    chunk_texts = {1: "some text"}
    raw_answer = "I could not find this in the provided documents."

    row = evaluate_single_answer(item, raw_answer, citations, chunk_texts, latency_ms=80.0)

    assert row["answerable"] is True
    assert row["is_refusal"] is True
    assert row["answered_with_citation"] is False
    assert row["total_citations"] == 0
    assert row["supported_citations"] == 0


def test_evaluate_single_answer_unanswerable_not_found():
    item = {
        "id": "none-01",
        "question": "What was the secret sauce?",
        "answerable": False,
    }
    citations = [{"id": 1, "document": "report.pdf", "page_number": 1, "snippet": "sauce details"}]
    chunk_texts = {1: "sauce details"}
    raw_answer = "I could not find this in the provided documents."

    row = evaluate_single_answer(item, raw_answer, citations, chunk_texts, latency_ms=50.0)

    assert row["answerable"] is False
    assert row["is_not_found"] is True
    assert row["final_citations"] == []


def test_evaluate_single_answer_unanswerable_hallucination():
    item = {
        "id": "none-02",
        "question": "What was the secret sauce?",
        "answerable": False,
    }
    citations = [{"id": 1, "document": "report.pdf", "page_number": 1, "snippet": "recipe"}]
    chunk_texts = {1: "recipe"}
    raw_answer = "The secret sauce is mayonnaise."

    row = evaluate_single_answer(item, raw_answer, citations, chunk_texts, latency_ms=60.0)

    assert row["answerable"] is False
    assert row["is_not_found"] is False


def test_summarize_answers():
    rows = [
        # Answerable 1: answered with citation, supported
        {
            "id": "q1",
            "answerable": True,
            "status": "success",
            "is_refusal": False,
            "answered_with_citation": True,
            "total_citations": 2,
            "supported_citations": 2,
            "latency_ms": 100.0,
        },
        # Answerable 2: answered with citation, partially supported
        {
            "id": "q2",
            "answerable": True,
            "status": "success",
            "is_refusal": False,
            "answered_with_citation": True,
            "total_citations": 2,
            "supported_citations": 1,
            "latency_ms": 200.0,
        },
        # Answerable 3: refusal
        {
            "id": "q3",
            "answerable": True,
            "status": "success",
            "is_refusal": True,
            "answered_with_citation": False,
            "total_citations": 0,
            "supported_citations": 0,
            "latency_ms": 150.0,
        },
        # Unanswerable 1: correctly not found
        {
            "id": "u1",
            "answerable": False,
            "status": "success",
            "is_not_found": True,
            "latency_ms": 80.0,
        },
        # Unanswerable 2: incorrectly answered (hallucination)
        {
            "id": "u2",
            "answerable": False,
            "status": "success",
            "is_not_found": False,
            "latency_ms": 90.0,
        },
        # Error row
        {
            "id": "err1",
            "answerable": True,
            "status": "error",
            "error": "Timeout",
        },
    ]

    summary = summarize_answers(rows)

    assert summary["n_total"] == 6
    assert summary["n_answerable"] == 3
    assert summary["n_unanswerable"] == 2
    assert summary["n_errors"] == 1

    # Answerable: 1 refusal out of 3 -> 1/3 = 0.333
    assert summary["refusal_rate"] == 0.333
    # Answerable: 2 answered with citation out of 3 -> 2/3 = 0.667
    assert summary["answered_with_citation_rate"] == 0.667
    # Total citations = 4, supported = 3 -> 3/4 = 0.75
    assert summary["citation_anchor_rate"] == 0.75
    assert summary["total_citations"] == 4
    assert summary["supported_citations"] == 3

    # Unanswerable: 1 not-found out of 2 -> 1/2 = 0.5
    assert summary["not_found_rate"] == 0.5

    # Latencies: [80, 90, 100, 150, 200] -> mean = 124.0
    assert summary["latency_ms_mean"] == 124.0


def test_summarize_answers_empty():
    summary = summarize_answers([])
    assert summary["n_total"] == 0
    assert summary["refusal_rate"] == 0.0
    assert summary["not_found_rate"] == 0.0
    assert summary["latency_ms_mean"] == 0.0


def test_old_sentence_absent_from_system_prompt():
    """Verifies that the old leaked instruction 'Say so plainly and cite nothing.' is absent."""
    prompt_service = PromptService()
    system_prompt = prompt_service.SYSTEM_PROMPT
    assert "say so plainly and cite nothing" not in system_prompt.lower()
    assert (
        "reply with exactly this sentence and nothing else: i could not find this in the provided documents."
        in system_prompt.lower()
    )


def test_repeat_counts_trials_correctly():
    """
    Verifies that --repeat asks unanswerable questions N times,
    asks answerable questions 1 time, and calculates the not-found rate
    over all trials accurately.
    """
    mock_db = MagicMock()
    mock_retrieval = MagicMock()
    mock_prompt = MagicMock()
    mock_ai = MagicMock()

    doc1 = MagicMock(id=1, original_filename="doc1.pdf")
    chunk1 = MagicMock(chunk_index=0, page_number=1, chunk_text="Revenue was 100.")
    mock_retrieval.retrieve.return_value = [MagicMock(document=doc1, chunk=chunk1)]
    mock_prompt.build_prompt.return_value = "prompt"

    # 1 answerable, 1 unanswerable
    items = [
        {"id": "q-ans", "question": "What is revenue?", "answerable": True, "must_contain_any": ["100"]},
        {"id": "q-unans", "question": "What is secret?", "answerable": False},
    ]

    # Let the unanswerable refuse twice and hallucinate once
    mock_ai.generate_answer.side_effect = [
        "Revenue was 100 [1].",                               # answerable (1 trial)
        "I could not find this in the provided documents.",   # unanswerable trial 1
        "The secret is 42 [1].",                              # unanswerable trial 2 (fails to refuse)
        "I could not find this in the provided documents.",   # unanswerable trial 3
    ]

    summary, rows = run_benchmark(
        db=mock_db,
        retrieval_service=mock_retrieval,
        prompt_service=mock_prompt,
        ai_service=mock_ai,
        items=items,
        org_id=1,
        repeat=3,
    )

    # 1 answerable trial + 3 unanswerable trials = 4 trials total
    assert summary["n_total"] == 4
    assert summary["n_answerable"] == 1
    assert summary["n_unanswerable"] == 3
    assert mock_ai.generate_answer.call_count == 4

    unans_rows = [r for r in rows if r["id"] == "q-unans"]
    assert len(unans_rows) == 3
    assert [r["trial"] for r in unans_rows] == [1, 2, 3]
    assert unans_rows[0]["is_not_found"] is True
    assert unans_rows[1]["is_not_found"] is False
    assert unans_rows[2]["is_not_found"] is True

    # 2 out of 3 refused
    assert summary["not_found_rate"] == round(2 / 3, 3)
