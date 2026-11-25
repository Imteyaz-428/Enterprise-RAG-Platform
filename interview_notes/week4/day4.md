# Week 4 - Day 4: Interview Notes: Hybrid Retrieval, RRF and Cross-Encoder Reranking

## 1. Why hybrid retrieval?

- **Vector search** captures meaning but can miss exact terms and numbers (for example "INR 410 crore" or an id).
- **Full-text (keyword) search** finds exact tokens but misses paraphrases.

Combining both covers both weaknesses.

---

## 2. How hybrid search works here

Both searches are scoped to the user's organization and only to documents with `status = completed`.

1. **Vector search**: pgvector cosine similarity on the question embedding (Voyage `voyage-3-large`, 1024 dimensions) → top 20.
2. **Keyword search**: PostgreSQL full-text search (`tsvector` / `tsquery`) → top 20.
3. **RRF fusion** → one ranked list of candidates.

---

## 3. Reciprocal Rank Fusion (RRF)

```text
score(d) = Σ over lists of 1 / (k + rank_list(d))      with k = 60
```

- Uses only ranks, not raw scores, so it does not matter that cosine similarity and text rank are on different scales.
- No weights to tune; robust in practice.

---

## 4. Cross-encoder reranking

- **Bi-encoder** (embeddings): query and chunk are encoded separately. Fast, good for searching a whole index, less precise.
- **Cross-encoder**: the model reads the **(query, chunk) pair together**. More accurate, but one forward pass per pair, so it is too slow for the whole index.

Therefore: retrieve about 20 candidates cheaply, then let the cross-encoder pick the best 5.

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (device selection: Apple MPS, CUDA or CPU).

---

## 5. The bug that made the reranker useless

`retrieve()` asked the hybrid search for only **5** results, and the reranker re-ordered those same 5 into 5.

Fix: add `RERANK_CANDIDATES = 20`. Hybrid search returns 20 fused candidates, the reranker returns the top 5.

---

## 6. Results (28 questions)

| Setup | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Fused only (`--no-rerank`) | 0.643 | 0.964 | 1.0 | 0.805 |
| Fused + cross-encoder (20 → 5) | 0.929 | 1.0 | 1.0 | 0.964 |

Honest reading:

- The gain came from the reranker. Hit@5 was already 1.0, so recall was saturated on this small corpus.
- The benchmark could not separate "20 candidates" from "5 candidates"; it only showed that reranking improves the ordering.
- Reranker cost is small: about 0.2 to 0.3 seconds extra per query for 20 candidates on CPU.

---

## 7. Interview Questions

### Q1. Why combine vector and keyword search?
Vector search handles semantics; keyword search handles exact terms and numbers.

### Q2. What is RRF and why use it?
It fuses ranked lists by summing `1/(k+rank)`. It ignores incompatible score scales and needs no tuning.

### Q3. Why is the reranker applied only to the top 20?
A cross-encoder runs one model pass per candidate, so it is too slow for a full index.

### Q4. Bi-encoder vs cross-encoder?
Bi-encoders embed texts independently (fast, approximate). Cross-encoders score a pair jointly (slow, accurate).

### Q5. What was wrong with the original reranking?
It reranked only 5 candidates into 5, so it could only reorder, never recover a better chunk.

### Q6. What did the results show?
Hit@1 rose from 0.643 to 0.929 and MRR from 0.805 to 0.964 on the same 28 questions.

### Q7. What is the limitation of that conclusion?
Hit@5 was already perfect on a small corpus, so the benchmark proves better ordering, not better recall.