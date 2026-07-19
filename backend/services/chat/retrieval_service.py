from sqlalchemy.orm import Session
from services.ai.config  import SEARCH_TOP_K
from utils.embedding import generate_embedding
from crud.document_chunk import search_similar_chunks
from typing import List
from models.document_chunk import DocumentChunk


class RetrievalService:

    def retrieve(
        self,
        db: Session,
        question: str,
        organization_id: int,
        top_k: int = SEARCH_TOP_K,
    ) -> List[DocumentChunk]:
        query_embedding = generate_embedding(question)

        chunks = search_similar_chunks(
            db=db,
            organization_id=organization_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        return chunks