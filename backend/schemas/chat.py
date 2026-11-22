from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: int | None = None


class CitationResponse(BaseModel):
    document: str
    chunk_index: int
    id: int | None = None
    document_id: int | None = None
    page_number: int | None = None
    snippet: str | None = None


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    citations: list[CitationResponse]