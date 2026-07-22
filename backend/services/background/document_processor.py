from database.database import SessionLocal

from crud.document import update_document_status
from crud.document_chunk import create_document_chunk

from utils.chunker import chunk_text
from utils.embedding import generate_embeddings
from utils.pdf import extract_text_from_pdf
from utils.logger import logger


def process_document(
    document_id: int,
    file_path: str,
):

    db = SessionLocal()

    try:

        text = extract_text_from_pdf(
            file_path
        )

        chunks = chunk_text(
            text
        )

        embeddings = generate_embeddings(
            chunks
        )

        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):

            create_document_chunk(
                db=db,
                document_id=document_id,
                chunk_index=index,
                chunk_text=chunk,
                embedding=embedding,
            )

        update_document_status(
            db=db,
            document_id=document_id,
            status="completed",
        )

        logger.info(
            f"Document {document_id} processed successfully."
        )

    except Exception:

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