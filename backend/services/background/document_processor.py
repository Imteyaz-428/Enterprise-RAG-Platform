
from database.database import SessionLocal

from crud.document import update_document_status
from crud.document_chunk import create_document_chunk

from utils.chunker import split_documents
from utils.embedding import generate_embeddings
from utils.pdf import extract_documents_from_pdf
from utils.logger import logger


def process_document(
    document_id: int,
    file_path: str,
):
    db = SessionLocal()

    try:
        # 1. Extract PDF page by page
        documents = extract_documents_from_pdf(
            file_path=file_path,
            document_id=document_id,
        )

        if not documents:
            raise ValueError(
                "No extractable text found in PDF."
            )

        # 2. Split LangChain Documents
        chunks = split_documents(
            documents,
            chunk_size=1000,
            overlap=200,
        )

        if not chunks:
            raise ValueError("No chunks generated.")

        # 3. Extract chunk text for embeddings
        chunk_texts = [
            chunk.page_content
            for chunk in chunks
        ]

        # 4. Generate Voyage AI embeddings
        embeddings = generate_embeddings(
            chunk_texts
        )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embedding count does not match chunk count."
            )

        # 5. Store chunks and metadata
        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):

            create_document_chunk(
                db=db,
                document_id=document_id,
                chunk_index=index,
                chunk_text=chunk.page_content,
                embedding=embedding,
                page_number=chunk.metadata.get("page_number"),
            )

        # 6. Mark document completed
        update_document_status(
            db=db,
            document_id=document_id,
            status="completed",
        )

        logger.info(
            f"Document {document_id} processed successfully. "
            f"Total chunks: {len(chunks)}"
        )

    except Exception:
        db.rollback()

        logger.exception(
            f"Document {document_id} processing failed."
        )

        update_document_status(
            db=db,
            document_id=document_id,
            status="failed",
        )

    finally:
        db.close()
