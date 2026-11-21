import math
from collections import defaultdict
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


def strip_repeated_headers_and_footers(
    documents: List[Document],
) -> List[Document]:
    """
    Before chunking, remove repeated header/footer lines:
    a normalised line that appears at the top or bottom of at least 50% of pages
    and on 3 or more pages.
    """
    if len(documents) < 3:
        return documents

    total_pages = len(documents)
    threshold = max(3, math.ceil(total_pages * 0.5))

    line_page_counts: dict[str, int] = defaultdict(int)

    for doc in documents:
        lines = [line.strip() for line in doc.page_content.splitlines() if line.strip()]
        if not lines:
            continue
        top_line = lines[0]
        bottom_line = lines[-1]
        seen_on_page = {top_line, bottom_line}
        for line in seen_on_page:
            line_page_counts[line] += 1

    repeated_lines = {
        line for line, count in line_page_counts.items()
        if count >= threshold
    }

    if not repeated_lines:
        return documents

    cleaned_docs = []
    for doc in documents:
        lines = doc.page_content.splitlines()

        # Strip matching repeated header from top
        while lines:
            stripped = lines[0].strip()
            if not stripped:
                lines.pop(0)
            elif stripped in repeated_lines:
                lines.pop(0)
                break
            else:
                break

        # Strip matching repeated footer from bottom
        while lines:
            stripped = lines[-1].strip()
            if not stripped:
                lines.pop()
            elif stripped in repeated_lines:
                lines.pop()
                break
            else:
                break

        doc.page_content = "\n".join(lines).strip()
        cleaned_docs.append(doc)

    return cleaned_docs
