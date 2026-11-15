
from sqlalchemy.orm import Session

from services.ai.config import SEARCH_TOP_K, RERANK_CANDIDATES
from utils.embedding import generate_embedding
from crud.document_chunk import search_hybrid_chunks
from services.chat.retrieval_result import RetrievalResult
from services.chat.reranking_service import RerankingService


class RetrievalService:

    def __init__(self):
        self.reranking_service = RerankingService()

    def retrieve(
        self,
        db: Session,
        question: str,
        organization_id: int,
        top_k: int = SEARCH_TOP_K,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievalResult]:

        # 1. Generate query embedding if not provided
        if query_embedding is None:
            query_embedding = generate_embedding(question)

        # 2. Retrieve candidates using hybrid search
        results = search_hybrid_chunks(
            db=db,
            organization_id=organization_id,
            query=question,
            query_embedding=query_embedding,
            top_k=RERANK_CANDIDATES,
            candidate_k=RERANK_CANDIDATES,
            rrf_k=60,
        )

        # 3. Convert database results into RetrievalResult objects
        retrieval_results = [
            RetrievalResult(
                chunk=chunk,
                document=document,
                score=float(score),
            )
            for chunk, document, score in results
        ]

        # 4. Rerank candidates using CrossEncoder
        return self.reranking_service.rerank(
            query=question,
            results=retrieval_results,
            top_k=top_k,
        )
