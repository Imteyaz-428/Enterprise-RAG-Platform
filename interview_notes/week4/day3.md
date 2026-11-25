# Week 4 - Day 3: Interview Notes: Evaluation First (Hit@K, MRR, Benchmark Design)

## 1. Why measure before improving?

Without measurement, an "improvement" is only a feeling. A benchmark makes every change comparable and shows when a change did nothing (or made things worse).

Principle used throughout: **change one thing, run the same benchmark, keep the change only if the numbers justify it.**

---

## 2. Metrics

- **Hit@K**: fraction of questions where a chunk containing the answer text is in the top K results.
- **MRR (Mean Reciprocal Rank)**: average of `1 / rank` of the first correct chunk (0 if none).
- **Page match**: when the answer is found, is the chunk's page in the expected page list?
- **Duplicate rate**: share of duplicate chunk texts in the top K.
- **Latency**: mean and p95 of retrieval time.

Hit@K measures retrieval, not answer correctness. Answer-level metrics were added later (see Week 5).

---

## 3. Dataset design

Each JSONL line:

```json
{"id": "mba-02", "source": "mba-report",
 "question": "What total capital investment does Project Lotus require?",
 "must_contain_any": ["total capital investment of inr 410 crore"],
 "pages": [1]}
```

Key decisions:

- **Text anchors as ground truth, not document ids.** The same PDF had been uploaded several times, so ids were unreliable. A hit means a top-K chunk contains the anchor text (case and whitespace normalised).
- **Anchors verified against the PDFs** page by page before running (28 of 28 were correct).
- **`dataset_error` vs `miss`**: if the anchor text is not in the ingested corpus at all, it is a dataset problem, not a retrieval failure.
- **Unanswerable questions** (`answerable: false`) are skipped for retrieval metrics and used later for abstention tests.
- **Per-organization datasets**: documents lived in different organizations, so each dataset is run with its own `--org-id`.

Documents used: a university OS lab PDF, a synthetic business report ("Project Lotus"), and a synthetic research paper ("SparseRoute"). Personal PDFs (resume, scorecards) were deliberately excluded.

---

## 4. Tooling

- `bench_retrieval.py`: runs the benchmark, prints a report with misses, saves JSON and a CSV summary.
- Flags: `--no-rerank` (measure the reranker's contribution), `--rewrite` (use the query rewriter for follow-ups).
- `embed_cache.py`: caches query embeddings on disk and paces live calls (free-tier rate limits), so repeated runs are instant and deterministic.
- `inspect_corpus.py`: lists documents, statuses and chunk counts per organization, and finds which documents contain a phrase.

---

## 5. Early lessons

- The first self-made benchmark was **saturated** (Hit@5 = 1.0 on 8 easy questions) and reported `page_match 0.0` because of a bug, so it proved nothing.
- On a tiny corpus (one 16-chunk document), the old and new code gave identical numbers. Improvements need **distractors**: several documents and about 80 chunks.
- All questions returned `dataset_error` once because the documents were in a different organization than the benchmark used.
- LLM-dependent runs are **noisy**: the same code produced Hit@1 from 0.455 to 0.727 on 11 follow-up questions. Hit@5 is more stable; small samples must be called small.

---

## 6. Interview Questions

### Q1. Why did you build an evaluation set before optimising?
To compare changes objectively and avoid claiming improvements that were noise.

### Q2. What are Hit@K and MRR?
Hit@K is the share of questions with a correct chunk in the top K. MRR averages the reciprocal rank of the first correct chunk.

### Q3. Why use text anchors instead of document ids?
Duplicate uploads make ids unreliable; text anchors are stable across re-uploads.

### Q4. What is the weakness of your benchmark?
It is small (28 and 8 questions) and built on synthetic documents, so results are reported as "on my evaluation set".

### Q5. Why can a tiny corpus hide improvements?
Almost everything is retrieved anyway; with few distractors, ranking changes do not show.

### Q6. How do you handle noisy LLM-dependent metrics?
Repeat runs, prefer recall-style metrics (Hit@5), and state the sample size.

### Q7. What is a `dataset_error`?
The expected evidence is not in the ingested corpus, so the failure is in the data setup, not in retrieval.