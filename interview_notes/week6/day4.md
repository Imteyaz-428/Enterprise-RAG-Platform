# Week 6 - Day 4: Interview Notes: Complete Interview Question Bank (with Short Answers)

Use this file for mock interviews: read the question, answer aloud, then compare.

---

## A. Project overview

### Q1. Describe the project in 30 seconds.
A multi-tenant document Q&A platform. Users upload PDFs and ask questions; answers come with page-level citations. Retrieval is hybrid (vector + full-text with RRF) followed by a cross-encoder reranker. I built an evaluation set and raised Hit@1 from 78.6% to 92.9%. It is deployed on free tiers.

### Q2. Walk me through what happens when a user asks a question.
Query rewriting (if there is history) → cache lookup → embed query → hybrid search scoped to the organization → RRF → rerank top 20 to top 5 → prompt with numbered sources → LLM via fallback chain, streamed over SSE → citation validation → cache and save.

### Q3. What is the difference between your system and naive RAG?
Query rewriting, hybrid search, reranking, numbered citations with validation, abstention on unanswerable questions, tenant isolation, evaluation, and production concerns.

### Q4. What was the hardest problem?
Fitting the backend into 512 MB: PyTorch ran out of memory, so I replaced the reranker with a 22 MB int8 ONNX model with equal benchmark results.

---

## B. Retrieval and ranking

### Q5. Why hybrid retrieval?
Vector search handles meaning; keyword search handles exact terms and numbers.

### Q6. What is RRF?
Rank fusion: `score = Σ 1/(k + rank)` with k = 60. It ignores incompatible score scales.

### Q7. Bi-encoder vs cross-encoder?
Bi-encoder: independent embeddings, fast. Cross-encoder: reads the pair jointly, accurate but slow, so used on the top 20 only.

### Q8. Why HNSW?
Fast approximate nearest-neighbour search with good recall. IVFFlat needs clustering and probe tuning.

### Q9. What does the GIN index do?
It indexes `tsvector` lexemes for fast full-text search.

### Q10. Why 20 candidates and 5 final chunks?
20 gives the reranker room to correct the order; 5 keeps the prompt short and focused.

### Q11. How do you handle follow-up questions?
Rewrite them into standalone questions using the last four messages; guard against bad rewrites.

### Q12. What if the rewriter fails?
It never raises; it returns the original question.

### Q13. How do you chunk documents?
Page-aware text splitting with metadata (document id, organization id, chunk index, page number); repeated headers and footers are removed first.

### Q14. How do you deal with duplicate documents?
SHA-256 hash with a unique index per organization (HTTP 409).

---

## C. Evaluation

### Q15. How did you evaluate retrieval?
A 28-question JSONL dataset with text anchors and pages; Hit@1/3/5, MRR, page match, duplicate rate, latency.

### Q16. Why anchors instead of ids?
Duplicates made ids unreliable.

### Q17. Hit@K vs MRR?
Hit@K is binary within K; MRR rewards ranking the correct chunk higher.

### Q18. How did you evaluate hallucination?
Unanswerable and adversarial "trap" questions with repeated trials; the system must reply with the exact not-found sentence, with no false refusals on answerable questions.

### Q19. Can your metrics be gamed or noisy?
Yes: LLM variance and a small sample. I report sample sizes and prefer Hit@5 for noisy runs.

### Q20. What would you add to the evaluation?
More real documents, 100+ questions, RAGAS faithfulness and context precision, deterministic rewrite caching.

---

## D. Hallucination and citations

### Q21. How do you reduce hallucination?
Context-only prompt, exact refusal sentence, scope rule, citation validation, and tests on traps.

### Q22. How do citations work?
Chunks are numbered in the prompt, the model cites `[n]`, and the backend maps numbers to retrieval metadata (document, page, chunk, snippet).

### Q23. What does the validator catch and miss?
Catches invalid markers and numbers unsupported by the cited chunk. Misses semantic errors with correct numbers (the FY2026 example).

### Q24. Why is the not-found sentence exact?
It is detectable by code, so citations can be suppressed and the UI can behave correctly.

---

## E. LLM and streaming

### Q25. Why a provider fallback chain?
Reliability and free-tier quotas: Gemini, then Groq, then DeepSeek.

### Q26. How is fallback handled during streaming?
Switch only before the first token; afterwards end the stream with an error event.

### Q27. SSE vs WebSocket?
One-way streaming over plain HTTP is enough; WebSockets are for two-way traffic.

### Q28. What was the SSE newline bug?
A token containing a newline ended the event early. Fixed by emitting multiple `data:` lines.

### Q29. How do you save a streamed answer?
Collect tokens and store a single assistant message after streaming finishes.

---

## F. Caching and reliability

### Q30. What do you cache?
The final answer and citations, keyed by organization and a SHA-256 of the standalone question. Not history, documents or embeddings.

### Q31. Cache invalidation?
The cache is cleared after a successful document upload because answers may change.

### Q32. What happens if Redis is down?
Fail-open with a 2 second timeout and a 30 second circuit breaker.

### Q33. How do you handle provider quota errors?
Cooldown per provider using the provider's retry delay (cap 15 minutes).

---

## G. Security and multi-tenancy

### Q34. How is tenant isolation implemented?
`organization_id` on rows, filters in every query (including chunks), tenant-scoped cache keys, tests.

### Q35. Explain your RBAC.
Hierarchical roles: super admin, admin, manager, employee. Upload/delete need manager; user management needs admin.

### Q36. Explain your JWT design.
Short-lived access token, 7-day refresh token with a type claim, refresh endpoint, startup validation of the secret.

### Q37. How do you prevent a refresh token being used as an access token?
The dependency checks `type == "access"`.

### Q38. What security weaknesses remain?
Tokens in `localStorage`, no refresh-token revocation or rate limiting, free-tier demo.

### Q39. Why did signup return 500 before?
Its schema was weaker than the inner schemas; now it validates the same rules and returns 422.

---

## H. Database and ingestion

### Q40. Why Alembic?
Versioned, reversible schema changes; `create_all` does not alter existing tables.

### Q41. What did migration 002 add?
file hash, error message, per-organization unique hash index, chunk organization id, GIN and HNSW indexes.

### Q42. What happens when processing fails?
Status failed, short error message, partial chunks removed.

### Q43. How does the frontend know processing finished?
Polling the documents endpoint while any document is `processing`.

### Q44. Why background tasks for processing?
So uploads return immediately; the task opens its own database session.

---

## I. Performance, memory and deployment

### Q45. How did you reduce memory?
Lazy imports, no torch in the default image, int8 ONNX reranker baked into the image.

### Q46. What did you measure?
171.6 MiB idle, 108.6 MiB while reranking, 0.36 s per 20 chunks, Spearman 0.971 versus PyTorch.

### Q47. What is quantization?
Using 8-bit weights instead of 32-bit floats: smaller and faster with a small accuracy change.

### Q48. How is the app deployed?
Docker backend on Render, Neon Postgres with pgvector, Redis Cloud, React on Vercel, GitHub Actions for CI.

### Q49. How do you handle cold starts?
A keep-alive ping and a README note; a limitation of the free tier.

### Q50. What limits throughput on the free tier?
Voyage's 3 requests per minute, Gemini's 20 requests per day, and the 512 MB instance.

---

## J. Testing and CI

### Q51. How is the code tested?
211 backend tests (mocks, SQLite for database logic, fake clocks), frontend vitest tests, and benchmark scripts for retrieval and answers.

### Q52. Why did CI fail while local tests passed?
Import-time client creation without a key and missing local-only files. Fixed with lazy clients, dummy env vars and model caching.

### Q53. How did you verify the CI fix?
Ran the same steps in a fresh clone without `.env` and model files.

---

## K. Behavioural

### Q54. Tell me about a mistake you made.
I guessed that a chunk lacked a figure; chunk overlap proved me wrong when I read the data. I now verify with data before explaining.

### Q55. Tell me about a time a result was misleading.
A rerank benchmark looked bad because rate limiting made reranking silently fail open. I read the warnings, identified the cause, and moved to a local model.

### Q56. How do you prioritise?
Stability, measurement, quality, security, deployment.

### Q57. What would you do with more time?
Larger real evaluation set, RAGAS, object storage, observability, rate limiting, load testing.

### Q58. How did you use AI coding tools?
For implementation of scoped tasks, with branches, tests, benchmarks and manual review of sensitive diffs.