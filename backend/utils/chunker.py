
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter(
    chunk_size: int = 1000,
    overlap: int = 200
):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size"
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=[
            "\n\n",
            "\n",
            " ",
            "",
        ],
        strip_whitespace=True,
        add_start_index=True,
    )


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[str]:
    """Split plain text into chunks."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text.strip():
        return []

    splitter = get_text_splitter(chunk_size, overlap)

    return splitter.split_text(text)


def split_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Document]:
    """
    Split LangChain Documents while preserving metadata.
    """

    if not documents:
        return []

    splitter = get_text_splitter(chunk_size, overlap)

    return splitter.split_documents(documents)
