from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    users = relationship("User",back_populates="organization",cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization")