from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime
from core.enums import UserRole


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String,unique=True, nullable=False,index=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole),nullable=False)
    organization_id = Column(  Integer, ForeignKey("organizations.id"),  nullable=False)
    created_at = Column(DateTime,default=datetime.utcnow)
    organization = relationship("Organization", back_populates="users")
    documents = relationship("Document", back_populates="uploader")