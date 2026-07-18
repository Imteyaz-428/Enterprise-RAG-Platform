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




def search_similar_chunks(
    db: Session,
    document_id: int,
    query_embedding: list[float],
    limit: int = 5,
):
    results = (
        db.query(
            DocumentChunk,
            DocumentChunk.embedding.cosine_distance(query_embedding).label("score"),
        )
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
        .all()
    )

    return [chunk for chunk, _ in results]