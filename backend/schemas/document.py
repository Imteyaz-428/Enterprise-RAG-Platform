from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class DocumentResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    file_size: int
    file_hash: Optional[str] = None
    error_message: Optional[str] = None
    uploaded_at: datetime
    organization_id: int
    uploaded_by: int
    status: str
    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
