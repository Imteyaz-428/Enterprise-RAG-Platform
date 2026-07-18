from pydantic import BaseModel


class ChatRequest(BaseModel):
    document_id: int
    question: str


class ChatResponse(BaseModel):
    answer: str