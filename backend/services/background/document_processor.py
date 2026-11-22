from database.database import SessionLocal
from crud.document import get_document_by_id, update_document_status
from models.document_chunk import DocumentChunk
from utils.chunker import split_documents, strip_repeated_headers_and_footers
from utils.embedding import generate_embeddings, split_chunks_into_batches
from utils.retry import retry_request
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

        # 4. Split chunks into embedding batches of at most EMBED_BATCH_TOKENS (estimate tokens as len(text)/3)
        chunk_batches = split_chunks_into_batches(chunks)

        # 5. Embed batch by batch, retrying on 429 with exponential backoff up to 5 times
        embeddings = []
        for batch in chunk_batches:
            batch_texts = [chunk.page_content for chunk in batch]
            batch_embeddings = retry_request(
                generate_embeddings,
                batch_texts,
                max_attempts=5,
            )
            embeddings.extend(batch_embeddings)

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
