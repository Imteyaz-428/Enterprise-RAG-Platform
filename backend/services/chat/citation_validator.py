import re
from typing import Any, List, Set, Tuple


class ValidationResult(tuple):
    clean_answer: str
    used_citations: list
    invalid_markers: list[int]
    none_cited: bool

    def __new__(
        cls,
        clean_answer: str,
        used_citations: list,
        invalid_markers: list[int],
        none_cited: bool = False,
    ):
        instance = super().__new__(
            cls, (clean_answer, used_citations, invalid_markers)
        )
        instance.clean_answer = clean_answer
        instance.used_citations = used_citations
        instance.invalid_markers = invalid_markers
        instance.none_cited = none_cited
        return instance


def extract_markers(answer: str) -> list[int]:
    """
    Extracts all citation marker numbers in order of appearance.
    Matches markers like [1], [2][3], [ 4 ].
    """
    if not answer or not isinstance(answer, str):
        return []
    return [int(m) for m in re.findall(r"\[\s*(\d+)\s*\]", answer)]


def _get_citation_id(citation: Any, default_id: int) -> int:
    if isinstance(citation, dict):
        cid = citation.get("id")
    else:
        cid = getattr(citation, "id", None)
    return cid if isinstance(cid, int) else default_id


def validate_citations(
    answer: str,
    citations: list[Any] | None,
) -> ValidationResult:
    """
    Validates citation markers in the answer against available sources.

    - Removes markers whose number is not a source ID and tidies leftover double spaces.
    - Returns the citations actually cited, in order of first appearance.
    - If the answer has no valid marker, returns all citations unchanged and
      reports that none were cited (none_cited=True).
    """
    if answer is None:
        answer = ""
    citations = citations or []

    citation_by_id = {}
    for idx, cit in enumerate(citations, start=1):
        cid = _get_citation_id(cit, default_id=idx)
        citation_by_id[cid] = cit
    valid_source_ids: Set[int] = set(citation_by_id.keys())

    invalid_markers: list[int] = []
    valid_markers: list[int] = []

    for match in re.finditer(r"\[\s*(\d+)\s*\]", answer):
        num = int(match.group(1))
        if num in valid_source_ids:
            valid_markers.append(num)
        else:
            invalid_markers.append(num)

    def _replace_invalid(match: re.Match) -> str:
        num = int(match.group(1))
        if num not in valid_source_ids:
            return ""
        return match.group(0)

    clean_answer = re.sub(r"\[\s*(\d+)\s*\]", _replace_invalid, answer)
    # Tidy leftover double spaces
    clean_answer = re.sub(r" {2,}", " ", clean_answer)
    # Tidy spaces before punctuation like " ." or " ,"
    clean_answer = re.sub(r" +([.,;!?])", r"\1", clean_answer)
    # Tidy leading spaces at newline boundaries
    clean_answer = re.sub(r"\n +", "\n", clean_answer)
    clean_answer = clean_answer.strip()

    if valid_markers:
        seen: Set[int] = set()
        used_citations = []
        for marker in valid_markers:
            if marker not in seen:
                seen.add(marker)
                used_citations.append(citation_by_id[marker])
        none_cited = False
    else:
        used_citations = list(citations)
        none_cited = True

    return ValidationResult(
        clean_answer,
        used_citations,
        invalid_markers,
        none_cited=none_cited,
    )
