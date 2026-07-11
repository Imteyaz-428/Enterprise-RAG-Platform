from sqlalchemy import Column, Integer, ForeignKey, Text
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

    chunk_index = Column(Integer, nullable=False)

    chunk_text = Column(Text, nullable=False)

    embedding = Column(Vector(1024))
    document = relationship( "Document", back_populates="chunks")

