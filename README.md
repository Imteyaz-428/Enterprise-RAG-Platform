# 🚀 Enterprise RAG Platform

> A multi-tenant, production-grade Retrieval-Augmented Generation (RAG) platform enabling organizations to securely index proprietary knowledge, retrieve contextual evidence through hybrid search and cross-encoder reranking, and stream verified answers with deterministic source citations.

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17%20pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Production%20Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

---

## 📑 Table of Contents
- [What It Is](#-what-it-is)
- [Key Features](#-key-features)
- [Architecture Overview](#-architecture-overview)
- [Setup & Installation](#-setup--installation)
  - [Prerequisites](#prerequisites)
  - [With Docker (Recommended)](#running-with-docker)
  - [Without Docker (Local Development)](#running-without-docker-bare-metal)
- [Environment Variables](#-environment-variables)
- [API Overview](#-api-overview)
- [Roles & Permissions](#-roles--permissions)
- [Running Tests & Benchmarks](#-running-tests--benchmarks)
- [Database Migrations](#-database-migrations)
- [Security Notes](#-security-notes)
- [Known Limitations](#-known-limitations)

---

## 📖 What It Is

The **Enterprise RAG Platform** is an enterprise AI knowledge management system designed for strict data isolation, high retrieval precision, and reliable AI generation. Organizations upload proprietary documents (such as PDF manuals, contracts, technical specifications), which are chunked, embedded, and indexed. When team members ask questions, the system:
1. Re-writes conversational follow-up questions into standalone queries using conversation context.
2. Performs **hybrid retrieval** fusing dense semantic embeddings (`pgvector`) with sparse BM25 keyword matching via Reciprocal Rank Fusion (RRF).
3. Evaluates top passages with a **neural cross-encoder reranker** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to eliminate irrelevant context.
4. Generates responses through an **AI provider fallback mesh** (Gemini → Groq → DeepSeek) equipped with in-memory thread-safe rate-limit and quota cooldowns.
5. Emits strict, verified citations mapping exact bracketed markers (`[1]`, `[2]`) to document titles, pages, and chunk snippets.

---

## ✨ Key Features

- **Strict Multi-Tenant Isolation**: Complete isolation of organizations, users, documents, chunks, embeddings, and chat sessions.
- **Hybrid Retrieval & Reranking**: Combines dense semantic vectors (Voyage AI) and sparse keyword search (PostgreSQL trigram/full-text) with Cross-Encoder scoring for high retrieval precision (92.9% Hit@1, 0.964 MRR).
- **Conversational Query Rewriting**: Re-writes multi-turn follow-up queries to maintain high retrieval recall across continuous dialogues.
- **Resilient AI Provider Mesh**: Seamless fallback across Gemini, Groq, and DeepSeek with automated cooldowns on HTTP 429 / quota exhaustion (capped at 15 minutes, defaulting to 60 seconds).
- **Faithful Citation Validation**: Verifies that every bracketed source marker in LLM answers corresponds to actual retrieved passages, stripping unsupported citations.
- **Redis Caching & Fail-Open Resilience**: Sub-millisecond response for repeat questions; non-blocking fail-open design ensures chat availability even during cache outages.
- **Hierarchical Role-Based Access Control (RBAC)**: Super Admin, Admin, Manager, and Employee roles governing administrative, document, and query capabilities.
- **Production-Hardened Docker**: Slim Python 3.13 image executing under a non-root system user (`appuser`) with automated database migration entrypoints and `/health` probes.

---

## 🏛️ Architecture Overview

```mermaid
flowchart TD
    Client["Client Web App (React 19 + Vite)"]

    subgraph Platform ["Enterprise RAG Platform Backend (FastAPI)"]
        Router["API Gateway / Routers<br>(Auth, Org, Users, Docs, Chat, Health)"]
        RBAC["RBAC & Security Guard<br>(JWT, Passlib, Org Isolation)"]
        ChatEngine["Chat & Streaming Engine"]
        Rewriter["Conversational Query Rewriter"]
        RetrievalSvc["Hybrid Retrieval Service<br>(RRF Dense + Sparse)"]
        RerankerSvc["Cross-Encoder Reranker<br>(ms-marco-MiniLM-L-6-v2)"]
        Validator["Citation Validator & Cleaner"]
        AISvc["AIService Fallback Engine<br>(Rate-Limit Cooldown + Tenacity)"]
    end

    subgraph DataTier ["Data & Caching Layer"]
        Postgres[("PostgreSQL 17 + pgvector<br>(Tenant DB, Vector Index, Full-Text)")]
        RedisCache[("Redis 7<br>(Response Cache & Cooldowns)")]
    end

    subgraph ExternalAI ["External AI Provider APIs"]
        Voyage["Voyage AI<br>(Dense Embeddings)"]
        Gemini["Google Gemini<br>(Primary LLM)"]
        Groq["Groq Llama-3.3<br>(Fallback LLM 1)"]
        DeepSeek["DeepSeek Chat<br>(Fallback LLM 2)"]
    end

    Client -->|HTTP / SSE| Router
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

For complete pipeline sequence interactions, see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.13+
- Node.js 18+ (for frontend)
- PostgreSQL 17 with `pgvector` extension
- Redis 7+
- (Optional) Docker and Docker Compose

---

### Running with Docker

The repository includes a production-ready stack definition (`docker-compose.yml`) and an override for live local development (`docker-compose.dev.yml`).

#### 1. Production Stack
Runs PostgreSQL (pgvector), Redis, and the backend with named volumes for database persistence (`pgdata`) and uploaded documents (`uploads`), running under an unprivileged user without source mounting:

```bash
# 1. Create environment file from template
cp backend/.env.example .env

# 2. Start the production stack
docker compose up -d --build

# 3. Check container status
docker compose ps

# 4. View logs
docker compose logs -f backend
```

#### 2. Development Stack (with hot-reload and source mount)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

---

### Running Without Docker (Bare Metal)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies (CPU PyTorch and production libraries)
pip install -r requirements.txt -r requirements-dev.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL, Redis, and AI Provider keys

# Apply Alembic database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🔐 Environment Variables

The table below outlines all environment variables utilized by the backend. **No production secrets or credentials should ever be hard-coded or committed.**

| Variable Name | Description | Required |
|---|---|:---:|
| `DATABASE_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@host:port/dbname`) | Yes |
| `REDIS_URL` | Redis connection URL (e.g. `redis://host:port/0` or `rediss://...`) | Optional |
| `REDIS_HOST` | Redis hostname (used if `REDIS_URL` is omitted; defaults to `localhost`) | Optional |
| `REDIS_PORT` | Redis port number (defaults to `6379`) | Optional |
| `REDIS_DB` | Redis database number (defaults to `0`) | Optional |
| `REDIS_PASSWORD` | Redis authentication password | Optional |
| `REDIS_EXPIRE` | Default cache expiration TTL in seconds (defaults to `3600`) | Optional |
| `REDIS_CONNECT_TIMEOUT` | Timeout in seconds for Redis socket connection (defaults to `2.0`) | Optional |
| `REDIS_SOCKET_TIMEOUT` | Timeout in seconds for Redis socket read/write operations (defaults to `2.0`) | Optional |
| `REDIS_CIRCUIT_COOLDOWN`| Circuit-breaker trip duration in seconds during Redis outages (defaults to `30.0`) | Optional |
| `SECRET_KEY` | High-entropy cryptographic key for signing and validating JWT tokens | Yes |
| `ALGORITHM` | Cryptographic JWT signing algorithm (defaults to `HS256`) | Optional |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of access tokens in minutes (defaults to `180`) | Optional |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifetime of refresh tokens in days (defaults to `30`) | Optional |
| `VOYAGE_API_KEY` | API key for Voyage AI dense embedding generation (`voyage-3-large`) | Yes |
| `VOYAGE_MIN_INTERVAL_SECONDS` | Minimum interval (in seconds) between consecutive Voyage API calls enforced via a process-wide lock (e.g. `20` or `21` for Voyage free tier's 3 RPM limit; defaults to `0`) | Optional |
| `EMBED_BATCH_TOKENS` | Token threshold for batching chunks during document embedding (tokens estimated as `len(text)/3`; defaults to `6000` for Voyage free tier's 10,000 TPM limit) | Optional |
| `RERANKER_BACKEND` | Reranker engine selection: `onnx` (default in production Docker image; CPU int8 quantized model), `local` (dev/test PyTorch CrossEncoder), `voyage` (Voyage AI remote API), `none` (passthrough); defaults to `onnx` in Docker image, `local` in dev | Optional |
| `VOYAGE_RERANK_MODEL` | Voyage AI reranking model used when `RERANKER_BACKEND=voyage` (defaults to `rerank-2`) | Optional |
| `ONNX_RERANKER_MODEL_PATH` | Path to the ONNX model file (defaults to `models/reranker/model.onnx`) | Optional |
| `ONNX_RERANKER_TOKENIZER_PATH` | Path to the tokenizer JSON file (defaults to `models/reranker/tokenizer.json`) | Optional |
| `GEMINI_API_KEY` | Primary LLM generation key (Google Gemini 2.5 Flash) | Yes |
| `GOOGLE_API_KEY` | Alternative Google API key fallback for Gemini models | Optional |
| `GROQ_API_KEY` | Secondary fallback LLM key (Groq Llama-3.3-70b-versatile) | Optional |
| `DEEPSEEK_API_KEY` | Tertiary fallback LLM key (DeepSeek Chat) | Optional |
| `PORT` | Web server bind port (defaults to `8000`) | Optional |

### Free-Tier Mode & Memory Optimization (Zero Provider Billing)

Without a paid subscription or payment method, Voyage AI imposes strict free-tier rate limits:
- **3 requests/minute (3 RPM)**: Requests must be spaced by at least 20 seconds.
- **10,000 tokens/minute (10,000 TPM)**: Remote reranking 20 candidate chunks consumes over 5,000 tokens per call, quickly exhausting quotas and failing queries. PDFs exceeding ~15 pages fail to embed in a single request.

To run completely free without provider billing or rate limit exhaustion:

1. **Local ONNX Reranker (`RERANKER_BACKEND=onnx`)**:
   - Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` quantized to int8 (`onnx/model_qint8_arm64.onnx`, 23.2 MB, bit-for-bit identical to generic CPU `model_qint8_avx512.onnx`), baked into the container image at Docker build time into `/app/models/reranker/`.
   - Uses `tokenizers` (max length 512, truncation, batches of at most 20) and `onnxruntime` (CPU execution provider, `intra_op_num_threads=1`).
   - Keeps `torch` and `transformers` completely out of the default Docker image.
   - **Measured Memory in `docker run --memory=512m`**:
     - Container memory during 20-chunk rerank: **108.6 MiB / 512 MiB (21.2% usage)**
     - Process peak RSS (`ru_maxrss`): **155.84 MB** (VmHWM: **160.5 MB**)
     - Latency: **~0.36 seconds** per 20 pairs
     - Spearman rank correlation with PyTorch local reranker: **0.9709**
     - Top-5 overlap with PyTorch local reranker: **100.0%**
     - Voyage quota consumed: **0 TPM / 0 RPM** (completely free!)
   - **Fail-Open**: Fails open to fused reciprocal rank order on any error.

2. **Free-Tier Aware Embeddings**:
   - `VOYAGE_MIN_INTERVAL_SECONDS` (default `0`): Process-wide thread lock enforcing consecutive Voyage API calls are at least `N` seconds apart (e.g. set to `21.0` to respect the 3 RPM limit).
   - **Ingestion Batching**: In `document_processor.py`, chunks are split into batches of at most `EMBED_BATCH_TOKENS` (default `6000`, estimating tokens as `len(text)/3`), embedded batch-by-batch, retrying on 429 with exponential backoff up to 5 times (reusing `utils/retry.py`). Document error message is updated only after all 5 retries are exhausted.
   - **Query Embedding**: On 429, waits 5 seconds and retries once; if rate limited again, returns a clear HTTP 503 `"Search is busy, please retry in a few seconds"`.

---

## 📡 API Overview

| Tag | HTTP Method | Endpoint | Description | Minimum Role |
|---|:---:|---|---|:---:|
| **Health** | `GET` | `/health` | Liveness probe: returns 200 without dependencies | Public |
| **Health** | `GET` | `/health/ready` | Readiness probe: checks DB (SELECT 1) and Redis ping | Public |
| **Auth** | `POST` | `/auth/signup` | Register new organization and initial administrator user | Public |
| **Auth** | `POST` | `/auth/login` | Authenticate user credentials and return access + refresh tokens | Public |
| **Auth** | `POST` | `/auth/refresh` | Exchange valid refresh token for fresh access token | Public |
| **Auth** | `GET` | `/auth/me` | Fetch authenticated user profile and organizational context | Employee |
| **Organizations** | `GET` | `/organizations` | List organizations (platform admin) or get own organization | Admin |
| **Organizations** | `PUT` | `/organizations/{id}` | Update organization metadata | Admin |
| **Users** | `GET` | `/users` | List all users within caller's organization | Admin |
| **Users** | `POST` | `/users` | Create new user within caller's organization | Admin |
| **Users** | `PUT` | `/users/{id}` | Update user details or reassign role | Admin / Self |
| **Users** | `DELETE` | `/users/{id}` | Remove user from organization | Admin |
| **Users** | `PUT` | `/users/change-password` | Update current user password | Employee |
| **Documents** | `POST` | `/documents/upload` | Upload PDF, trigger chunking, vector embedding, and indexing | Manager |
| **Documents** | `GET` | `/documents` | List organization documents with status and chunk count | Employee |
| **Documents** | `GET` | `/documents/{id}` | Get document metadata and download link | Employee |
| **Documents** | `DELETE` | `/documents/{id}` | Delete document, chunks, and associated vector records | Manager |
| **Chat** | `POST` | `/chat` | Submit question, retrieve context, generate answer with citations | Employee |
| **Chat** | `POST` | `/chat/stream` | Server-Sent Events (SSE) streaming chat answer with citations | Employee |
| **Chat** | `GET` | `/chat/sessions` | List user's conversation sessions | Employee |
| **Chat** | `GET` | `/chat/sessions/{id}` | Retrieve chat session message history | Employee |
| **Chat** | `DELETE`| `/chat/sessions/{id}` | Delete conversation session and all messages | Employee |

---

## 🛡️ Roles & Permissions

The platform enforces hierarchical Role-Based Access Control (`SUPER_ADMIN` > `ADMIN` > `MANAGER` > `EMPLOYEE`):

| Capability | Super Admin | Admin | Manager | Employee / User |
|---|:---:|:---:|:---:|:---:|
| Ask Questions & Stream Chat (`/chat`, `/chat/stream`) | ✅ | ✅ | ✅ | ✅ |
| View Own Chat Sessions & History | ✅ | ✅ | ✅ | ✅ |
| View Organization Documents | ✅ | ✅ | ✅ | ✅ |
| Update Own Password & Profile | ✅ | ✅ | ✅ | ✅ |
| Upload Documents & Trigger Ingestion | ✅ | ✅ | ✅ | ❌ |
| Delete Organization Documents | ✅ | ✅ | ✅ | ❌ |
| Create, Update, Delete Organization Users | ✅ | ✅ | ❌ | ❌ |
| Assign or Change User Roles | ✅ | ✅ | ❌ | ❌ |
| Manage Organization Details | ✅ | ✅ | ❌ | ❌ |
| Cross-Tenant Platform Administration | ✅ | ❌ | ❌ | ❌ |

---

## 🧪 Running Tests & Benchmarks

### 1. Test Suite Execution
All unit, integration, and reliability tests mock external AI provider calls to ensure deterministic execution without credential requirements:

```bash
cd backend
source .venv/bin/activate

# Run all tests with fail-fast flag
pytest -x

# Run tests with coverage report
pytest --cov=. --cov-report=term-missing
```

### 2. Retrieval & Answer Benchmarks
Automated evaluation scripts are located in `backend/eval/`:

```bash
cd backend

# Execute retrieval benchmark across queries and traps
python eval/eval_retrieval.py

# Evaluate answer quality and citation faithfulness
python eval/eval_answers.py
```

Evaluation run logs and comparative metrics are automatically appended to `backend/eval/results/summary.csv`.

---

## 🗄️ Database Migrations

Database schema changes are managed via Alembic:

```bash
cd backend
source .venv/bin/activate

# Apply all pending migrations to the latest revision
alembic upgrade head

# Create a new migration revision after model modifications
alembic revision --autogenerate -m "Add new column or table"

# Rollback single migration step
alembic downgrade -1
```

---

## 🔒 Security Notes

- **Credential Sanitization**: The application sanitizes error strings and log outputs (`_sanitize_error`) to prevent leaking API keys, bearer tokens, or database passwords.
- **Tenant Scope Enforcement**: All document, chunk, session, and message database operations include mandatory `organization_id` filters to eliminate horizontal privilege escalation.
- **JWT Cryptography**: Signed with `HS256`, rejecting tokens lacking cryptographic expiration or subject claims. Passwords use salted `bcrypt` hashing.
- **Container Isolation**: Docker images run as an unprivileged user (`appuser`, UID 1000) rather than `root`.
- **Secrets Management**: Secrets are injected strictly through environment variables or uncommitted `.env` files; secrets are never baked into image layers.

---

## ⚠️ Known Limitations

1. **Document Types**: Document ingestion currently specializes in PDF extraction via PyMuPDF (`fitz`). Word (`.docx`) or Markdown direct uploads require pre-conversion.
2. **Provider Cooldown Scope**: AI provider cooldown states are managed in-memory per backend process. In multi-replica worker environments without sticky routing, an outage on one worker initiates local cooldown rather than cluster-wide (which can be augmented with Redis-backed cooldown keys).
3. **Context Window Limits**: Extremely large prompts containing tens of retrieved passages may be truncated to fit within model context limitations.
