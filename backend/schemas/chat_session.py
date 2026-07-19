from datetime import datetime

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    title: str


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    organization_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True