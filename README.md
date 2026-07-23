# 🚀 Enterprise Multi-Tenant RAG Platform

> A production-oriented AI knowledge management backend that lets organizations upload documents, run semantic search over them, and chat with their private knowledge base using Retrieval-Augmented Generation (RAG).

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue)
![Redis](https://img.shields.io/badge/Redis-Caching-red)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-orange)

---

# 📖 Overview

Enterprise RAG Platform is a multi-tenant, RAG-as-a-Service backend built with **FastAPI**, **PostgreSQL + pgvector**, and **Redis**.

Each organization can upload PDF documents, have them automatically chunked and embedded, and let their users chat with that knowledge base — with every answer grounded in retrieved source chunks and cited back to the originating document.

The platform is built around a handful of enterprise engineering patterns:

- Multi-Tenant Architecture (organization-scoped data isolation)
- Role-Based Access Control (RBAC)
- Service Layer Architecture
- Provider Pattern (pluggable LLM backends with fallback)
- Retrieval-Augmented Generation (RAG)
- Background Document Processing
- Redis Response Caching
- Streaming AI Responses (SSE)

---

# ✨ Features

## 🔐 Authentication & Security

- JWT authentication (OAuth2 Bearer flow, `python-jose`)
- Password hashing with `bcrypt` via `passlib`
- Secrets (JWT key, algorithm, expiry) loaded from environment, not hardcoded
- Role-Based Access Control (`admin` / regular user)
- Organization-scoped authorization on every resource (users, documents, chat sessions) — one tenant cannot read another tenant's data

## 🏢 Multi-Tenant Architecture

- Organization management (CRUD)
- User management scoped to an organization
- Documents, chat sessions, and messages all carry `organization_id`
- Every read/write path checks the requester's organization before returning data

## 📄 Document Processing

- PDF upload with content-type, size, and empty-file validation
- UUID-based file storage on disk
- Asynchronous background processing (FastAPI `BackgroundTasks`) so uploads return immediately
- Document status tracking (`processing` → `completed` / `failed`)
- Text extraction via **PyMuPDF**
- Fixed-size chunking with overlap
- Embeddings via **Voyage AI** (`voyage-3-large`)
- Vector storage and cosine-similarity search via **pgvector**

## 🤖 AI & RAG

- Semantic search over an organization's documents (top-K cosine similarity)
- Multi-document retrieval with de-duplicated source citations
- Centralized prompt-building service
- Pluggable multi-provider LLM layer: **Gemini → Groq → DeepSeek**, with automatic retry and provider fallback if one fails

## 💬 Chat System

- Persistent chat sessions per user, per organization
- Automatic session creation and title generation from the first message
- Full conversation history stored and replayed into the prompt
- Streaming responses over Server-Sent Events (`/chat/stream`)
- Non-streaming JSON responses (`/chat`) for simpler clients
- Session listing, retrieval, and deletion

## ⚡ Performance

- Redis caching of chat answers, keyed by organization + normalized question
- Background tasks for document ingestion (non-blocking upload endpoint)
- Retry logic and automatic fallback across AI providers

---

# 🛠️ Tech Stack

### Backend
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL + pgvector
- Redis
- Pydantic v2

### AI / ML
- Voyage AI (embeddings)
- Gemini, Groq, DeepSeek (generation, with fallback)
- PyMuPDF (PDF text extraction)

### Security
- JWT (`python-jose`)
- OAuth2 Password Flow
- bcrypt (`passlib`)

### DevOps
- Docker + Docker Compose (Postgres/pgvector, Redis, backend service)
- Kubernetes manifests — *planned*

---

# 🏗️ Architecture

```text
                           User
                             │
                             ▼
                     Authentication
                             │
                             ▼
                     FastAPI Router
                             │
                             ▼
                      ChatService
                             │
      ┌──────────────────────┴──────────────────────┐
      ▼                                              ▼
RetrievalService                              Session Service
      │
      ▼
Prompt Service
      │
      ▼
AI Service (retry + fallback)
      │
 ┌────┴──────────────────┐
 ▼                        ▼
Gemini              Groq → DeepSeek
      │
      ▼
Generated Response (+ citations)
```

---

# 🔄 RAG Pipeline

```text
Upload PDF
     │
     ▼
Validate (type, size, non-empty)
     │
     ▼
Store file (UUID filename) + create Document row
     │
     ▼
Background Task ─┐
                 ├─ Extract Text (PyMuPDF)
                 ├─ Chunk Text (fixed size + overlap)
                 ├─ Generate Embeddings (Voyage AI)
                 └─ Store chunks + embeddings (pgvector)
     │
     ▼
User asks a question
     │
     ▼
Embed question → Cosine similarity search (org-scoped)
     │
     ▼
Retrieve top-K chunks
     │
     ▼
Build prompt (history + chunks + question)
     │
     ▼
AI Service → Gemini / Groq / DeepSeek
     │
     ▼
Answer + citations → cached in Redis → returned to user
```

---

# 📂 Project Structure

```text
enterprise-rag-platform/
│
├── backend/
│   ├── core/            # security (JWT/hashing), dependencies, enums
│   ├── crud/            # DB access layer
│   ├── database/        # SQLAlchemy engine/session setup
│   ├── dependencies/    # FastAPI dependency providers (DB session)
│   ├── models/          # SQLAlchemy ORM models
│   ├── router/          # API route definitions
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/
│   │   ├── ai/          # provider pattern (Gemini/Groq/DeepSeek) + prompts
│   │   ├── background/  # document processing pipeline
│   │   ├── cache/       # Redis service
│   │   └── chat/        # chat orchestration, retrieval, prompt building
│   ├── utils/           # chunking, embeddings, PDF extraction, logging, retry
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── app.py
│
├── frontend/            # planned (React)
├── docker/              # deployment configs (planned)
├── kubernetes/          # K8s manifests (planned)
└── README.md
```

---

# 📡 API Overview

## Users & Auth

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/users/` | Register a new user |
| POST | `/users/login` | Login (OAuth2 form), returns JWT |
| GET | `/users/me` | Get the current authenticated user |
| GET | `/users/{id}` | Get a user by ID (same org only) |
| GET | `/users/` | List users (admin only) |
| PUT | `/users/{id}` | Update a user (self or admin) |
| DELETE | `/users/{id}` | Delete a user (admin only) |

## Organizations

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/organizations/` | Create an organization |
| GET | `/organizations/` | List organizations (admin only) |
| GET | `/organizations/{id}` | Get an organization (same org only) |
| PUT | `/organizations/{id}` | Update an organization (admin only) |
| DELETE | `/organizations/{id}` | Delete an organization (admin only) |

## Documents

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/documents/upload` | Upload a PDF, kicks off background processing |
| GET | `/documents/{id}` | Get document status/details (same org only) |

## Chat

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/chat` | Ask a question, get a full JSON response |
| POST | `/chat/stream` | Ask a question, get an SSE token stream |
| GET | `/chat/sessions` | List the current user's chat sessions |
| GET | `/chat/sessions/{id}` | Get a session with full message history |
| DELETE | `/chat/sessions/{id}` | Delete a chat session |

---

# 🚀 Quick Start

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/Imteyaz-428/enterprise-rag-platform.git
cd enterprise-rag-platform/backend

cp .env.example .env   # fill in your keys, see below
docker compose up --build
```

This spins up Postgres (with pgvector), Redis, and the FastAPI backend together on `http://localhost:8000`.

### Option B — Local

```bash
git clone https://github.com/Imteyaz-428/enterprise-rag-platform.git
cd enterprise-rag-platform/backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app:app --reload
```

### Environment Variables

Create a `.env` file inside `backend/`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/enterprise_rag

SECRET_KEY=replace-with-a-long-random-value
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=180

VOYAGE_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
DEEPSEEK_API_KEY=

REDIS_HOST=localhost
REDIS_PORT=6379
```

---

# 🧪 Example Workflow

```text
Register user → Login → Upload PDF
                              │
                              ▼
                    Background Processing
                    (extract → chunk → embed → store)
                              │
                              ▼
                        Ask a question
                              │
                              ▼
              Semantic search over org's documents
                              │
                              ▼
                 Retrieve relevant chunks + build prompt
                              │
                              ▼
                  Generate answer (with fallback)
                              │
                              ▼
        Save to chat history → cache in Redis → return
                  answer + source citations
```

---

# 📊 Project Status

## ✅ Completed

**Backend Core**
- JWT authentication, RBAC, organization-scoped authorization
- User & organization management

**Document Processing**
- Upload, validation, background processing, status tracking
- Text extraction, chunking, Voyage AI embeddings, pgvector storage

**AI & RAG**
- Semantic search, multi-document retrieval, prompt builder, citations
- Multi-provider AI support with retry and fallback

**Chat**
- Persistent sessions, conversation history, SSE streaming

**Performance & DevOps**
- Redis caching, background tasks
- Dockerfile + Docker Compose (Postgres/pgvector, Redis, backend)

## 🚧 In Progress
- React frontend

## 📅 Planned
- Kubernetes deployment manifests
- CI/CD pipeline
- Rate limiting
- Monitoring & structured logging
- Automated test suite

---

# 🗺️ Roadmap

## ✅ Phase 1 — Backend
Authentication · RBAC · Multi-Tenant Architecture · Document Processing · RAG Pipeline · Chat System · Streaming · Redis Caching · Background Tasks

## 🚧 Phase 2 — Frontend
React Dashboard · Auth Pages · Document Management · Chat Interface · Citation UI

## ✅ / 🚧 Phase 3 — Deployment
Docker & Docker Compose ✅ · Kubernetes 🚧 · Managed hosting for frontend & backend 🚧

## 📦 Phase 4 — Production Hardening
Monitoring · Logging · Rate Limiting · CI/CD · Automated Tests

---

# 📚 Key Learnings

Building this project involved hands-on work with:

- FastAPI, SQLAlchemy, PostgreSQL, pgvector
- Retrieval-Augmented Generation & semantic search
- Vector embeddings and prompt engineering
- JWT authentication and multi-tenant authorization design
- Provider pattern for interchangeable LLM backends
- Service layer architecture and separation of concerns
- Background task processing and Redis caching
- Server-Sent Events for streaming AI responses

---

# 🤝 Contributing

Contributions, suggestions, and feedback are welcome.

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Push to your fork
5. Open a Pull Request

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 👨‍💻 Author

**Imteyaz Alam**
B.Tech – Artificial Intelligence & Machine Learning

- GitHub: https://github.com/Imteyaz-428
- LinkedIn: https://linkedin.com/in/imteyaz428

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.