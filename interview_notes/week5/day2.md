# Week 5 - Day 2: Interview Notes: Ingestion Hardening and Database Migrations

(Builds on Week 3 Day 4, where PDF processing was moved into background tasks.)

## 1. Why harden ingestion?

Problems with the first version:

- Only the `Content-Type` header was checked (easy to fake).
- The same PDF could be uploaded many times, and duplicates crowded the top results.
- Every chunk was committed separately (slow and could leave partial data).
- A failed document gave no reason and could leave partial chunks that retrieval might still use.
- Repeated page headers and footers became part of every chunk.
- Chunks had no `organization_id` of their own.
- Deleting a document left the file on disk.

---

## 2. Alembic migrations

Why not `create_all()`? It creates missing tables but never adds columns to existing ones. Migrations version the schema and can be rolled back.

- `001_baseline`: current schema, starting with `CREATE EXTENSION IF NOT EXISTS vector`.
- `002_ingestion_hardening`:
  - `documents.file_hash` (SHA-256) and `documents.error_message`
  - partial unique index on `(organization_id, file_hash)`
  - `document_chunks.organization_id` (foreign key, backfilled from documents, then NOT NULL)
  - index on `document_chunks(organization_id)`
  - **GIN** index on `to_tsvector('english', chunk_text)` for full-text search
  - **HNSW** index on the embedding column with `vector_cosine_ops`
- `003_db_integrity`: ON DELETE rules (see Day 3).

Applying to an existing database: `alembic stamp 001_baseline`, then `alembic upgrade head`. Migrations were first proven on a throwaway database (upgrade, downgrade, upgrade, drop) before touching the real one.

---

## 3. Ingestion flow after hardening

Upload

↓

Check `%PDF-` magic bytes

↓

Compute SHA-256

↓

Same hash in the **same organization**? → HTTP 409 (different organization is allowed)

↓

Save document (`processing`) and return immediately

↓

Background task: extract text page by page → strip repeated headers/footers → chunk

↓

Embed in token-bounded batches (see Day 5)

↓

Insert all chunks in one batched transaction with `organization_id`, `document_id`, `chunk_index`, `page_number`

↓

Status `completed`, or on any failure: `failed` + short `error_message` + partial chunks deleted

---

## 4. Header and footer removal

A normalised line that appears at the top or bottom of at least **50% of pages** and on **3 or more pages** is removed before chunking. Documents with fewer than 3 pages are left untouched.

Why: a line such as "Synthetic document generated for RAG evaluation... Page 3" was part of every chunk and added noise to keyword search and snippets.

---

## 5. Retrieval changes that go with it

- The search filters directly on `DocumentChunk.organization_id` (defence in depth; no join needed for isolation).
- Only chunks of documents with `status = completed` are searched, so failed or in-progress documents never leak into answers.
- Deleting a document also deletes the file on disk (a missing file is ignored with a warning).

---

## 6. Results

- No chunk contains the old header text any more.
- Hit@5 stayed at 1.0 on the 28-question benchmark.
- Mean retrieval latency dropped from 3153 ms to 1726 ms on the same questions with cached embeddings. Caveat: the corpus was re-uploaded and cleaned at the same time as the indexes were added, so the gain cannot be attributed to indexes alone.
- Fused-only Hit@1 moved from 0.643 (old corpus) to 0.786 (cleaned corpus). The documents were re-uploaded, so this is not a perfectly controlled comparison.

---

## 7. Interview Questions

### Q1. Why check magic bytes?
The `Content-Type` header is controlled by the client; `%PDF-` is part of the file.

### Q2. How do you detect duplicate uploads?
SHA-256 of the file content with a unique partial index per organization; duplicates return 409.

### Q3. Why allow the same file in two organizations?
Tenants must be independent; one organization's upload must not block or reveal another's.

### Q4. What happens when processing fails halfway?
Status becomes `failed`, a short error message is stored, and partial chunks are deleted.

### Q5. Why Alembic instead of `create_all`?
It evolves existing databases safely and is reversible.

### Q6. What is `alembic stamp`?
It marks an existing database as being at a given revision without running that revision.

### Q7. Why a GIN index and an HNSW index?
GIN speeds up full-text search; HNSW speeds up approximate nearest-neighbour vector search.

### Q8. Why filter by `organization_id` on chunks directly?
Defence in depth for tenant isolation and fewer joins.