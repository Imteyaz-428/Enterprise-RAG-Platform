
import fitz

from utils.pdf import extract_documents_from_pdf
from utils.chunker import split_documents


def test_pdf_metadata_is_preserved(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    # Create a temporary two-page PDF.
    with fitz.open() as pdf:
        page1 = pdf.new_page()
        page1.insert_text(
            (72, 72),
            "Artificial Intelligence and Machine Learning."
        )

        page2 = pdf.new_page()
        page2.insert_text(
            (72, 72),
            "Deep Learning uses neural networks."
        )

        pdf.save(pdf_path)

    documents = extract_documents_from_pdf(
        file_path=str(pdf_path),
        document_id=1,
    )

    assert len(documents) == 2
    assert documents[0].metadata["page_number"] == 1
    assert documents[1].metadata["page_number"] == 2

    chunks = split_documents(
        documents,
        chunk_size=1000,
        overlap=200,
    )

    assert len(chunks) == 2

    for chunk in chunks:
        assert chunk.metadata["document_id"] == 1
        assert chunk.metadata["page_number"] in [1, 2]
        assert "start_index" in chunk.metadata
        assert chunk.page_content.strip()
