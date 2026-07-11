from sqlalchemy.orm import Session
from models.document import Document

def create_document(db: Session, document: Document):

    db.add(document)
    db.commit()
    db.refresh(document)

    return document