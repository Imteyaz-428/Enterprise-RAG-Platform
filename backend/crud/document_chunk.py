
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from models.document import Document
from models.document_chunk import DocumentChunk


def create_document_chunk(
    db: Session,
    document_id: int,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float],
    page_number: int | None = None,
):
    chunk = DocumentChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        embedding=embedding,
        page_number=page_number,
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk


# --------------------------------------------------
# 1. SEMANTIC VECTOR SEARCH
# --------------------------------------------------

def search_similar_chunks(
    db: Session,
    organization_id: int,
    query_embedding: list[float],
    top_k: int = 5,
):
    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    return (
        db.query(
            DocumentChunk,
            Document,
            distance.label("score"),
        )
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .filter(
            Document.organization_id == organization_id,
            DocumentChunk.embedding.isnot(None),
        )
        .order_by(distance.asc())
        .limit(top_k)
        .all()
    )


# --------------------------------------------------
# 2. KEYWORD SEARCH
# --------------------------------------------------


def search_keyword_chunks(
    db: Session,
    organization_id: int,
    query: str,
    top_k: int = 5,
):
    search_vector = func.to_tsvector(
        "english",
        DocumentChunk.chunk_text,
    )

    terms = list(dict.fromkeys(query.split()))

    if not terms:
        return []

    # Parse individual terms into PostgreSQL tsquery expressions
    keyword_queries = [
        func.plainto_tsquery("english", term)
        for term in terms
    ]

    # Match a chunk if any individual term matches
    conditions = [
        search_vector.op("@@")(keyword_query)
        for keyword_query in keyword_queries
    ]

    # Calculate ranking as the sum of individual term scores.
    # No tsquery-to-tsquery OR operator is required.
    keyword_score = sum(
        (
            func.ts_rank_cd(search_vector, keyword_query)
            for keyword_query in keyword_queries
        ),
        0,
    )

    return (
        db.query(
            DocumentChunk,
            Document,
            keyword_score.label("score"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .filter(
            Document.organization_id == organization_id,
            DocumentChunk.embedding.isnot(None),
            or_(*conditions),
        )
        .order_by(keyword_score.desc())
        .limit(top_k)
        .all()
    )


# --------------------------------------------------
# 3. RECIPROCAL RANK FUSION (RRF)
# --------------------------------------------------

def reciprocal_rank_fusion(
    vector_results,
    keyword_results,
    top_k: int = 5,
    rrf_k: int = 60,
):
    fused_results = {}

    def add_ranked_results(results):
        for rank, (chunk, document, _) in enumerate(
            results,
            start=1,
        ):
            chunk_id = chunk.id

            if chunk_id not in fused_results:
                fused_results[chunk_id] = {
                    "chunk": chunk,
                    "document": document,
                    "score": 0.0,
                }

            fused_results[chunk_id]["score"] += (
                1.0 / (rrf_k + rank)
            )

    # Add vector rankings
    add_ranked_results(vector_results)

    # Add keyword rankings
    add_ranked_results(keyword_results)

    # Sort by combined RRF score
    ranked_results = sorted(
        fused_results.values(),
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        (
            item["chunk"],
            item["document"],
            item["score"],
        )
        for item in ranked_results[:top_k]
    ]


# --------------------------------------------------
# 4. HYBRID SEARCH
# --------------------------------------------------

def search_hybrid_chunks(
    db: Session,
    organization_id: int,
    query: str,
    query_embedding: list[float],
    top_k: int = 5,
    candidate_k: int = 20,
    rrf_k: int = 60,
):
    # 1. Semantic vector retrieval
    vector_results = search_similar_chunks(
        db=db,
        organization_id=organization_id,
        query_embedding=query_embedding,
        top_k=candidate_k,
    )

    # 2. Keyword retrieval
    keyword_results = search_keyword_chunks(
        db=db,
        organization_id=organization_id,
        query=query,
        top_k=candidate_k,
    )

    # 3. Combine rankings using Reciprocal Rank Fusion
    return reciprocal_rank_fusion(
        vector_results=vector_results,
        keyword_results=keyword_results,
        top_k=top_k,
        rrf_k=rrf_k,
    )
