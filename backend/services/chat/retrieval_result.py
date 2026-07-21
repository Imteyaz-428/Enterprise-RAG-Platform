from dataclasses import dataclass

from models.document import Document
from models.document_chunk import DocumentChunk


@dataclass
class RetrievalResult:
    chunk: DocumentChunk
    document: Document
    score: float