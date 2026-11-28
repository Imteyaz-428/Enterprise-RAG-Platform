# 🚀 Enterprise RAG Platform

> A multi-tenant document question-answering and Retrieval-Augmented Generation (RAG) platform enabling organizations to securely index proprietary PDFs, retrieve contextual evidence through hybrid search (`pgvector` + full-text) and cross-encoder reranking, and stream verified answers with deterministic page-level citations.

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17%20pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-int8%20CPU-005CED?logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![Docker](https://img.shields.io/badge/Docker-Non--Root%20Slim-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/Imteyaz-428/Enterprise-RAG-Platform/actions)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

- **Repository:** [https://github.com/Imteyaz-428/Enterprise-RAG-Platform](https://github.com/Imteyaz-428/Enterprise-RAG-Platform)
- **Live Demo:** [https://enterprise-rag-platform-three.vercel.app](https://enterprise-rag-platform-three.vercel.app) *(Free-tier hosting: the first request after 15 minutes of inactivity can take 30–60 seconds due to cold start)*
- **Stack:** FastAPI, PostgreSQL 17 + `pgvector`, Redis 7, React 19 + Vite + Tailwind CSS, ONNX Runtime, Docker, GitHub Actions
- **Deployment (All Free Tier):** Render (Backend), Neon (PostgreSQL), Redis Cloud (Cache), Vercel (Frontend)

> This document serves as both the complete **project README** and an **engineering revision guide**: every component is documented with where it lives, how it works, why it was built that way, how it was tested, and key trade-offs. All benchmark figures come directly from `backend/eval/results/summary.csv`.

---

## 📑 Table of Contents
1. [What It Is & Headline Results](#1-what-it-is--headline-results)
2. [Feature Overview](#2-feature-overview)
3. [Architecture & End-to-End Flows](#3-architecture--end-to-end-flows)
4. [Tech Stack & Design Decisions](#4-tech-stack--design-decisions)
5. [Repository Layout](#5-repository-layout)
6. [Data Model & Migrations](#6-data-model--migrations)
7. [Feature Deep Dives](#7-feature-deep-dives)
8. [Setup & Installation](#8-setup--installation)
9. [Environment Variables & Free-Tier Optimization](#9-environment-variables--free-tier-optimization)
10. [API Reference](#10-api-reference)
11. [Roles & Permissions (RBAC)](#11-roles--permissions-rbac)
12. [Testing & CI](#12-testing--ci)
13. [Evaluation Framework & Benchmark Results](#13-evaluation-framework--benchmark-results)
14. [Project Evolution & Engineering Lessons](#14-project-evolution--engineering-lessons)
15. [Security Model & Known Limitations](#15-security-model--known-limitations)
16. [Interview Preparation & Glossary](#16-interview-preparation--glossary)

---

## 1. What It Is & Headline Results

The **Enterprise RAG Platform** is a multi-tenant AI knowledge management system engineered for strict organizational data isolation, high retrieval precision, low memory footprint, and grounded AI generation.

Organizations upload proprietary PDFs (manuals, contracts, reports, technical specifications), which are validated, deduplicated, parsed per page, cleaned of repeated headers/footers, chunked, embedded, and indexed. When team members ask questions:
1. **Query Rewriting:** Multi-turn follow-up questions are rewritten into standalone queries using conversation history (protected by a content-word overlap guard).
2. **Tenant-Scoped Caching:** Redis checks `cache:{organization_id}:{sha256(standalone_question)}` with a fail-open circuit breaker.
3. **Hybrid Retrieval:** Dense semantic embeddings (`pgvector` HNSW) and sparse keyword matching (`tsvector` GIN) each retrieve 20 candidates, fused via **Reciprocal Rank Fusion (RRF, $k=60$)** into 20 candidates.
4. **Cross-Encoder Reranking:** An **int8 quantized ONNX** cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, ~22 MB) scores all 20 `(query, chunk)` pairs on CPU in ~0.36 s and selects the top 5 passages.
5. **Resilient Generation & Validation:** Answers stream via Server-Sent Events (SSE) through a fallback chain (**Gemini 2.5 Flash → Groq Llama-3.3 → DeepSeek Chat**), enforced by strict grounding rules, deterministic page-level citations (`[1]`, `[2]`), and an exact refusal sentence when evidence is missing.

### Headline Benchmark Results

All metrics are measured on the project's own evaluation sets (`28` retrieval questions, `8` multi-turn follow-ups, `11` abstention questions + `8` adversarial traps). Because the evaluation sets are small and partly synthetic, interpret these as performance *on the project evaluation set*.

| Area | Result | Evidence / Source |
|---|---|---|
| **Retrieval Ranking (Hit@1)** | **78.6% → 92.9%** with reranker (same 28 questions, same corpus) | `fused-only` vs `rerank-onnx` in `summary.csv` |
| **Retrieval Ranking (MRR)** | **0.878 → 0.958** | Same benchmark comparison |
| **Follow-up Questions (Hit@5)** | **87.5% → 100%** with query rewriting (`8` multi-turn questions) | Follow-up benchmark (`bench_followups.jsonl`) |
| **Abstention & Hallucination** | **33/33** correct "not found" trials, **0/28** false refusals | Answer benchmark (`bench_answers.py`) |
| **Container Memory** | **171.6 MiB** idle / **108.6 MiB** active rerank in a **512 MiB** container | `docker stats` (PyTorch build exceeded 512 MiB) |
| **Reranker Compression** | PyTorch → **22 MB int8 ONNX** (Spearman **0.971**, Top-5 overlap **100%**) | `scripts/eval_onnx_correctness.py` |
| **Rerank Latency** | **0.36 s** for 20 chunks on CPU | Measured inside 512 MiB container |
| **Automated Test Suite** | **211 backend tests** (`pytest`) + frontend unit tests (`vitest`) | GitHub Actions CI |

---

## 2. Feature Overview

| # | Feature | One-Line Summary |
|---|---|---|
| 1 | **Authentication** | JWT access (30 min) and refresh (7 days) tokens with `type` claim validation and `bcrypt` password hashing |
| 2 | **Hierarchical RBAC** | `super_admin` > `admin` > `manager` > `employee` enforced at the API dependency layer |
| 3 | **Multi-Tenancy** | Every database row, vector/FTS query, file hash, and Redis cache key is strictly scoped by `organization_id` |
| 4 | **Document Ingestion** | PDF magic-byte check, SHA-256 deduplication, background processing, header/footer stripping, token-bounded embedding batches |
| 5 | **Hybrid Retrieval** | `pgvector` cosine search (HNSW) + PostgreSQL full-text search (GIN), fused with Reciprocal Rank Fusion ($k=60$) |
| 6 | **Cross-Encoder Reranking** | `cross-encoder/ms-marco-MiniLM-L-6-v2` (int8 ONNX by default) re-scoring top 20 candidates down to top 5 |
| 7 | **Query Rewriting** | Rewrites follow-up questions into standalone queries using last 4 messages, protected by an overlap guard |
| 8 | **Resilient AI Mesh** | Grounded numbered-source prompts with **Gemini 2.5 Flash → Groq → DeepSeek** fallback, retries, and 429 cooldowns |
| 9 | **SSE Streaming** | Server-Sent Events with a strict event contract (`metadata` → `token*` → `done` or `error` → `done`) and multi-line newline framing |
| 10 | **Validated Citations** | Bracketed markers mapped to document title, page number, chunk index, and snippet; verified for numeric support |
| 11 | **Hallucination Control** | Exact refusal string (`I could not find this in the provided documents.`), scope rule, and adversarial trap testing |
| 12 | **Fail-Open Redis Cache** | Tenant-scoped response cache with 2 s timeouts, 30 s circuit breaker, and automatic invalidation on upload/delete |
| 13 | **Central Error Handling** | Unified handlers mapping DB/AI outages to `503`, duplicates to `409`, validation to `422`, and sanitized `500`s with request IDs |
| 14 | **Observability & Probes** | `/health` liveness, `/health/ready` readiness, `/chat/providers/health`, request IDs, and fail-open warning logs |
| 15 | **Evaluation Suite** | Text-anchor retrieval and answer benchmarks, disk embedding cache, and corpus inspector |
| 16 | **Database Migrations** | Versioned, reversible Alembic migrations (`001_baseline` → `002_ingestion_hardening` → `003_db_integrity`) |
| 17 | **React Frontend** | Streaming chat UI with custom `fetch` SSE parser, interactive citation chips, single-flight token refresh, and role-gated views |
| 18 | **DevOps & Free-Tier Ops** | Non-root `python:3.13-slim` Docker image, Docker Compose stacks, GitHub Actions CI, and keep-alive automation |

---

## 3. Architecture & End-to-End Flows

### 3.1 System Context

```mermaid
flowchart TD
    Client["Client Web App (React 19 + Vite on Vercel)"]

    subgraph Platform ["Enterprise RAG Platform Backend (FastAPI on Render)"]
        Router["API Gateway / Routers<br>(Auth, Org, Users, Docs, Chat, Health)"]
        RBAC["RBAC & Security Guard<br>(JWT, Passlib, Org Isolation)"]
        ChatEngine["Chat & Streaming Engine"]
        Rewriter["Conversational Query Rewriter<br>(5s Budget + Overlap Guard)"]
        RetrievalSvc["Hybrid Retrieval Service<br>(RRF Dense + Sparse, k=60)"]
        RerankerSvc["Cross-Encoder Reranker<br>(int8 ONNX ms-marco-MiniLM-L-6-v2)"]
        Validator["Citation Validator & Cleaner"]
        AISvc["AIService Fallback Engine<br>(Rate-Limit Cooldown + Tenacity)"]
    end

    subgraph DataTier ["Data & Caching Layer"]
        Postgres[("PostgreSQL 17 + pgvector (Neon)<br>(Tenant DB, HNSW Vector, GIN Full-Text)")]
        RedisCache[("Redis 7 (Redis Cloud)<br>(Response Cache & Circuit Breaker)")]
    end

    subgraph ExternalAI ["External AI Provider APIs"]
        Voyage["Voyage AI<br>(voyage-3-large Dense Embeddings)"]
        Gemini["Google Gemini 2.5 Flash<br>(Primary LLM)"]
        Groq["Groq Llama-3.3-70B<br>(Fallback LLM 1)"]
        DeepSeek["DeepSeek Chat<br>(Fallback LLM 2)"]
    end

    Client -->|HTTPS REST + SSE| Router
    Router --> RBAC
    RBAC --> ChatEngine
    ChatEngine --> Rewriter
    ChatEngine -->|Cache Check / Store| RedisCache
    ChatEngine --> RetrievalSvc
    RetrievalSvc -->|Embed Query| Voyage
    RetrievalSvc -->|Dense & Sparse Search| Postgres
    RetrievalSvc --> RerankerSvc
    ChatEngine --> AISvc
    AISvc -->|Primary| Gemini
    AISvc -.->|On 429 / Error| Groq
    AISvc -.->|On 429 / Error| DeepSeek
    ChatEngine --> Validator
    ChatEngine -->|Persist History| Postgres
```

### 3.2 Chat & Streaming Request Pipeline

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI (ChatService)
    participant RW as Query Rewriter (LLM)
    participant RC as Redis
    participant E as Voyage Embeddings
    participant DB as Postgres (pgvector + FTS)
    participant RR as Reranker (ONNX)
    participant L as LLM (Fallback Chain)

    C->>A: POST /chat/stream (question, session_id)
    A->>A: Authenticate JWT, resolve org-scoped session, load last 4 messages
    A->>RW: Rewrite follow-up (only if history exists, 5s timeout)
    RW-->>A: Standalone question (validated by overlap guard)
    A->>A: Persist user's original question
    A->>RC: Lookup cache:{org_id}:{sha256(standalone)}
    alt Cache Hit
        A-->>C: event: metadata, cached tokens..., event: done
    else Cache Miss
        A->>E: Embed standalone question (1024 dims)
        A->>DB: Vector top 20 + Keyword top 20 (org-scoped, status='completed')
        A->>A: RRF fusion -> 20 candidates
        A->>RR: Rerank 20 candidates -> top 5 chunks
        A->>L: Prompt with numbered sources [1..5] + conversation history
        L-->>A: Token stream
        A-->>C: event: metadata (citations), event: token..., event: done
        A->>A: Validate citations, save assistant message, write Redis cache
    end
```

**Failure Behaviour by Pipeline Step:**

| Step | Failure Condition | System Behaviour |
|---|---|---|
| 1. Auth | Missing, expired, or `refresh` token passed | Returns `401 Unauthorized` |
| 4. Rewriter | LLM timeout/error or off-topic rewrite | Logs warning and falls back to user's original question |
| 6. Cache | Redis timeout or connection error | Treated as cache miss; trips 30 s circuit breaker |
| 7–8. Embed / DB | Voyage rate limit (after 1 retry) or DB outage | Returns `503` (or `event: error` + `event: done` in stream) |
| 9. Reranker | ONNX/Voyage error | Fails open to RRF fused order and logs warning |
| 12. Generation | All LLM providers exhausted or cooling down | Returns `503 AI_SERVICE_UNAVAILABLE` (or `event: error` in stream) |
| 13. Citations | Model emits no valid `[n]` markers | Returns all retrieved citations (legacy fallback) |

### 3.3 Document Ingestion Pipeline

```mermaid
flowchart TD
    UP["POST /documents/upload"] --> M{"PDF magic bytes (%PDF-)?"}
    M -- No --> E400["400 Bad Request"]
    M -- Yes --> H["Compute SHA-256 Hash"]
    H --> D{"Same hash in same org?"}
    D -- Yes --> E409["409 Conflict (Duplicate)"]
    D -- No --> S["Save file + DB row (status=processing)"]
    S --> RESP["Return 200 immediately"]
    S --> BG["Background Task"]
    BG --> X["Extract text per page (PyMuPDF)"]
    X --> HF["Strip repeated headers/footers (>=50% pages, >=3 pages)"]
    HF --> CH["Chunk text with page_number & chunk_index metadata"]
    CH --> EM["Embed in token-bounded batches (retry 429 up to 5x)"]
    EM --> INS["Single transactional insert (org_id, doc_id, page, index, vector)"]
    INS --> OK["status=completed, invalidate org Redis cache"]
    BG -. Any Exception .-> FAIL["status=failed + sanitized error_message, delete partial chunks"]
```

### 3.4 SSE Streaming & Authentication Flows

- **SSE Event Contract:**
  ```text
  Success: event: metadata  -->  event: token (repeated)  -->  event: done
  Failure: event: metadata  -->  event: error             -->  event: done  (no tokens after error)
  ```
  Tokens containing newlines are split into multiple `data:` lines per the SSE specification and rejoined with `\n` on the client (`utils/sse.js`).
- **Silent JWT Refresh Flow:**
  ```text
  POST /auth/login -> access_token (30 min) + refresh_token (7 days)
  API call returns 401 -> Axios interceptor sends ONE POST /auth/refresh (concurrent requests queue)
    -> Refresh succeeds: updates token & retries failed request once
    -> Refresh fails: clears storage & redirects to /login
  ```

---

## 4. Tech Stack & Design Decisions

| Component | Choice | Why It Was Chosen | Trade-Off Accepted |
|---|---|---|---|
| **API Framework** | FastAPI + Pydantic | Strong request/response validation, automatic OpenAPI docs (`/docs`), native async `StreamingResponse` | Requires discipline around sync SQLAlchemy sessions in async endpoints |
| **Database & Vector Store** | PostgreSQL 17 + `pgvector` | Single transactional store for relational data, full-text search, and vector embeddings; enforces multi-tenant joins atomically | Less specialized than a standalone vector DB at billion-vector scale |
| **Vector Index** | HNSW (`vector_cosine_ops`) | High recall and low query latency without requiring clustering training data (unlike IVFFlat) | Higher memory usage during index build |
| **Keyword Search** | `tsvector` + GIN Index | Exact keyword, acronym, and numeric matching inside PostgreSQL | Language-specific stemming (`english`) |
| **Rank Fusion** | Reciprocal Rank Fusion ($k = 60$) | Combines incompatible cosine similarity and `ts_rank` scales using rank positions only—no weight tuning needed | Ignores raw score confidence margins |
| **Embeddings** | Voyage `voyage-3-large` (1024 dims) | High retrieval accuracy on technical and enterprise text | Strict free-tier limits (3 RPM / 10k TPM without billing) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` (int8 ONNX) | Joint `(query, passage)` attention dramatically boosts Hit@1; int8 ONNX runs in 22 MB RAM on CPU without PyTorch | Extra Docker build step to download model artifacts |
| **LLM Mesh** | Gemini 2.5 Flash → Groq → DeepSeek | High speed, generous context, and automatic failover across free-tier quota limits | Slight stylistic differences across fallback models |
| **Cache** | Redis 7 | Sub-millisecond repeat query latency; circuit breaker ensures fail-open resilience | Stale cache until cleared on document upload/delete |
| **PDF Extraction** | PyMuPDF (`fitz`) | Fast, accurate page-boundary preservation for page-level citations | Scanned image-only PDFs require OCR (not yet integrated) |
| **Frontend** | React 19, Vite, Tailwind CSS, Axios | Fast build loop, custom `fetch` stream reader (supports `Authorization` headers unlike `EventSource`) | Tokens stored in `localStorage` rather than `httpOnly` cookies |

---

## 5. Repository Layout

```text
.
├── backend/
│   ├── app.py                       # FastAPI app, CORS, middleware, health probes, lifespan
│   ├── core/
│   │   ├── security.py              # bcrypt hashing, JWT creation/verification, startup validation
│   │   ├── dependencies.py          # get_current_user, hierarchical require_role()
│   │   ├── enums.py                 # UserRole and numeric permission ranks
│   │   └── errors.py                # Central exception handlers (503, 409, 422, sanitized 500)
│   ├── router/
│   │   ├── auth.py                  # /auth/signup, /login, /refresh, /me
│   │   ├── user.py                  # /users CRUD and password change
│   │   ├── organization.py          # /organizations management
│   │   ├── document.py              # /documents upload, list, get, delete
│   │   └── chat.py                  # /chat, /chat/stream, sessions, provider health
│   ├── services/
│   │   ├── chat/
│   │   │   ├── chat_service.py      # Pipeline orchestration: chat(), chat_stream(), _prepare_chat()
│   │   │   ├── query_rewriter.py    # Conversational query rewriting + content-word overlap guard
│   │   │   ├── retrieval_service.py # Hybrid search + reranking coordination
│   │   │   ├── reranking_service.py # Backends: onnx | local (torch) | voyage | none
│   │   │   ├── prompt_service.py    # Grounded prompt builder with numbered sources & refusal rule
│   │   │   └── citation_validator.py# Marker extraction, numeric support check, not-found normalization
│   │   ├── ai/
│   │   │   ├── ai_services.py       # Provider fallback chain, tenacity retries, 429 cooldowns
│   │   │   ├── config.py            # Constants (SEARCH_TOP_K=5, RERANK_CANDIDATES=20, timeouts)
│   │   │   └── providers/           # Gemini, Groq, and DeepSeek adapters
│   │   ├── cache/redis_service.py   # Fail-open Redis client with 30s circuit breaker
│   │   └── background/document_processor.py # Async PDF extraction, header stripping, batch embedding
│   ├── crud/                        # SQLAlchemy data access (document_chunk.py holds RRF hybrid SQL)
│   ├── models/                      # SQLAlchemy ORM models + central relationship registry
│   ├── schemas/                     # Pydantic v2 request/response contracts
│   ├── utils/                       # chunker, lazy Voyage embedding client, retry, secret-redacting logger
│   ├── migrations/versions/         # 001_baseline, 002_ingestion_hardening, 003_db_integrity
│   ├── eval/                        # Benchmarks (bench_retrieval.py, bench_answers.py), datasets, summary.csv
│   ├── scripts/                     # download_onnx_model.py, eval_onnx_correctness.py, set_role.py
│   ├── test_*.py                    # 211 automated backend tests
│   ├── Dockerfile                   # Slim non-root Python 3.13 image with pre-baked int8 ONNX model
│   ├── entrypoint.sh                # Runs `alembic upgrade head` before starting `uvicorn`
│   └── requirements*.txt            # Production, dev, and optional local-PyTorch dependencies
├── frontend/                        # React 19 + Vite app (SSE parser, citation chips, role UI) + vitest
├── docs/                            # ARCHITECTURE.md and FRONTEND_AUDIT.md
├── docker-compose.yml               # Production-like stack (pgvector Postgres, Redis, Backend)
├── docker-compose.dev.yml           # Local development override with hot-reload and source mount
└── .github/workflows/ci.yml         # CI pipeline: pytest + ONNX model cache + Docker image build
```

---

## 6. Data Model & Migrations

### Entity-Relationship Diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ DOCUMENTS : owns
    ORGANIZATIONS ||--o{ DOCUMENT_CHUNKS : scopes
    ORGANIZATIONS ||--o{ CHAT_SESSIONS : scopes
    USERS ||--o{ CHAT_SESSIONS : starts
    USERS ||--o{ DOCUMENTS : uploads
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : split_into
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains

    ORGANIZATIONS {
        int id
        string name
        string slug
    }
    USERS {
        int id
        string name
        string email
        string hashed_password
        string role
        int organization_id
    }
    DOCUMENTS {
        int id
        string title
        string original_filename
        int file_size
        string status
        string file_hash
        string error_message
        int organization_id
        int uploaded_by
    }
    DOCUMENT_CHUNKS {
        int id
        int document_id
        int organization_id
        int chunk_index
        int page_number
        string chunk_text
        vector embedding
    }
    CHAT_SESSIONS {
        int id
        int organization_id
        int user_id
    }
    CHAT_MESSAGES {
        int id
        int session_id
        string role
        string content
    }
```

### Key Constraints, Indexes & Alembic Revisions

- **Deduplication Index:** Partial unique index on `documents (organization_id, file_hash) WHERE file_hash IS NOT NULL` prevents duplicate uploads within the same tenant while allowing different organizations to upload identical documents.
- **Tenant Defense-in-Depth:** `document_chunks.organization_id` is `NOT NULL`, indexed, and foreign-keyed to `organizations`, allowing hybrid retrieval queries to filter directly on chunks without expensive joins.
- **Search Indexes:** `GIN` index on `to_tsvector('english', chunk_text)` for sparse keyword search; `HNSW` index (`vector_cosine_ops`) on `embedding` (`vector(1024)`) for dense similarity search.
- **Document Lifecycle States:** `processing` → `completed` | `failed`. Retrieval queries strictly filter `documents.status = 'completed'`.
- **Alembic Migration History:**
  - `001_baseline`: Core tables and `CREATE EXTENSION IF NOT EXISTS vector`.
  - `002_ingestion_hardening`: Adds `file_hash`, `error_message`, partial unique index, backfilled `document_chunks.organization_id`, `GIN`, and `HNSW` indexes.
  - `003_db_integrity`: Enforces `ON DELETE CASCADE` for tenant/session children and `ON DELETE SET NULL` for `documents.uploaded_by`.

```bash
cd backend
alembic upgrade head                                        # Apply all migrations
alembic revision --autogenerate -m "Describe schema change" # Generate new migration
alembic downgrade -1                                        # Roll back one revision
```

---

## 7. Feature Deep Dives

### 7.1 Authentication & Hierarchical RBAC
- **Where:** `core/security.py`, `core/dependencies.py`, `core/enums.py`, `router/auth.py`
- **How It Works:** Passwords are salted and hashed with `bcrypt`. Login issues a 30-minute access token (`type="access"`) and a 7-day refresh token (`type="refresh"`). `get_current_user` rejects refresh tokens and malformed `sub` claims with `401`. At startup, `app.py` validates that `SECRET_KEY` is at least 32 characters and `ALGORITHM` is valid—failing fast rather than booting insecurely.
- **Hierarchical RBAC:** Roles map to integer ranks (`super_admin` > `admin` > `manager` > `employee`), so higher roles automatically satisfy lower-role dependencies via a single rank check.

### 7.2 Multi-Tenancy
- **Where:** `crud/`, `services/chat/`, `services/cache/redis_service.py`
- **How It Works:** Every query filters by `current_user.organization_id`. Redis keys are prefixed with `cache:{organization_id}:...`. Verified by 24 dedicated tenant- and user-isolation tests (`test_organization_isolation.py`, `test_user_isolation.py`).

### 7.3 Document Ingestion & Header/Footer Cleaning
- **Where:** `router/document.py`, `services/background/document_processor.py`, `utils/chunker.py`
- **How It Works:** Validates `%PDF-` magic bytes, hashes the file with SHA-256, rejects same-org duplicates with `409`, saves the file, and returns `200` immediately with `status="processing"`. A background task extracts text page-by-page via PyMuPDF, strips normalized lines appearing at the top or bottom of $\ge 50\%$ of pages (on documents with $\ge 3$ pages), splits text into overlapping chunks with `page_number` and `chunk_index`, embeds chunks in token-bounded batches (`EMBED_BATCH_TOKENS=6000`), and inserts everything in one transaction. Any error rolls back partial chunks and stores a sanitized `error_message`.

### 7.4 Hybrid Retrieval & Reciprocal Rank Fusion
- **Where:** `services/chat/retrieval_service.py`, `crud/document_chunk.py`
- **How It Works:** Executes dense cosine similarity search (`pgvector` HNSW, top 20) and sparse full-text search (`to_tsvector('english', chunk_text)`, top 20) scoped to the organization and completed documents. Candidates are merged via Reciprocal Rank Fusion:
  $$\text{RRF}(d) = \sum_{L \in \{\text{vector}, \text{keyword}\}} \frac{1}{60 + \text{rank}_L(d)}$$
  The top `RERANK_CANDIDATES` (`20`) fused passages are forwarded to the reranker.

### 7.5 Local int8 ONNX Cross-Encoder Reranking
- **Where:** `services/chat/reranking_service.py`, `scripts/download_onnx_model.py`
- **How It Works:** Supports `onnx` (production Docker default), `local` (PyTorch for dev), `voyage` (remote API), and `none` (passthrough). In `onnx` mode, `cross-encoder/ms-marco-MiniLM-L-6-v2` quantized to int8 (~22–23.2 MB) is baked into `/app/models/reranker/` at Docker build time and executed with `onnxruntime` CPU (`intra_op_num_threads=1`) and Rust `tokenizers` (max length 512, batches of $\le 20$). Keeps `torch` and `transformers` completely out of the production container. On any error, it fails open to the RRF order.

### 7.6 Conversational Query Rewriting with Overlap Guard
- **Where:** `services/chat/query_rewriter.py`
- **How It Works:** When conversation history exists, the last 4 messages (truncated to 500 chars each) are passed to an LLM with a 5-second timeout to produce a standalone question under 40 words. A **content-word overlap guard** checks that at least 50% of non-stopword terms from the original question (using 5-character prefix matching for inflections) appear in the rewrite; if an anomalous off-topic rewrite occurs, the guard discards it and uses the original question. The standalone question drives retrieval and the Redis cache key, while the user's original phrasing is preserved in chat history and the final prompt.

### 7.7 Grounded Generation, Fallback Mesh & Citation Validation
- **Where:** `services/chat/prompt_service.py`, `services/chat/citation_validator.py`, `services/ai/ai_services.py`
- **Provider Mesh:** Calls **Gemini 2.5 Flash → Groq → DeepSeek** with 30-second timeouts, `tenacity` exponential backoff on transient errors (`429`, `503`, timeouts), and thread-safe per-provider cooldowns (default 60 s, capped at 15 min) upon quota exhaustion. During SSE streaming, provider switching is permitted *only before the first token is emitted* so responses never mix outputs from two models.
- **Citation Validation:** Extracts `[n]` markers, drops out-of-range markers, filters the returned citation list to only cited sources in order of appearance, and verifies that numeric values in each sentence exist in the cited chunk text (e.g., `1,510` matches `1510`, `41%` matches `41`). If evidence is absent, the model outputs the exact refusal sentence `I could not find this in the provided documents.`, which code detects to strip all citations.

### 7.8 Fail-Open Redis Cache & Frontend Experience
- **Cache (`services/cache/redis_service.py`):** Keys follow `cache:{organization_id}:{sha256(standalone_question)}` (TTL `3600` s). Uses 2-second socket timeouts and a 30-second circuit breaker so Redis outages degrade gracefully to cache misses. Cleared automatically whenever a document finishes processing or is deleted.
- **Frontend (`frontend/src`):** Built with React 19, Vite, and Tailwind CSS. Features a custom `fetch` SSE parser (`utils/sse.js`), single-flight Axios refresh interceptor, role-gated navigation (`hasRole`), clickable `[n]` citation chips with page/snippet popovers, document polling while `processing`, and an error boundary.

---

## 8. Setup & Installation

### Prerequisites
- **Docker & Docker Compose** *(recommended)*, or:
- **Python 3.13+**, **Node.js 18+**, **PostgreSQL 17** (with `pgvector`), and **Redis 7+**

### Option A: Running with Docker (Recommended)

#### 1. Production-Like Stack
Starts PostgreSQL (`pgvector`), Redis, and the non-root FastAPI backend with named volumes (`pgdata`, `uploads`) and automatic Alembic migrations on boot:

```bash
# 1. Configure environment variables
cp backend/.env.example .env
# Edit .env and set SECRET_KEY (>=32 chars), VOYAGE_API_KEY, and GEMINI_API_KEY

# 2. Build and start containers
docker compose up -d --build

# 3. Verify readiness (database + redis)
curl -s http://localhost:8000/health/ready

# 4. Tail backend logs
docker compose logs -f backend
```

#### 2. Development Stack (Hot-Reload & Source Mount)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

#### 3. Verify 512 MiB Container Memory Footprint
```bash
docker build -t enterprise-rag ./backend
docker run -d --memory=512m -p 8000:8000 --env-file backend/.env enterprise-rag
docker stats --no-stream
```

### Option B: Running Without Docker (Bare Metal)

#### 1. Backend
```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
# Optional: only required if using RERANKER_BACKEND=local (PyTorch)
# pip install -r requirements-local-rerank.txt

cp .env.example .env
# Populate DATABASE_URL, REDIS_URL, SECRET_KEY, VOYAGE_API_KEY, GEMINI_API_KEY

# Download the int8 ONNX reranker (~22 MB)
python scripts/download_onnx_model.py

# Run database migrations and start server
alembic upgrade head
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

---

## 9. Environment Variables & Free-Tier Optimization

> **Security Note:** Never commit `.env` files or real API keys. Startup will fail fast if `SECRET_KEY` is missing or shorter than 32 characters.

| Variable | Description | Default | Required |
|---|---|---|:---:|
| `DATABASE_URL` | PostgreSQL connection URI (`postgresql://user:pass@host:port/db`) | — | **Yes** |
| `SECRET_KEY` | Cryptographic JWT signing key (minimum 32 characters) | — | **Yes** |
| `ALGORITHM` | JWT signing algorithm | `HS256` | Optional |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime in minutes | `30` | Optional |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime in days | `7` | Optional |
| `VOYAGE_API_KEY` | Voyage AI key for `voyage-3-large` (1024-d) embeddings | — | **Yes** |
| `VOYAGE_MIN_INTERVAL_SECONDS` | Process-wide minimum seconds between Voyage API calls (`21` for 3 RPM free tier) | `0` | Optional |
| `EMBED_BATCH_TOKENS` | Max estimated tokens (`len(text)/3`) per ingestion embedding batch | `6000` | Optional |
| `RERANKER_BACKEND` | Reranker engine: `onnx` (Docker default), `local` (PyTorch), `voyage`, or `none` | `onnx` / `local` | Optional |
| `VOYAGE_RERANK_MODEL` | Voyage rerank model when `RERANKER_BACKEND=voyage` | `rerank-2` | Optional |
| `ONNX_RERANKER_MODEL_PATH` | Path to int8 ONNX model file | `models/reranker/model.onnx` | Optional |
| `ONNX_RERANKER_TOKENIZER_PATH` | Path to HuggingFace `tokenizer.json` | `models/reranker/tokenizer.json` | Optional |
| `GEMINI_API_KEY` | Primary LLM key (Google Gemini 2.5 Flash) | — | **Yes** |
| `GOOGLE_API_KEY` | Alternative fallback environment variable for Gemini | — | Optional |
| `GROQ_API_KEY` | First fallback LLM key (Groq Llama-3.3-70B-versatile) | — | Optional |
| `DEEPSEEK_API_KEY` | Second fallback LLM key (DeepSeek Chat) | — | Optional |
| `REDIS_URL` | Redis connection URI (`redis://...` or `rediss://...`) | — | Optional |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD` | Individual Redis connection parameters (used if `REDIS_URL` is unset) | `localhost:6379/0` | Optional |
| `REDIS_EXPIRE` | Cache TTL in seconds (**plain integer only**, e.g. `3600`) | `3600` | Optional |
| `REDIS_CONNECT_TIMEOUT` / `REDIS_SOCKET_TIMEOUT` | Redis socket timeouts in seconds | `2.0` | Optional |
| `REDIS_CIRCUIT_COOLDOWN` | Circuit-breaker cooldown in seconds after Redis error | `30.0` | Optional |
| `PORT` | Backend server port | `8000` | Optional |
| `VITE_API_URL` | Frontend environment variable pointing to backend base URL | `http://localhost:8000` | Frontend |

### Free-Tier Engineering (Zero Billing Configuration)

Running on free tiers introduces strict constraints: **512 MiB RAM** on Render, **3 RPM / 10,000 TPM** on Voyage AI without a payment method, and **~20 RPD** on Gemini free tier. To operate reliably at $0 cost:
1. **int8 ONNX Reranker (`RERANKER_BACKEND=onnx`):** Eliminates PyTorch (`>512 MiB` OOM) and consumes **0 Voyage tokens/requests** while keeping container memory at **171.6 MiB idle** (108.6 MiB during active rerank).
2. **Paced & Token-Bounded Embeddings:** Set `VOYAGE_MIN_INTERVAL_SECONDS=21` and `EMBED_BATCH_TOKENS=6000` so multi-page PDFs embed cleanly within 3 RPM and 10,000 TPM with up to 5 exponential-backoff retries on `429`.
3. **Provider Fallback & Cooldowns:** Automatically shifts traffic from Gemini to Groq and DeepSeek on quota exhaustion.

---

## 10. API Reference

Interactive Swagger/OpenAPI documentation is served at `/docs`.

| Domain | Method | Endpoint | Min Role | Description |
|---|---:|---|:---:|---|
| **Health** | `GET` | `/health` | Public | Liveness probe (always returns `200`) |
| **Health** | `GET` | `/health/ready` | Public | Readiness probe (`SELECT 1` on DB + Redis ping; `503` if DB down) |
| **Auth** | `POST` | `/auth/signup` | Public | Register new organization + initial `admin` user (`slug` `^[a-z0-9-]+$`) |
| **Auth** | `POST` | `/auth/login` | Public | OAuth2 form (`username`, `password`) → `access_token` + `refresh_token` |
| **Auth** | `POST` | `/auth/refresh` | Refresh | Exchange valid refresh token for a new access token |
| **Auth** | `GET` | `/auth/me` | Employee | Get current user profile, role, and organization |
| **Organizations** | `POST` | `/organizations/` | Super Admin | Create an organization |
| **Organizations** | `GET` | `/organizations/`, `/organizations/{id}` | Admin | List organizations (super admin) or view own organization |
| **Organizations** | `PUT`, `DELETE` | `/organizations/{id}` | Admin | Update or delete organization |
| **Users** | `POST` | `/users/` | Admin | Create user within organization (`role` lowercase) |
| **Users** | `GET` | `/users/` | Admin | List all users in caller's organization |
| **Users** | `GET`, `PUT`, `DELETE` | `/users/{id}` | Self / Admin | View, update (role changes require `admin`), or remove org user |
| **Users** | `PUT` | `/users/change-password` | Employee | Change authenticated user's password |
| **Documents** | `POST` | `/documents/upload` | Manager | Upload PDF (`400` invalid magic bytes, `409` org duplicate) |
| **Documents** | `GET` | `/documents`, `/documents/{id}` | Employee | List or inspect org documents (`status`, `error_message`, chunk count) |
| **Documents** | `DELETE` | `/documents/{id}` | Manager | Delete document, chunks, stored file, and clear org cache |
| **Chat** | `POST` | `/chat` | Employee | Synchronous RAG Q&A returning answer, validated citations, `session_id` |
| **Chat** | `POST` | `/chat/stream` | Employee | SSE streaming RAG Q&A (`metadata`, `token`, `done`, `error`) |
| **Chat** | `GET` | `/chat/sessions`, `/chat/sessions/{id}` | Employee | List user's chat sessions or retrieve message history |
| **Chat** | `DELETE` | `/chat/sessions/{id}` | Employee | Delete chat session and messages |
| **Chat** | `GET` | `/chat/providers/health` | Employee | Inspect LLM provider availability and cooldown status |

---

## 11. Roles & Permissions (RBAC)

Hierarchical Role-Based Access Control (`SUPER_ADMIN` > `ADMIN` > `MANAGER` > `EMPLOYEE`), strictly scoped to the caller's `organization_id`:

| Capability | Super Admin | Admin | Manager | Employee |
|---|:---:|:---:|:---:|:---:|
| Ask Questions & Stream Chat (`/chat`, `/chat/stream`) | ✅ | ✅ | ✅ | ✅ |
| View & Delete Own Chat Sessions | ✅ | ✅ | ✅ | ✅ |
| View Organization Documents | ✅ | ✅ | ✅ | ✅ |
| Update Own Profile & Password | ✅ | ✅ | ✅ | ✅ |
| Upload Documents & Trigger Ingestion | ✅ | ✅ | ✅ | ❌ |
| Delete Organization Documents | ✅ | ✅ | ✅ | ❌ |
| Create, Update, Delete Organization Users | ✅ | ✅ | ❌ | ❌ |
| Assign or Modify User Roles | ✅ | ✅ | ❌ | ❌ |
| Manage Organization Details | ✅ | ✅ | ❌ | ❌ |
| Cross-Tenant Platform Administration | ✅ | ❌ | ❌ | ❌ |

---

## 12. Testing & CI

### Backend Test Suite (`211` Tests)
All tests run offline against in-memory SQLite with mocked AI clients and injectable clocks—no external API keys required:

```bash
cd backend
source .venv/bin/activate

pytest -x                              # Run all 211 tests with fail-fast
pytest --cov=. --cov-report=term-missing # Run with coverage report
```

| Test Module(s) | Count | Coverage Focus |
|---|:---:|---|
| `test_citation_validator.py` | 22 | Marker extraction, adjacent markers, numeric support checks, not-found suppression |
| `test_organization_isolation.py`, `test_user_isolation.py` | 24 | Cross-tenant and cross-user isolation across DB, retrieval, sessions, and cache |
| `test_query_rewriter.py` | 18 | Follow-up rewriting, content-word overlap guard, 5 s timeout, standalone cache keys |
| `test_redis_reliability.py` | 12 | Fail-open behaviour, 30 s circuit breaker, TTL handling |
| `test_ai_provider_reliability.py`, `test_provider_fallback.py` | 24 | Retries, error classification, secret redaction, fallback chain, mid-stream rule |
| `test_stage3_security.py` | 12 | RBAC permission matrix, JWT refresh flow, startup secret validation, `422` validation |
| `test_bench_answers.py` | 12 | Answer benchmark scoring, refusal detection, trap evaluation |
| `test_reranker_service.py`, `test_reranker_model.py`, `test_onnx_reranker.py` | 17 | ONNX int8 scoring, batching, thread safety, fail-open, torch-free import verification |
| `test_chat_pipeline_end_to_end.py`, `test_chat_stream_integration.py` | 17 | Full `/chat` and `/chat/stream` flows, SSE event ordering, multi-line newline framing |
| `test_production_readiness.py`, `test_error_handling.py`, `test_api_stability_compatibility.py` | 27 | `/health` probes, cooldown timers, `503`/`409`/`422`/`500` mapping, schema compatibility |
| `test_free_tier_embeddings.py`, `test_stage25_ingestion_hardening.py` | 13 | Token batching, fake-clock pacing, 429 retries, magic bytes, SHA-256 dedupe, header stripping |
| `test_sqlalchemy_relationships.py`, `test_hybrid_retrieval.py`, `test_chunker.py`, etc. | 13 | Relationship registry, cascade deletes, RRF hybrid retrieval, chunk metadata |

### Frontend Tests & GitHub Actions CI
- **Frontend (`vitest`):** Tests SSE chunk buffering/newline framing, `[n]` citation chip parsing, not-found source suppression, `hasRole()`, and `getErrorMessage()`.
- **CI (`.github/workflows/ci.yml`):** Installs dependencies, caches the int8 ONNX model, executes all `211` `pytest` tests with dummy environment secrets, and builds the production Docker image on every push.

---

## 13. Evaluation Framework & Benchmark Results

All benchmarks live in `backend/eval/` and append timestamped runs to `backend/eval/results/summary.csv`. Ground truth uses **exact text anchors** (rather than document IDs) so results remain valid across re-uploads.

```bash
cd backend

# Run retrieval benchmark (supports --no-rerank, --rewrite, --dataset, --label, --org-id, --k)
python eval/bench_retrieval.py --label rerank-onnx

# Run answer faithfulness & abstention benchmark (without mutating DB/Redis)
python eval/bench_answers.py --repeat 3

# Inspect ingested documents and locate anchor phrases per organization
python eval/inspect_corpus.py --org-id 1
```

### Detailed Benchmark Results

#### 1. Retrieval Ranking (`28` Questions)
| Configuration | Hit@1 | Hit@3 | Hit@5 | MRR | Notes |
|---|:---:|:---:|:---:|:---:|---|
| Hybrid only, original corpus | 0.643 | 0.964 | 1.000 | 0.805 | Repeated page headers polluted chunks |
| + Cross-encoder reranker (`20 → 5`), original corpus | 0.929 | 1.000 | 1.000 | 0.964 | +28.6 pts Hit@1 |
| Hybrid only, cleaned corpus | 0.786 | 0.964 | 1.000 | 0.878 | Headers stripped and corpus re-uploaded |
| **+ PyTorch Cross-Encoder (`local`)** | **0.929** | **1.000** | **1.000** | **0.958** | Reference float32 model |
| **+ int8 ONNX Cross-Encoder (`onnx`)** | **0.929** | **1.000** | **1.000** | **0.958** | **Identical retrieval metrics at 22 MB** |
| Voyage remote reranker (free tier) | 0.821 | 0.964 | 1.000 | 0.902 | ~26/28 calls rate-limited and failed open to RRF |

#### 2. Multi-Turn Follow-Up Retrieval
| Configuration | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|:---:|:---:|:---:|:---:|
| Without query rewriting (`8` questions) | 0.625 | 0.875 | 0.875 | 0.729 |
| **With query rewriting (`8` questions)** | **0.750** | **1.000** | **1.000** | **0.854** |
| With query rewriting (`11` questions, multi-run variance) | 0.455–0.727 | 0.818–0.909 | 0.909–1.000 | 0.647–0.780 |

#### 3. Answer Grounding & Abstention
| Check | Result |
|---|---|
| False refusals on answerable questions | **0 / 28** |
| Answerable questions answered with valid citations | **28 / 28** |
| Unanswerable questions refused (`3` questions × `3` trials) | **9 / 9** |
| Adversarial trap questions refused (`8` traps × `3` trials) | **24 / 24** |
| Citation anchor rate (exact-phrase proxy) | **~73% – 81%** |

#### 4. Latency & Memory Profile
| Metric | Measured Value |
|---|---|
| Mean retrieval latency (cached embeddings) | **3153 ms → 1726 ms** (after HNSW/GIN indexes, header cleanup, and org-scoped chunk filters) |
| Idle memory in `512 MiB` container | **171.6 MiB** |
| Container memory during 20-chunk ONNX rerank | **108.6 MiB** (process peak RSS: **155.84 MB**) |
| Rerank latency (20 candidate chunks on CPU) | **0.36 s** |
| PyTorch vs. int8 ONNX rank correlation (`10 × 20` pairs) | **Spearman 0.971**, **Top-5 overlap 100%** |

---

## 14. Project Evolution & Engineering Lessons

### Development Roadmap (Stages 0 → 11)
0. **Audit:** Identified hardcoded secrets, duplicate routes, `5 → 5` reranker bug, and history-blind caching.
1. **Stabilize:** Added fail-open Redis circuit breaker, SSE event contract, LLM fallback chain, and central error handlers (`105` tests).
2. **Measure:** Built text-anchor evaluation datasets, disk embedding cache, and corpus inspector.
3. **Retrieval:** Expanded reranker candidates from `5` to `20`, boosting Hit@1 from `0.643` to `0.929`.
4. **Conversation:** Added LLM query rewriting with overlap guard and standalone-question cache keys (`87.5% → 100%` follow-up Hit@5).
5. **Trust:** Implemented numbered source prompts, numeric citation validation, exact refusal normalization, and adversarial trap tests (`33/33` refusals).
6. **Ingestion & DB:** Added PDF magic-byte validation, SHA-256 deduplication, repeated header/footer stripping, batched inserts, and Alembic `001`–`002`.
7. **Security:** Built hierarchical RBAC, JWT refresh tokens, startup secret validation, and Alembic `003` (`175` tests).
8. **Production:** Created non-root Docker image, Compose stacks, health endpoints, provider cooldowns, and GitHub Actions CI (`184` tests).
9. **Memory:** Replaced PyTorch with 22 MB int8 ONNX Runtime (`171.6 MiB` idle in `512 MiB` container) and added free-tier embedding pacing.
10. **Frontend:** Built custom SSE parser, single-flight Axios refresh interceptor, role-gated UI, citation popovers, and error boundary.
11. **CI & Deploy:** Made external SDK clients lazy at import time and deployed live across Render, Neon, Redis Cloud, and Vercel (`211` tests).

### Key Troubleshooting Lessons
- **512 MiB OOM on Render:** Loading PyTorch + `sentence-transformers` exceeded 512 MiB and caused port-bind timeouts; migrating to int8 ONNX Runtime solved both memory and cold-start speed with zero metric loss.
- **Silent Fail-Open Masking Rate Limits:** A hosted reranker benchmark looked mediocre (`0.821` Hit@1) only because 26/28 calls hit free-tier rate limits and silently fell back to RRF—highlighting the importance of monitoring fail-open warning logs.
- **SSE Newline & Whitespace Framing:** Trimming token whitespace merged words together, and raw `\n` inside tokens prematurely terminated SSE events; fixed via multi-line `data:` framing and removing at most one leading space per `data:` line.
- **Numeric Check vs. Semantic Scope:** In an early test, the LLM combined a project projection with FY2026 company revenue using valid numbers; resolved via explicit scope rules in the prompt and adversarial trap benchmarks.

---

## 15. Security Model & Known Limitations

### Security Controls
| Threat | Mitigation |
|---|---|
| **Cross-Tenant Data Access** | Mandatory `organization_id` filters on documents, chunks, sessions, and Redis keys; 24 isolation tests |
| **Privilege Escalation** | Backend hierarchical RBAC (`require_role`) + organization ownership checks on every mutating endpoint |
| **Token Misuse & Weak Secrets** | Short-lived access tokens (`30 min`), JWT `type` claim enforcement, `bcrypt` passwords, startup `SECRET_KEY` length check ($\ge 32$ chars) |
| **Malicious / Duplicate Uploads** | `%PDF-` magic-byte verification, per-org SHA-256 deduplication, PyMuPDF parsing |
| **Prompt Injection & XSS** | Grounded sources-only system prompt with exact refusal rule; Markdown rendered without raw HTML |
| **Secret Leakage** | Secret redaction in logs (`_sanitize_error`), sanitized `500` responses with request IDs, pre-push regex scans |

### Known Limitations & Roadmap
- **Ephemeral File Storage:** Uploaded PDFs live on local container disk; chunks and embeddings persist in PostgreSQL across redeploys, but raw PDF downloads require S3/R2 object storage (planned).
- **In-Process Ingestion & Cooldowns:** Document ingestion runs as a FastAPI background task and LLM cooldowns live in-process; multi-worker deployments should move these to Redis-backed queues/state.
- **Auth Storage & Rate Limiting:** Frontend stores tokens in `localStorage` without refresh-token revocation or per-IP rate limiting (`slowapi`, `httpOnly` cookies, and PostgreSQL Row-Level Security are on the roadmap).
- **Benchmark Scale:** Current datasets (`28` retrieval / `11` follow-up / `19` abstention) are small and partly synthetic; expanding to 100+ real-world documents with RAGAS faithfulness metrics is planned.

---

## 16. Interview Preparation & Glossary

### Elevator Pitches
- **30 Seconds:** *"I built a multi-tenant document Q&A platform where organizations upload PDFs and stream answers with page-level citations. It uses hybrid retrieval—pgvector cosine search plus PostgreSQL full-text search fused with RRF—followed by a 22 MB int8 ONNX cross-encoder reranker. On my evaluation set, reranking lifted Hit@1 from 78.6% to 92.9%, and the entire stack runs inside a 512 MB container on free tiers."*
- **2 Minutes:** Add the full pipeline (follow-up rewriting with overlap guard, tenant-scoped Redis cache, hybrid 20 → rerank 5, Gemini → Groq → DeepSeek fallback chain, numeric citation validation), trust guardrails (`33/33` abstentions, `0/28` false refusals), and security (hierarchical RBAC, JWT refresh rotation, 24 isolation tests).
- **5 Minutes:** Deep-dive into three engineering stories: (1) solving Render's 512 MiB OOM by replacing PyTorch with int8 ONNX Runtime while verifying Spearman `0.971` and `100%` Top-5 overlap; (2) evaluation-first engineering (catching rate-limited reranker fallbacks and cleaning repeated PDF headers); and (3) building the content-word overlap guard after observing an off-topic query rewrite.

### Glossary
| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation: grounding LLM responses in retrieved document chunks |
| **Hybrid Search** | Combining dense vector similarity (`pgvector`) with sparse keyword matching (`tsvector`) |
| **RRF** | Reciprocal Rank Fusion ($\sum \frac{1}{k + \text{rank}}$): rank-based merging without score calibration |
| **Bi-Encoder vs. Cross-Encoder** | Bi-encoders embed query and chunk independently (fast); cross-encoders score `(query, chunk)` jointly (accurate) |
| **Quantization (`int8`)** | Compressing 32-bit float model weights to 8-bit integers for ~4x smaller memory and faster CPU inference |
| **Hit@K / MRR** | Share of queries with a relevant chunk in top $K$ / Mean Reciprocal Rank ($\frac{1}{\text{rank}}$) of the first relevant chunk |
| **Abstention** | Refusing to answer (`I could not find this in the provided documents.`) when retrieved sources lack evidence |
| **Circuit Breaker / Fail-Open** | Temporarily bypassing a failing non-critical dependency (Redis, reranker) so core chat remains available |