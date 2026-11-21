from sqlalchemy import Column, Integer, ForeignKey, Text, event
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_index = Column(Integer, nullable=False)

    page_number = Column(Integer, nullable=True)

    chunk_text = Column(Text, nullable=False)

    embedding = Column(Vector(1024))

    document = relationship(
        "Document",
        back_populates="chunks"
    )

    def __init__(self, **kwargs):
        if "organization_id" not in kwargs and "document" in kwargs and kwargs["document"] is not None:
            kwargs["organization_id"] = kwargs["document"].organization_id
        super().__init__(**kwargs)


@event.listens_for(DocumentChunk, "before_insert")
def populate_chunk_organization_id(mapper, connection, target):
    """Automatically populate organization_id from associated document if missing."""
    if target.organization_id is None and target.document is not None:
        target.organization_id = target.document.organization_id
