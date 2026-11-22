from database.database import SessionLocal
from crud.document import get_document_by_id, update_document_status
from models.document_chunk import DocumentChunk
from utils.chunker import split_documents, strip_repeated_headers_and_footers
from utils.embedding import generate_embeddings
from utils.pdf import extract_documents_from_pdf
from utils.logger import logger


def process_document(
    document_id: int,
    file_path: str,
):
    db = SessionLocal()

    try:
        doc = get_document_by_id(db=db, document_id=document_id)
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        organization_id = doc.organization_id

        # 1. Extract PDF page by page
        documents = extract_documents_from_pdf(
            file_path=file_path,
            document_id=document_id,
        )

        if not documents:
            raise ValueError(
                "No extractable text found in PDF."
            )

        # 2. Before chunking, remove repeated header/footer lines
        documents = strip_repeated_headers_and_footers(documents)
        documents = [d for d in documents if d.page_content.strip()]

        if not documents:
            raise ValueError("No extractable text found in PDF after header/footer removal.")

        # 3. Split LangChain Documents
        chunks = split_documents(
            documents,
            chunk_size=1000,
            overlap=200,
        )

        if not chunks:
            raise ValueError("No chunks generated.")

        # 4. Extract chunk text for embeddings
        chunk_texts = [
            chunk.page_content
            for chunk in chunks
        ]

        # 5. Generate Voyage AI embeddings
        embeddings = generate_embeddings(
            chunk_texts
        )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embedding count does not match chunk count."
            )

        # 6. Store chunks and mark document completed in one batched transaction
        chunk_objects = [
            DocumentChunk(
                organization_id=organization_id,
                document_id=document_id,
                chunk_index=index,
                chunk_text=chunk.page_content,
                embedding=embedding,
                page_number=chunk.metadata.get("page_number"),
            )
            for index, (chunk, embedding) in enumerate(
                zip(chunks, embeddings)
            )
        ]

        db.add_all(chunk_objects)
        doc.status = "completed"
        doc.error_message = None
        db.commit()

        logger.info(
            f"Document {document_id} processed successfully. "
            f"Total chunks: {len(chunks)}"
        )

    except Exception as e:
        db.rollback()

        logger.exception(
            f"Document {document_id} processing failed."
        )

        # Short error message (no stack traces, no secrets)
        raw_error = str(e).strip()
        if not raw_error:
            error_message = "Document processing failed."
        else:
            first_line = raw_error.splitlines()[0]
            error_message = first_line[:255].strip()

        # Delete any partial chunks for this document
        try:
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            db.commit()
        except Exception:
            db.rollback()

        # Update document status to failed
        try:
            update_document_status(
                db=db,
                document_id=document_id,
                status="failed",
                error_message=error_message,
            )
        except Exception:
            db.rollback()
            logger.exception(f"Failed to record status=failed for document {document_id}")

    finally:
        db.close()
