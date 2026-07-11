from pydantic import BaseModel, Field
from typing import List


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=1000
    )


class SearchResult(BaseModel):
    chunk_text: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]