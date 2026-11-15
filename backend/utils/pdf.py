import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> str:
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


import fitz
from pathlib import Path
from langchain_core.documents import Document


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF."""

    with fitz.open(file_path) as pdf:
        return "\n".join(
            page.get_text()
            for page in pdf
        )


def extract_documents_from_pdf(
    file_path: str,
    document_id: int
) -> list[Document]:
    """
    Extract PDF page by page and create LangChain Documents.
    Each page retains its source metadata.
    """

    documents = []

    with fitz.open(file_path) as pdf:

        for page_index, page in enumerate(pdf):

            text = page.get_text().strip()

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "document_id": document_id,
                        "page_number": page_index + 1,
                        "source": Path(file_path).name,
                    }
                )
            )

    return documents
