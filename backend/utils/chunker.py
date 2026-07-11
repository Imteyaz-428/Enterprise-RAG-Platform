from typing import List

def chunk_text( text: str,chunk_size: int = 500, overlap: int = 100) -> List[str]:

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks