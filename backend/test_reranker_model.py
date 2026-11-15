import pytest
from sentence_transformers import CrossEncoder
from services.chat.reranking_service import get_optimal_device


def test_reranker_model_prediction():
    device = get_optimal_device()
    try:
        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            device=device,
        )
    except Exception:
        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cpu",
        )

    query = "What is static code analysis?"

    passages = [
        "Static code analysis examines source code without executing it.",
        "A database stores structured information.",
        "Static analysis can detect security vulnerabilities and code quality issues.",
    ]

    pairs = [(query, passage) for passage in passages]

    scores = model.predict(pairs)

    ranked = sorted(
        zip(passages, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    assert len(ranked) == 3
    # Top ranked passage must be about static code analysis
    assert "Static" in ranked[0][0]


def run_diagnostics():
    device = get_optimal_device()
    try:
        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            device=device,
        )
    except Exception:
        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cpu",
        )

    query = "What is static code analysis?"
    passages = [
        "Static code analysis examines source code without executing it.",
        "A database stores structured information.",
        "Static analysis can detect security vulnerabilities and code quality issues.",
    ]
    pairs = [(query, passage) for passage in passages]
    scores = model.predict(pairs)
    ranked = sorted(zip(passages, scores), key=lambda item: float(item[1]), reverse=True)
    for passage, score in ranked:
        print(f"Score: {float(score):.4f} | {passage}")


if __name__ == "__main__":
    run_diagnostics()
