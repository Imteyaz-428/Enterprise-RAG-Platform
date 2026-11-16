"""List what is actually ingested: documents and chunk counts per organization.

    PYTHONPATH=. python eval/inspect_corpus.py
    PYTHONPATH=. python eval/inspect_corpus.py "child process"   # which docs contain a phrase
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func  # noqa: E402

from database.database import SessionLocal  # noqa: E402
from models.document import Document  # noqa: E402
from models.document_chunk import DocumentChunk  # noqa: E402


def main():
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            phrase = " ".join(sys.argv[1:])
            rows = (
                db.query(Document.organization_id, Document.id,
                         Document.original_filename, func.count(DocumentChunk.id))
                .join(DocumentChunk, DocumentChunk.document_id == Document.id)
                .filter(DocumentChunk.chunk_text.ilike(f"%{phrase}%"))
                .group_by(Document.organization_id, Document.id, Document.original_filename)
                .order_by(Document.organization_id, Document.id)
                .all()
            )
            print(f'Chunks containing "{phrase}":')
            for org, doc_id, name, n in rows:
                print(f"  org {org} | doc {doc_id} | {n} chunk(s) | {name}")
            if not rows:
                print("  none")
            return

        rows = (
            db.query(Document.organization_id, Document.id, Document.original_filename,
                     Document.status, func.count(DocumentChunk.id))
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .group_by(Document.organization_id, Document.id,
                      Document.original_filename, Document.status)
            .order_by(Document.organization_id, Document.id)
            .all()
        )
        for org, doc_id, name, status, n in rows:
            print(f"org {org} | doc {doc_id} | {status:<10} | {n:>4} chunks | {name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()