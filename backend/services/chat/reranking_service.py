
import torch
from sentence_transformers import CrossEncoder
from services.chat.retrieval_result import RetrievalResult


def get_optimal_device() -> str:
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class RerankingService:

    def __init__(self, device: str | None = None):
        self.device = device or get_optimal_device()
        self.model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            device=self.device,
        )

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RetrievalResult]:

        if not results:
            return []

        pairs = [
            (query, result.chunk.chunk_text)
            for result in results
        ]

        scores = self.model.predict(pairs)

        ranked_results = sorted(
            zip(results, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        return [
            result
            for result, score in ranked_results[:top_k]
        ]
