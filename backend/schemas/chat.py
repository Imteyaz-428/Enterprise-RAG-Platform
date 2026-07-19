from pydantic import BaseModel


class ChatRequest(BaseModel):
    document_id: int
    question: str
    session_id: int | None = None

class ChatResponse(BaseModel):
    session_id: int
    answer: str