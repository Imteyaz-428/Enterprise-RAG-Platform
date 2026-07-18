from sqlalchemy.orm import Session
from models.document import Document


def create_document(db: Session, document: Document):
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document_by_id( db: Session,document_id: int) -> Document | None:

    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )
    
def get_accessible_document( db: Session, document_id: int, organization_id: int) -> Document | None:

    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id
        )
        .first()
    )