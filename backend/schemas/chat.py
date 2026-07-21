from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: int | None = None


class CitationResponse(BaseModel):
    document: str
    chunk_index: int


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    citations: list[CitationResponse]