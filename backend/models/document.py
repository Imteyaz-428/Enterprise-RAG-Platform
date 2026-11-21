from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    status = Column(String, nullable=False, default="processing")

    organization = relationship("Organization", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_documents_org_file_hash",
            "organization_id",
            "file_hash",
            unique=True,
            postgresql_where=text("file_hash IS NOT NULL"),
            sqlite_where=text("file_hash IS NOT NULL"),
        ),
    )
