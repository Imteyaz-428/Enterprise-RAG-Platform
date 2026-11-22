from pathlib import Path
from sqlalchemy.orm import Session
from models.document import Document
from utils.logger import logger


def create_document(db: Session, document: Document):
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document_by_id(db: Session, document_id: int) -> Document | None:
    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )


def get_accessible_document(db: Session, document_id: int, organization_id: int) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id
        )
        .first()
    )


def get_document_by_hash(db: Session, organization_id: int, file_hash: str) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.organization_id == organization_id,
            Document.file_hash == file_hash,
        )
        .first()
    )


def update_document_status(
    db: Session,
    document_id: int,
    status: str,
    error_message: str | None = None,
):
    document = get_document_by_id(db, document_id)
    if document is None:
        return None

    document.status = status
    document.error_message = error_message
    db.commit()
    db.refresh(document)
    return document


def get_documents(db: Session, organization_id: int):
    return (
        db.query(Document)
        .filter(Document.organization_id == organization_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def delete_document(db: Session, document: Document):
    file_path = document.file_path
    db.delete(document)
    db.commit()

    if file_path:
        try:
            path = Path(file_path)
            if path.is_file():
                path.unlink()
            else:
                logger.warning(
                    f"File not found on disk during document deletion: {file_path}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to delete file on disk {file_path}: {e}"
            )
