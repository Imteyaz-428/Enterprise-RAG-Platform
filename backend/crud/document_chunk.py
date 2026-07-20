from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from models.document_chunk import DocumentChunk



def create_document_chunk(
    db: Session,
    document_id: int,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float]
):
    chunk = DocumentChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        embedding=embedding
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk




from sqlalchemy.orm import Session

from models.document import Document
from models.document_chunk import DocumentChunk


def search_similar_chunks(
    db: Session,
    organization_id: int,
    query_embedding: list[float],
    top_k: int = 5,
):
    results = (
        db.query(
            DocumentChunk,
            Document,
            DocumentChunk.embedding.cosine_distance(query_embedding).label("score"),
        )
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .filter(
            Document.organization_id == organization_id,
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(query_embedding),
        )
        .limit(top_k)
        .all()
    )

    return results