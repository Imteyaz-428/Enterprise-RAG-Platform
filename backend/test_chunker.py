
from utils.chunker import chunk_text


def test_chunk_text_returns_chunks():
    text = """
    Artificial Intelligence is transforming industries.

    Machine Learning is a subset of Artificial Intelligence.
    It allows computers to learn patterns from data.

    Deep Learning uses neural networks with multiple layers.
    It is widely used in computer vision and NLP.
    """

    chunks = chunk_text(
        text,
        chunk_size=100,
        overlap=20,
    )

    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_chunk_text_empty_input():
    assert chunk_text("") == []


def test_chunk_text_invalid_overlap():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("Some text", chunk_size=100, overlap=100)
