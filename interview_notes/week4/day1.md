# Week 4 - Day 1: Interview Notes: Backend Audit, Redis Reliability, Error Handling, SQLAlchemy

## 1. Why did we start with an audit?

Before adding features, the existing backend (Week 1–3) was reviewed to find what would break in production. Priorities were chosen in this order: stability, measurement, retrieval quality, security, deployment.

Problems found:

- A `.env` file with live keys was inside the project archive.
- Duplicate routes: `/users/login` and `/auth/login`.
- SQLAlchemy relationship registry error (`Organization` referenced `"Document"` before it was imported).
- Retrieval fetched only 5 candidates and the reranker reranked those same 5 (no benefit).
- The cache key ignored conversation history.
- Streaming setup errors happened after the HTTP 200 had already started.
- No migrations (`create_all` only), no ON DELETE rules.
- Any logged-in user could upload or delete documents.
- `torch` and `sentence-transformers` were imported but missing from `requirements.txt`.

---

## 2. Redis reliability (fail-open)

Problem: if Redis is down or unreachable, a naive app hangs or crashes.

What was implemented in `RedisService`:

- Operations: `get`, `set`, `delete`, `ttl`, `exists`, `ping`.
- Connection and socket timeouts of **2 seconds**.
- A **circuit breaker** with a **30 second cooldown**: after a failure, Redis is skipped for 30 seconds instead of retrying on every request.
- **Fail-open** behaviour: any Redis error returns "cache miss" and the normal RAG pipeline continues.

Why: a cache is an optimisation, not a dependency. If it fails, the system should become slower, not broken.

Tests: 12 unit tests (get/set/delete/ttl, failure, cooldown, recovery).

---

## 3. Centralised error handling

Goal: no unexplained HTTP 500 responses.

Handlers in `core/errors.py`:

| Exception | HTTP status | Meaning |
|---|---|---|
| `OperationalError` (DB drop, SSL disconnect) | 503 | `DATABASE_UNAVAILABLE` |
| `IntegrityError` (unique / foreign key) | 409 | `INTEGRITY_ERROR` |
| `AIProviderError` (all providers failed) | 503 | `AI_SERVICE_UNAVAILABLE` |
| `RequestValidationError` | 422 | structured error list |
| Any other exception | 500 | sanitized message + request id, traceback only in logs |

Other fixes:

- Table creation moved from import time into the FastAPI **lifespan**, so the app does not crash on import when the database is briefly unreachable.
- `get_current_user` validates the JWT `sub` claim. A malformed token now returns **401** instead of crashing with a `ValueError` (500).

Tests: 9 tests.

---

## 4. SQLAlchemy relationship registry

Error: `expression 'Organization' failed to locate a name`.

Cause: relationships use string names (`"Document"`). SQLAlchemy can only resolve them if every model module has been imported before mappers are configured.

Fix: `models/__init__.py` imports all models (Organization, User, Document, DocumentChunk, ChatSession, ChatMessage). Importing any `models.x` module runs the package `__init__` first, so the registry is always complete. Relationships were also made symmetric with matching `back_populates` and cascade rules.

Tests: 5 relationship and cascade tests. Test suite after Phase 1: **105 tests passing**.

---

## 5. Flow: Redis fail-open

Request

↓

Cache lookup

├── Redis healthy → hit or miss

└── Redis down / circuit open → treat as miss

↓

RAG pipeline

↓

Try to cache the result (ignored if Redis is unavailable)

↓

Response

---

## 6. Interview Questions

### Q1. What does fail-open mean?
When an optional dependency fails, the system continues without it. For Redis, a failure is treated as a cache miss.

### Q2. What is a circuit breaker?
A mechanism that stops calling a failing dependency for a cooldown period so that every request does not wait for a timeout.

### Q3. Why a 2 second timeout?
To keep the API responsive when Redis is unreachable or firewalled.

### Q4. Why convert database errors to 503 and constraint errors to 409?
503 tells clients the service is temporarily unavailable (retry later). 409 tells them the request conflicts with existing data (fix the request).

### Q5. Why never expose tracebacks to users?
They can leak secrets, SQL, and internal paths. The client gets a safe message and a request id; the traceback stays in server logs.

### Q6. Why move `create_all` into the lifespan handler?
Import-time side effects can crash the whole process before it can serve health checks. Lifespan runs at startup in a controlled place.

### Q7. What caused the SQLAlchemy "failed to locate a name" error?
String-based relationships were resolved before all model classes had been imported.

### Q8. What was the order of priorities for improvement?
Stability, then measurement, then retrieval quality, then security, then production readiness.