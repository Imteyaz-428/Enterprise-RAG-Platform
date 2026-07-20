from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: int | None = None


class ChatResponse(BaseModel):
    session_id: int
    answer: str