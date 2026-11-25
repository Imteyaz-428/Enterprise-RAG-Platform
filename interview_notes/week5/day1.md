# Week 5 - Day 1: Interview Notes: Citation Validation and Hallucination Control

(Builds on Week 3 Day 1, where citations were first generated from retrieval metadata instead of by the LLM.)

## 1. What was missing in the first version of citations?

- Citations contained only the document name and chunk index.
- No page number, no document id, no snippet.
- Nothing checked that the answer really used the cited sources.
- The model could answer questions that the documents do not cover.

---

## 2. Numbered sources and richer citations

- The prompt lists retrieved chunks as `[1]`, `[2]`, ... `[n]`.
- The model is told to cite each factual statement with the source number, for example `[1]` or `[2][3]`.
- `CitationResponse` gained optional fields: `id`, `document_id`, `page_number`, `snippet` (first 200 characters of the chunk). Existing fields (`document`, `chunk_index`) were kept, so old clients and cached entries still work.
- Retrieved chunks are de-duplicated so source numbers and citation ids map one-to-one.

Citations are still built by the backend from retrieval metadata, not by the model.

---

## 3. The citation validator (pure functions)

`validate_citations(answer, citations, chunk_texts=None)`:

1. Extract markers (`[1]`, `[2][3]`, `[ 4 ]`).
2. Remove markers that do not correspond to a real source id.
3. Return only the citations that are actually used, in order of first appearance, without duplicates.
4. **Number-support check**: for each sentence with markers, the numbers in that sentence must appear in the cited chunk's text (formats like `1,510` and `1510`, or `41%` and `41`, are normalised). If not, that marker is removed from the sentence. Answer text is never deleted, only markers.
5. If no marker is present, return all citations unchanged (legacy behaviour).
6. If the answer is the "not found" sentence, return **no citations**.

Full chunk text is used only inside the validator and is never put into the API response or the cache.

---

## 4. The "not found" behaviour

Exact sentence: `I could not find this in the provided documents.`

- The prompt says: if the sources do not contain the answer, reply with exactly this sentence and nothing else.
- `is_not_found()` recognises it (case and whitespace insensitive).
- In `chat()`, a not-found answer is normalised to the exact sentence before saving and caching.

**Bug found:** an answer arrived as "I could not find this in the provided documents. Say so plainly and cite nothing." An older prompt instruction was still in the system prompt and the model copied it into its answer. The validator only checked the start of the string, so the benchmark still passed. Fix: keep a single rule, remove the old sentence, normalise the answer.

---

## 5. A hallucination the number check cannot catch

Question: "What was Veloura Retail's revenue in FY2026?" The model answered with Project Lotus's Year 1 projection (95 crore) as if it were company revenue and invented the label "FY2026" (the document never mentions FY2026). Both numbers existed in the chunks, so the number check passed.

Lesson: number grounding is not a faithfulness check. Mitigations:

- Scope rule in the prompt: do not combine or reinterpret figures; if the question asks about a specific year or entity and the sources give a different one, use the not-found sentence.
- Trap questions in the benchmark (a related number exists, but the asked scope does not).

---

## 6. Answer-level benchmark

`bench_answers.py` runs the whole pipeline without writing to the database or Redis.

| Check | Result |
|---|---|
| False refusals on 28 answerable questions | 0 / 28 |
| Answerable questions answered with citations | 28 / 28 |
| 3 unanswerable questions × 3 trials | 9 / 9 refused |
| 8 adversarial trap questions × 3 trials | 24 / 24 refused |
| Citation anchor rate (rough proxy) | about 73% to 81% |

Honest notes:

- The "before prompt" run already refused 3 of 3, so the extra scope rule's effect is not proven. LLM output varies between runs.
- The anchor rate is a proxy: a correct citation can lack the exact anchor phrase (the same fact appeared on pages 1, 3 and 4 of one document).
- A single page number in the dataset can mislabel a correct citation as a mismatch when a fact is repeated.

---

## 7. Interview Questions

### Q1. Why shouldn't the LLM generate citations?
It can invent document names or pages. The backend knows which chunks were retrieved.

### Q2. What does the validator do?
Removes invalid markers, keeps only used citations, checks that numbers in a sentence appear in the cited chunk, and returns no citations for a not-found answer.

### Q3. How do you stop answers that the documents cannot support?
A strict prompt, an exact refusal sentence, a scope rule, and trap questions to test it.

### Q4. Give an example of a hallucination your checks could not catch.
The "FY2026 revenue" case: numbers existed in the chunks but the meaning was wrong.

### Q5. How did you measure abstention?
33 trials (24 trap, 9 unanswerable) all refused, with 0 false refusals on 28 answerable questions.

### Q6. Why keep full chunk text out of the API response?
It is large and unnecessary; the snippet is enough for the UI.

### Q7. What would you add next for faithfulness?
An LLM-judged faithfulness metric (for example RAGAS) and a larger, more varied dataset.