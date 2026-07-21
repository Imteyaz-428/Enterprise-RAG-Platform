from sqlalchemy.orm import Session
from services.ai.config  import SEARCH_TOP_K
from utils.embedding import generate_embedding
from crud.document_chunk import search_similar_chunks
from typing import List
from models.document_chunk import DocumentChunk
from services.chat.retrieval_result import RetrievalResult

class RetrievalService:

   def retrieve(
    self,
    db: Session,
    question: str,
    organization_id: int,
    top_k: int = SEARCH_TOP_K,
) -> list[RetrievalResult]:

    query_embedding = generate_embedding(question)

    results = search_similar_chunks(
        db=db,
        organization_id=organization_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )

    return [
        RetrievalResult(
            chunk=chunk,
            document=document,
            score=score,
        )
        for chunk, document, score in results
    ]