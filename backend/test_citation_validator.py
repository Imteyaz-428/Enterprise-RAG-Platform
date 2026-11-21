from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from models.chat_message import ChatMessage
from models.document import Document
from models.document_chunk import DocumentChunk
from schemas.chat import CitationResponse, ChatResponse
from services.chat.citation_validator import (
    extract_markers,
    validate_citations,
    ValidationResult,
)
from services.chat.prompt_service import PromptService
from services.chat.retrieval_result import RetrievalResult
from services.chat.chat_service import ChatService


# =============================================================================
# 1. CITATION VALIDATOR UNIT TESTS
# =============================================================================

def test_extract_markers():
    """Verifies marker extraction for single, adjacent, repeated, and spaced markers."""
    assert extract_markers("Simple fact [1].") == [1]
    assert extract_markers("Adjacent facts [1][2].") == [1, 2]
    assert extract_markers("Repeated facts [1] and [1].") == [1, 1]
    assert extract_markers("Spaced markers [ 3 ] and [4 ].") == [3, 4]
    assert extract_markers("No markers here.") == []
    assert extract_markers("") == []
    assert extract_markers(None) == []


def test_validator_valid_markers():
    """Verifies that valid markers return corresponding citations and unchanged answer."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
        {"id": 2, "document": "doc2.pdf", "chunk_index": 1, "page_number": 2, "snippet": "Text 2"},
    ]
    answer = "Point A is true [1]. Point B is also true [2]."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == answer
    assert len(used) == 2
    assert used[0]["id"] == 1
    assert used[1]["id"] == 2
    assert invalid == []


def test_validator_invalid_marker_removed_and_double_spaces_tidied():
    """Verifies that invalid marker numbers are removed and double spaces/punctuation tidied."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
    ]
    # [99] is invalid and preceded by spaces or followed by period
    answer = "Point A is true [1]  and fake info [99]. Another [99] fact."
    clean, used, invalid = validate_citations(answer, citations)

    assert "[99]" not in clean
    assert "[1]" in clean
    assert "fake info." in clean
    assert "Another fact." in clean
    assert "  " not in clean
    assert invalid == [99, 99]
    assert len(used) == 1
    assert used[0]["id"] == 1


def test_validator_no_marker_returns_all_citations():
    """Verifies that if the answer has no valid marker, all citations are returned unchanged."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
        {"id": 2, "document": "doc2.pdf", "chunk_index": 1, "page_number": 2, "snippet": "Text 2"},
    ]
    answer = "I could not find that information in the uploaded documents."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == answer
    assert used == citations
    assert invalid == []
    # Also verify none_cited flag on result
    result = validate_citations(answer, citations)
    assert result.none_cited is True


def test_validator_only_invalid_markers_returns_all_citations():
    """Verifies that if only invalid markers exist, they are removed and all citations returned."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
    ]
    answer = "Fact with hallucinated citation [99]."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == "Fact with hallucinated citation."
    assert used == citations
    assert invalid == [99]
    assert validate_citations(answer, citations).none_cited is True


def test_validator_repeated_markers_no_duplicate_citations():
    """Verifies that repeated markers in the answer do not duplicate used citations."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
        {"id": 2, "document": "doc2.pdf", "chunk_index": 1, "page_number": 2, "snippet": "Text 2"},
    ]
    answer = "Point A is first [1]. Point A is reiterated [1]. Point B is next [2]."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == answer
    assert len(used) == 2
    assert [c["id"] for c in used] == [1, 2]
    assert invalid == []


def test_validator_adjacent_markers():
    """Verifies handling of adjacent markers like [1][2] and adjacent with invalid [1][99]."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
        {"id": 2, "document": "doc2.pdf", "chunk_index": 1, "page_number": 2, "snippet": "Text 2"},
    ]
    answer = "Combined facts supported by both sources [1][2]."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == answer
    assert len(used) == 2
    assert [c["id"] for c in used] == [1, 2]
    assert invalid == []

    # Adjacent with invalid marker
    answer_mixed = "Combined fact [1][99]."
    clean_mixed, used_mixed, invalid_mixed = validate_citations(answer_mixed, citations)
    assert clean_mixed == "Combined fact [1]."
    assert len(used_mixed) == 1
    assert used_mixed[0]["id"] == 1
    assert invalid_mixed == [99]


def test_validator_order_of_first_appearance():
    """Verifies that used citations preserve the order in which markers first appear in the text."""
    citations = [
        {"id": 1, "document": "doc1.pdf", "chunk_index": 0, "page_number": 1, "snippet": "Text 1"},
        {"id": 2, "document": "doc2.pdf", "chunk_index": 1, "page_number": 2, "snippet": "Text 2"},
        {"id": 3, "document": "doc3.pdf", "chunk_index": 2, "page_number": 3, "snippet": "Text 3"},
    ]
    answer = "Second source fact [2]. First source fact [1]. Third source fact [3]. Second again [2]."
    clean, used, invalid = validate_citations(answer, citations)

    assert [c["id"] for c in used] == [2, 1, 3]


def test_validator_none_page_number():
    """Verifies that citations with None page_number validate without error."""
    citations = [
        {"id": 1, "document": "old_doc.pdf", "chunk_index": 0, "page_number": None, "snippet": "Old text"},
    ]
    answer = "Old document fact [1]."
    clean, used, invalid = validate_citations(answer, citations)

    assert clean == answer
    assert len(used) == 1
    assert used[0]["page_number"] is None


# =============================================================================
# 2. PROMPT SERVICE UNIT TESTS
# =============================================================================

def test_build_prompt_contains_numbered_sources_and_instructions():
    """
    Verifies that PromptService.build_prompt:
    1. Numbers sources [1]..[n] in the context block.
    2. Includes the citation instructions.
    3. Keeps the question line and history handling.
    """
    prompt_service = PromptService()

    doc1 = SimpleNamespace(id=1, original_filename="mba_report.pdf")
    chunk1 = SimpleNamespace(id=101, chunk_index=0, chunk_text="Project Lotus requires INR 410 crore.")
    res1 = RetrievalResult(chunk=chunk1, document=doc1, score=0.95)

    doc2 = SimpleNamespace(id=2, original_filename="google_paper.pdf")
    chunk2 = SimpleNamespace(id=102, chunk_index=0, chunk_text="SparseRoute reduces tokens by 41%.")
    res2 = RetrievalResult(chunk=chunk2, document=doc2, score=0.90)

    history = [ChatMessage(role="user", content="Hello"), ChatMessage(role="assistant", content="Hi!")]
    question = "What is the capital investment?"

    prompt = prompt_service.build_prompt(
        history=history,
        chunks=[res1, res2],
        question=question,
    )

    # Numbered sources in context block
    assert "[1] (mba_report.pdf)" in prompt
    assert "Project Lotus requires INR 410 crore." in prompt
    assert "[2] (google_paper.pdf)" in prompt
    assert "SparseRoute reduces tokens by 41%." in prompt

    # Required instructions
    prompt_lower = prompt.lower()
    assert "answer only from the sources" in prompt_lower
    assert "cite each factual statement with the source number like [1] or [2][3]" in prompt_lower
    assert "if the sources do not contain the answer, say so plainly and cite nothing" in prompt_lower

    # Question line and history preserved
    assert "Current Question" in prompt
    assert question in prompt
    assert "User: Hello" in prompt
    assert "Assistant: Hi!" in prompt


# =============================================================================
# 3. CHAT SERVICE UNIT TESTS (MOCKS ONLY)
# =============================================================================

def test_chat_returns_only_cited_sources():
    """
    Verifies that ChatService.chat() filters citations to return and persist only
    the sources that were actually cited in the generated answer.
    """
    mock_retrieval = MagicMock()
    mock_prompt = MagicMock()
    mock_ai = MagicMock()
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    doc1 = SimpleNamespace(id=10, original_filename="doc1.pdf")
    chunk1 = SimpleNamespace(id=101, chunk_index=0, chunk_text="Fact from doc1.", page_number=1)
    res1 = RetrievalResult(chunk=chunk1, document=doc1, score=0.95)

    doc2 = SimpleNamespace(id=20, original_filename="doc2.pdf")
    chunk2 = SimpleNamespace(id=102, chunk_index=1, chunk_text="Fact from doc2.", page_number=2)
    res2 = RetrievalResult(chunk=chunk2, document=doc2, score=0.85)

    mock_retrieval.retrieve.return_value = [res1, res2]
    mock_prompt.build_prompt.return_value = "Mock prompt with [1] and [2]"
    # AI generates answer citing only source [1] and hallucinating [99]
    mock_ai.generate_answer.return_value = "Only source one fact is used [1] and fake [99]."

    service = ChatService(
        retrieval_service=mock_retrieval,
        prompt_service=mock_prompt,
        ai_service=mock_ai,
        redis=mock_redis,
    )

    mock_db = MagicMock()
    # Mock session lookup / creation
    mock_session = SimpleNamespace(id=123, title="Test Chat")
    service._get_or_create_session = MagicMock(return_value=mock_session)

    result = service.chat(
        db=mock_db,
        question="Tell me about doc1",
        organization_id=1,
        user_id=1,
    )

    # Clean answer has invalid [99] removed
    assert result["answer"] == "Only source one fact is used [1] and fake."
    # Citations returned must contain ONLY the cited source [1]
    assert len(result["citations"]) == 1
    assert result["citations"][0]["id"] == 1
    assert result["citations"][0]["document"] == "doc1.pdf"
    assert result["citations"][0]["page_number"] == 1
    assert result["citations"][0]["snippet"] == "Fact from doc1."

    # Cache set must have received only the clean answer and used citations
    mock_redis.set.assert_called_once()
    cached_value = mock_redis.set.call_args[0][1]
    assert cached_value["answer"] == result["answer"]
    assert len(cached_value["citations"]) == 1
    assert cached_value["citations"][0]["document"] == "doc1.pdf"


# =============================================================================
# 4. SCHEMA BACKWARD AND FORWARD COMPATIBILITY
# =============================================================================

def test_citation_response_accepts_old_and_new_dicts():
    """
    Verifies that CitationResponse and ChatResponse seamlessly accept both
    legacy citation dicts (document, chunk_index) and new extended dicts.
    """
    old_dict = {
        "document": "legacy_doc.pdf",
        "chunk_index": 3,
    }
    old_citation = CitationResponse(**old_dict)
    assert old_citation.document == "legacy_doc.pdf"
    assert old_citation.chunk_index == 3
    assert old_citation.id is None
    assert old_citation.document_id is None
    assert old_citation.page_number is None
    assert old_citation.snippet is None

    new_dict = {
        "id": 1,
        "document": "modern_doc.pdf",
        "document_id": 42,
        "chunk_index": 5,
        "page_number": 8,
        "snippet": "First 200 chars of snippet text...",
    }
    new_citation = CitationResponse(**new_dict)
    assert new_citation.id == 1
    assert new_citation.document == "modern_doc.pdf"
    assert new_citation.document_id == 42
    assert new_citation.chunk_index == 5
    assert new_citation.page_number == 8
    assert new_citation.snippet == "First 200 chars of snippet text..."

    # ChatResponse can hold a mixture of old and new citations
    response = ChatResponse(
        session_id=1,
        answer="Answer text with citations [1].",
        citations=[old_citation, new_citation],
    )
    assert len(response.citations) == 2
    assert response.citations[0].document == "legacy_doc.pdf"
    assert response.citations[1].page_number == 8
