# Week 6 - Day 5: Interview Notes: Concepts Cheat-Sheet, System Design Answer, Limitations and Commands

## 1. Core concepts (one-line definitions)

- **RAG**: retrieve relevant document chunks and give them to an LLM so answers are grounded in those documents.
- **Embedding**: a dense vector for a text (1024 dimensions here); similar meaning gives nearby vectors.
- **Cosine similarity**: angle-based similarity between vectors.
- **pgvector**: PostgreSQL extension for vector storage and similarity search.
- **HNSW**: graph-based approximate nearest-neighbour index; strong recall and speed, slower build, more memory.
- **IVFFlat**: clustering-based index that needs training data and tuning (probes).
- **Full-text search**: `tsvector`/`tsquery` matching on lexemes; **GIN** is the inverted index.
- **Hybrid search**: vector search plus keyword search.
- **RRF**: reciprocal rank fusion, `Σ 1/(k + rank)`.
- **Bi-encoder / cross-encoder**: independent encoding (fast) versus joint pair scoring (accurate).
- **Reranking**: reorder retrieved candidates with a stronger model.
- **Query rewriting**: turning a follow-up into a standalone question.
- **Hit@K / MRR**: retrieval metrics defined earlier.
- **Hallucination**: fluent but unsupported output.
- **Abstention**: refusing to answer when the sources lack the answer.
- **Faithfulness**: whether the answer is supported by the retrieved context.
- **Quantization**: lower-precision weights (int8) for smaller, faster models.
- **ONNX Runtime**: engine that runs exported models without the training framework.
- **SSE**: one-way HTTP event stream (`event:` and `data:` lines, blank line ends an event).
- **JWT**: signed token carrying claims; here access (30 min) and refresh (7 days).
- **RBAC**: permissions by role; hierarchical means higher roles include lower ones.
- **Multi-tenancy**: several organizations share one deployment with strict data isolation.
- **Alembic**: SQLAlchemy migration tool.
- **Circuit breaker**: stop calling a failing dependency for a cooldown.
- **Fail-open**: continue without an optional component when it fails.
- **Liveness / readiness**: process alive versus ready to serve.
- **CORS**: browser rule about which origins may call an API.

---

## 2. "Design a RAG system" answer template

1. **Requirements**: documents per tenant, latency, accuracy, cost, privacy, scale.
2. **Ingestion**: upload → validate → dedupe → extract → clean → chunk → embed → store with metadata and tenant id; asynchronous with status.
3. **Retrieval**: hybrid search with tenant filter, rank fusion, reranking.
4. **Generation**: grounded prompt, numbered sources, refusal rule, streaming, provider fallback.
5. **Trust**: citation validation, abstention tests, evaluation set and metrics.
6. **Conversation**: history, query rewriting, cache keyed by the standalone question and tenant.
7. **Security**: authentication, RBAC, tenant isolation, secrets, rate limits, audit.
8. **Operations**: migrations, health checks, CI, observability, deployment, cost control.
9. **Trade-offs**: quality versus latency (reranker), cost versus quality (free tier), recall versus precision (candidate count).
10. **Next steps**: larger evaluation, RAGAS, object storage, queue, tracing.

---

## 3. Pitch versions

**30 seconds**: multi-tenant document Q&A with hybrid retrieval, reranking and citations; evaluation-driven; Hit@1 78.6% to 92.9% on my 28-question set; free-tier deployment.

**2 minutes**: add the pipeline (rewrite, hybrid, rerank, generate, validate), abstention results (33 of 33, zero false refusals) and security (RBAC, JWT, isolation).

**5 minutes**: add three stories: the 512 MB memory fix with ONNX, the evaluation-first mindset (noisy and misleading metrics), and the rewriter guard.

---

## 4. Limitations and next steps

Limitations:

- Small, partly synthetic evaluation set; Hit@K is a retrieval metric.
- Free-tier limits (3 embedding requests per minute, 20 Gemini requests per day, cold starts).
- Uploaded files are stored on an ephemeral disk on the host; chunks remain in the database.
- Tokens in `localStorage`; no refresh-token revocation or rate limiting.
- Streaming answers show raw citation markers until the frontend replaces them with chips (the non-streaming endpoint returns cleaned answers).
- Provider output is stochastic, so some metrics vary between runs.

Next steps:

1. 100+ question dataset with real documents; RAGAS faithfulness and context precision.
2. Cache rewrite outputs for deterministic comparisons.
3. Object storage for PDFs and a Redis-backed job queue for ingestion.
4. Metrics, tracing, token and cost tracking.
5. Rate limiting, audit logging, token revocation, httpOnly cookies.
6. Load testing with paid provider keys.

---

## 5. Commands cheat-sheet

```bash
# Backend tests
cd backend && pytest -x

# Retrieval benchmark
PYTHONPATH=. python eval/bench_retrieval.py --org-id 1 --dataset eval/bench_org1.jsonl --label run
PYTHONPATH=. python eval/bench_retrieval.py --org-id 1 --dataset eval/bench_org1.jsonl --label fused --no-rerank
PYTHONPATH=. python eval/bench_retrieval.py --org-id 1 --dataset eval/bench_followups.jsonl --label fu --rewrite

# Answer-level benchmark (abstention, citations)
PYTHONPATH=. python eval/bench_answers.py --org-id 1 --dataset eval/bench_traps.jsonl --repeat 3 --label traps

# Reranker backend
RERANKER_BACKEND=onnx   # onnx | local | voyage | none

# Migrations
alembic stamp 001_baseline   # once, for a database created before migrations
alembic upgrade head
alembic current

# Docker memory proof
docker build -t rag ./backend
docker run --memory=512m -p 8000:8000 --env-file backend/.env rag
docker stats --no-stream

# Health
curl -s https://<backend>/health/ready

# Safety checks before pushing
git ls-files | grep -E "(^|/)\.env|\.zip$|uploads/|\.venv/|\.onnx$|node_modules/"
git grep -n -I -E "AIza[0-9A-Za-z_-]{30,}|gsk_[0-9A-Za-z]{30,}|sk-[0-9a-f]{30,}|pa-[0-9A-Za-z_-]{30,}"
```

---

## 6. Test-count timeline

105 (stabilized backend) → 112 → 117 → 123 → 135 (citations) → 143 → 153 → 157 → 163 (ingestion) → 175 (security) → 184 (production) → 188 → 198 → 211 (free-tier mode and CI).

---

## 7. Ten lessons to remember

1. Measure first, optimise second.
2. Make ground truth robust (text anchors).
3. A tiny corpus hides improvements; add distractors.
4. Repeat noisy metrics and state the sample size.
5. Validate LLM output; never trust it blindly.
6. Fail-open resilience can hide measurement problems; read warnings.
7. Treat third-party limits as design constraints.
8. The memory budget shapes the architecture.
9. Verify agent reports and your own guesses against data.
10. Check secrets and repository hygiene before every push.