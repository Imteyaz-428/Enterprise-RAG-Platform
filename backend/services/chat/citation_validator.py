import re
from typing import Any, Dict, List, Set, Tuple

from utils.logger import logger

NOT_FOUND_ANSWER = "I could not find this in the provided documents."


class ValidationResult(tuple):
    clean_answer: str
    used_citations: list
    invalid_markers: list[int]
    none_cited: bool
    marker_actions: list[dict]

    def __new__(
        cls,
        clean_answer: str,
        used_citations: list,
        invalid_markers: list[int],
        none_cited: bool = False,
        marker_actions: list[dict] | None = None,
    ):
        instance = super().__new__(
            cls, (clean_answer, used_citations, invalid_markers)
        )
        instance.clean_answer = clean_answer
        instance.used_citations = used_citations
        instance.invalid_markers = invalid_markers
        instance.none_cited = none_cited
        instance.marker_actions = marker_actions or []
        return instance


def is_not_found(answer: str | None) -> bool:
    """
    Checks if the answer starts with NOT_FOUND_ANSWER, case and whitespace insensitive.
    """
    if not answer or not isinstance(answer, str):
        return False
    norm_answer = " ".join(answer.strip().split()).lower()
    norm_target = " ".join(NOT_FOUND_ANSWER.strip().split()).lower()
    return norm_answer.startswith(norm_target)


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


def extract_sentence_numbers(sentence: str) -> list[str]:
    """
    Extracts numbers from a sentence (digits with optional decimals;
    ignores commas, %, currency symbols/words; ignores one-digit numbers
    unless that is all the sentence has).
    Citation markers like [1] are removed prior to extraction.
    """
    text = re.sub(r"\[\s*\d+\s*\]", "", sentence)
    matches = re.findall(r"(?:[\$€£₹]?\d+(?:,\d+)*(?:\.\d+)?%?)", text)

    cleaned_nums = []
    for m in matches:
        cleaned = re.sub(r"[^\d.]", "", m).rstrip(".")
        if cleaned and any(c.isdigit() for c in cleaned):
            cleaned_nums.append(cleaned)

    if not cleaned_nums:
        return []

    multi_digit = [n for n in cleaned_nums if not (len(n) == 1 and n.isdigit())]
    if multi_digit:
        return multi_digit
    return cleaned_nums


def extract_chunk_numbers(chunk_text: str) -> set[str]:
    """
    Extracts all normalized numbers from chunk text for comparison.
    """
    if not chunk_text or not isinstance(chunk_text, str):
        return set()
    matches = re.findall(r"(?:[\$€£₹]?\d+(?:,\d+)*(?:\.\d+)?%?)", chunk_text)
    nums = set()
    for m in matches:
        cleaned = re.sub(r"[^\d.]", "", m).rstrip(".")
        if cleaned:
            nums.add(cleaned)
    return nums


def _number_appears_in_chunk(num: str, chunk_text: str) -> bool:
    """
    Checks if a normalized number appears in chunk text, accounting for
    format variants (e.g. 1,510 vs 1510, 41% vs 41).
    """
    if not chunk_text or not isinstance(chunk_text, str):
        return False
    chunk_nums = extract_chunk_numbers(chunk_text)
    if num in chunk_nums:
        return True
    try:
        val = float(num)
        for cn in chunk_nums:
            try:
                if float(cn) == val:
                    return True
            except ValueError:
                pass
    except ValueError:
        pass
    return False


def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into sentences while preserving all delimiters, whitespace,
    and markers attached before or after punctuation.
    """
    pattern = r'([.!?]+(?:\s*\[\s*\d+\s*\])*\s+|\n+)'
    tokens = re.split(pattern, text)
    sentences = []
    for i in range(0, len(tokens), 2):
        chunk = tokens[i]
        delim = tokens[i + 1] if i + 1 < len(tokens) else ""
        s = chunk + delim
        if s:
            sentences.append(s)
    return sentences


def validate_citations(
    answer: str,
    citations: list[Any] | None,
    chunk_texts: dict[int, str] | None = None,
) -> ValidationResult:
    """
    Validates citation markers in the answer against available sources.

    - If answer is a not-found answer, returns an EMPTY used_citations list (none_cited=True).
    - Removes markers whose number is not a source ID and tidies leftover double spaces.
    - If chunk_texts is provided, performs numerical support check per sentence:
      extracts numbers; if at least one number, keeps marker only if at least one number
      appears in that source's chunk text; otherwise removes that marker from that sentence
      and logs a WARNING. If sentence has no numbers, keeps its markers. Never deletes answer text.
    - Returns the citations actually cited, in order of first appearance.
    - If the answer has no valid marker (or all markers are removed), falls back to today's
      behaviour: empty citations if not found, all citations if not 'not found' (none_cited=True).
    """
    if answer is None:
        answer = ""
    citations = citations or []

    if is_not_found(answer):
        return ValidationResult(
            NOT_FOUND_ANSWER,
            [],
            [],
            none_cited=True,
            marker_actions=[{"action": "not_found", "reason": "Answer is a not-found response"}],
        )

    citation_by_id = {}
    for idx, cit in enumerate(citations, start=1):
        cid = _get_citation_id(cit, default_id=idx)
        citation_by_id[cid] = cit
    valid_source_ids: Set[int] = set(citation_by_id.keys())

    invalid_markers: list[int] = []
    valid_markers: list[int] = []
    marker_actions: list[dict] = []

    for match in re.finditer(r"\[\s*(\d+)\s*\]", answer):
        num = int(match.group(1))
        if num in valid_source_ids:
            valid_markers.append(num)
        else:
            invalid_markers.append(num)
            marker_actions.append(
                {"marker": num, "action": "removed", "reason": f"Invalid marker [{num}]: not in source IDs"}
            )

    def _replace_invalid(match: re.Match) -> str:
        num = int(match.group(1))
        if num not in valid_source_ids:
            return ""
        return match.group(0)

    clean_answer = re.sub(r"\[\s*(\d+)\s*\]", _replace_invalid, answer)
    clean_answer = re.sub(r" {2,}", " ", clean_answer)
    clean_answer = re.sub(r" +([.,;!?])", r"\1", clean_answer)
    clean_answer = re.sub(r"\n +", "\n", clean_answer)
    clean_answer = clean_answer.strip()

    # Numerical support check
    if chunk_texts is not None:
        sentences = split_into_sentences(clean_answer)
        clean_sentences = []

        for sent in sentences:
            sent_markers = extract_markers(sent)
            if not sent_markers:
                clean_sentences.append(sent)
                continue

            sent_numbers = extract_sentence_numbers(sent)
            if sent_numbers:
                markers_to_remove = []
                for m in sent_markers:
                    ch_text = chunk_texts.get(m, "")
                    matching = [
                        num for num in sent_numbers
                        if _number_appears_in_chunk(num, ch_text)
                    ]
                    if matching:
                        marker_actions.append(
                            {"marker": m, "action": "kept", "reason": f"Supported by number(s) {matching} in source {m}"}
                        )
                    else:
                        markers_to_remove.append(m)
                        marker_actions.append(
                            {
                                "marker": m,
                                "action": "removed",
                                "reason": f"Source {m} does not contain any sentence numbers {sent_numbers}",
                            }
                        )
                        logger.warning(
                            f"Citation marker [{m}] removed from sentence: "
                            f"source {m} chunk does not contain any of numbers {sent_numbers}"
                        )

                # Remove unsupported markers from this sentence
                for m in markers_to_remove:
                    sent = re.sub(rf"\[\s*{m}\s*\]", "", sent)
                sent = re.sub(r" {2,}", " ", sent)
                sent = re.sub(r" +([.,;!?])", r"\1", sent)
            else:
                for m in sent_markers:
                    marker_actions.append(
                        {"marker": m, "action": "kept", "reason": "Sentence has no numbers (kept by rule)"}
                    )

            clean_sentences.append(sent)

        clean_answer = "".join(clean_sentences)
        clean_answer = re.sub(r" {2,}", " ", clean_answer)
        clean_answer = re.sub(r" +([.,;!?])", r"\1", clean_answer)
        clean_answer = re.sub(r"\n +", "\n", clean_answer)
        clean_answer = clean_answer.strip()

    surviving_markers = extract_markers(clean_answer)
    if surviving_markers:
        seen: Set[int] = set()
        used_citations = []
        for marker in surviving_markers:
            if marker in citation_by_id and marker not in seen:
                seen.add(marker)
                used_citations.append(citation_by_id[marker])
        none_cited = False
    else:
        # Fall back to today's behaviour for "no valid marker"
        if is_not_found(clean_answer):
            used_citations = []
        else:
            used_citations = list(citations)
        none_cited = True

    return ValidationResult(
        clean_answer,
        used_citations,
        invalid_markers,
        none_cited=none_cited,
        marker_actions=marker_actions,
    )
