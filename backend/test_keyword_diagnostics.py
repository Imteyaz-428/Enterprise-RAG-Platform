
from sqlalchemy import text
from database.database import engine

query = "Code Guardian AI static code analysis"

sql = text("""
    SELECT
        plainto_tsquery('english', :query) AS and_query,
        to_tsvector('english', :sample) AS sample_vector;
""")

sample = """
CodeGuardian AI static code analysis.
AST parsing, dependency graph, risk prediction.
AI-generated fixes and verification.
"""

with engine.connect() as connection:
    result = connection.execute(
        sql,
        {"query": query, "sample": sample},
    ).mappings().one()

    print("Parsed query:", result["and_query"])
    print("Sample vector:", result["sample_vector"])

    rows = connection.execute(text("""
        SELECT
            dc.chunk_index,
            d.original_filename,
            ts_rank_cd(
                to_tsvector('english', dc.chunk_text),
                plainto_tsquery('english', :query)
            ) AS rank,
            dc.chunk_text
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.organization_id = 1
          AND to_tsvector('english', dc.chunk_text)
              @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT 10
    """), {"query": query})

    print("\nKeyword matches:")
    for row in rows:
        print(
            f"Chunk: {row.chunk_index} | "
            f"Rank: {row.rank:.6f}"
        )
        print(row.chunk_text[:200])
