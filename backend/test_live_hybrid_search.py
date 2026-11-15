# Register SQLAlchemy relationship models
from models.organization import Organization
from models.user import User
from database.database import SessionLocal
from utils.embedding import generate_embedding
from crud.document_chunk import (
    search_similar_chunks,
    search_keyword_chunks,
    search_hybrid_chunks,
)

ORGANIZATION_ID = 1
QUERY = "Code Guardian AI static code analysis"


def main():
    db = SessionLocal()

    try:
        print("\n========== HYBRID SEARCH TEST ==========")
        print("Query:", QUERY)

        # Generate one query embedding through Voyage AI
        query_embedding = generate_embedding(QUERY)

        # 1. Test vector search
        vector_results = search_similar_chunks(
            db=db,
            organization_id=ORGANIZATION_ID,
            query_embedding=query_embedding,
            top_k=5,
        )

        print("\n--- VECTOR SEARCH ---")

        for chunk, document, score in vector_results:
            print(
                f"Document: {document.original_filename} | "
                f"Chunk: {chunk.chunk_index} | "
                f"Score: {score:.4f}"
            )

        # 2. Test keyword search
        keyword_results = search_keyword_chunks(
            db=db,
            organization_id=ORGANIZATION_ID,
            query=QUERY,
            top_k=5,
        )

        print("\n--- KEYWORD SEARCH ---")

        for chunk, document, score in keyword_results:
            print(
                f"Document: {document.original_filename} | "
                f"Chunk: {chunk.chunk_index} | "
                f"Score: {score:.4f}"
            )

        # 3. Test hybrid search
        hybrid_results = search_hybrid_chunks(
            db=db,
            organization_id=ORGANIZATION_ID,
            query=QUERY,
            query_embedding=query_embedding,
            top_k=5,
        )

        print("\n--- HYBRID SEARCH (RRF) ---")

        for chunk, document, score in hybrid_results:
            print(
                f"Document: {document.original_filename} | "
                f"Chunk: {chunk.chunk_index} | "
                f"RRF Score: {score:.6f}"
            )
            print("Text:", chunk.chunk_text[:200])
            print("-" * 60)

        print("\n========== TEST COMPLETED ==========")

    finally:
        db.close()


if __name__ == "__main__":
    main()
