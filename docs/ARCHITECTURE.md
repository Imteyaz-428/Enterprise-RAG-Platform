# Enterprise RAG Platform Architecture

## Chat Pipeline Sequence

The chat and streaming pipeline coordinates retrieval-augmented generation across multiple isolated services with caching, hybrid retrieval, cross-encoder reranking, LLM provider fallback with rate-limit cooldown, and citation validation.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant Router as Chat Router (/chat, /chat/stream)
    participant Auth as Auth & RBAC Guard
    participant Service as ChatService
    participant Rewriter as Query Rewriter
    participant Cache as Redis Cache
    participant DB as PostgreSQL (pgvector + Relational)
    participant Retrieval as Hybrid Retrieval Service
    participant Reranker as Cross-Encoder Reranker
    participant AI as AIService (Multi-Provider Fallback)
    participant Validator as Citation Validator

    User->>Router: POST /chat or /chat/stream {question, session_id}
    Router->>Auth: Validate JWT & Tenant Organization Scope
    Auth-->>Router: Authenticated (user_id, organization_id, role)
    Router->>Service: chat(db, session_id, user_id, organization_id, question)

    Service->>DB: Fetch Recent Conversation History
    DB-->>Service: History Messages
    Service->>Rewriter: rewrite_query(history, question)
    Rewriter-->>Service: Standalone Question

    Service->>DB: Persist User Message (Original Question)

    Service->>Cache: GET cache:org_{id}:{standalone_question_hash}
    alt Cache Hit
        Cache-->>Service: Cached Answer & Citations
        Service->>DB: Persist Assistant Response
        Service-->>Router: Return Cached Response
        Router-->>User: 200 OK (Instant Response)
    else Cache Miss
        Cache-->>Service: None / Miss

        Service->>Retrieval: retrieve(standalone_question, org_id)
        par Dense Vector Search
            Retrieval->>AI: Generate Query Embedding (Voyage AI)
            AI-->>Retrieval: Dense Vector (1024-dim)
            Retrieval->>DB: Cosine Similarity on document_chunks (pgvector)
            DB-->>Retrieval: Top Dense Candidates
        and Sparse BM25 / Trigram Search
            Retrieval->>DB: Text Search on chunk_text & title (Postgres)
            DB-->>Retrieval: Top Sparse Candidates
        end
        Retrieval->>Retrieval: Reciprocal Rank Fusion (RRF)
        Retrieval->>Reranker: rerank(standalone_question, fused_candidates)
        Reranker-->>Retrieval: Scored & Ordered Chunks
        Retrieval-->>Service: Top Filtered Chunks with Metadata

        Service->>Service: Build Prompt with Numbered Sources [1], [2]...

        loop Try Providers (Gemini -> Groq -> DeepSeek)
            Service->>AI: generate_answer(prompt) / stream_answer(prompt)
            alt Active Provider Success
                AI-->>Service: Generated LLM Answer / Tokens
            else Rate Limit / Quota Exceeded (429)
                AI->>AI: Parse Retry Delay & Set Thread-Safe In-Memory Cooldown
                AI->>AI: Fail Over to Next Provider Immediately
            else Transient Error (503 / Timeout)
                AI->>AI: Exponential Backoff Retry (Tenacity)
            end
        end

        Service->>Validator: validate_citations(answer, citations, chunk_texts)
        Validator->>Validator: Verify [N] markers, strip hallucinated citations
        Validator-->>Service: clean_answer, used_citations

        Service->>DB: Persist Assistant Message (clean_answer, used_citations)
        Service->>Cache: SETEX cache:org_{id}:{hash} (TTL 3600s)
        Service-->>Router: Response (session_id, clean_answer, used_citations)
        Router-->>User: 200 OK / SSE Stream
    end
```

---

## Benchmark Evaluation Results

The following evaluation metrics are taken directly from [`backend/eval/results/summary.csv`](../backend/eval/results/summary.csv) across iterative optimization phases (dense vector retrieval, BM25 sparse keyword fusion, cross-encoder reranking, and conversational query rewriting):

| Timestamp / Label | Run Configuration | Total Queries | Failed | Hit@1 | Hit@3 | Hit@5 | MRR | Page Match | Dup Rate | Avg Latency (ms) | P95 Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `baseline` | Initial Vector Baseline | 8 | 0 | 0.875 | 1.000 | 1.000 | 0.9375 | 0.000 | 0.000 | — | — |
| `stage3-candidates` | Stage 3 Initial Baseline | 8 | 0 | 0.875 | 1.000 | 1.000 | 0.9375 | 0.000 | 0.000 | — | — |
| `2026-11-15T18:22:07` | `no-rerank` | 5 | 0 | 1.000 | 1.000 | 1.000 | 1.0000 | 1.000 | 0.000 | 4646.2 | 4646.2 |
| `2026-11-15T21:28:41` | `baseline` | 5 | 0 | 0.800 | 1.000 | 1.000 | 0.9000 | 1.000 | 0.000 | 17913.9 | 22229.8 |
| `2026-11-15T21:41:02` | `baseline-os` | 5 | 0 | 0.800 | 1.000 | 1.000 | 0.9000 | 1.000 | 0.000 | 2566.9 | 4252.2 |
| `2026-11-15T21:45:51` | `clean-baseline-os` | 5 | 0 | 0.800 | 1.000 | 1.000 | 0.9000 | 1.000 | 0.000 | 3033.4 | 4217.6 |
| `2026-11-15T21:46:34` | `no-rerank` | 5 | 0 | 0.800 | 1.000 | 1.000 | 0.9000 | 1.000 | 0.000 | 3475.8 | 6015.3 |
| `2026-11-15T22:02:17` | `rerank20` | 28 | 0 | 0.929 | 1.000 | 1.000 | 0.9640 | 1.000 | 0.000 | 20437.0 | 23383.2 |
| `2026-11-15T22:03:53` | `fused-only` | 28 | 0 | 0.643 | 0.964 | 1.000 | 0.8050 | 1.000 | 0.000 | 2915.7 | 3661.3 |
| `2026-11-15T22:08:16` | `rerank20-cached` | 28 | 0 | 0.929 | 1.000 | 1.000 | 0.9640 | 1.000 | 0.000 | 3152.7 | 4994.0 |
| `2026-11-15T22:19:55` | `followups-baseline` | 8 | 0 | 0.625 | 0.875 | 0.875 | 0.7290 | 1.000 | 0.000 | 19271.0 | 23030.6 |
| `2026-11-15T22:26:21` | `followups-rewrite` | 8 | 0 | 0.750 | 1.000 | 1.000 | 0.8540 | 1.000 | 0.000 | 19739.4 | 28538.0 |
| `2026-11-15T22:30:14` | `rerank20-after-2-3` | 28 | 0 | 0.929 | 1.000 | 1.000 | 0.9640 | 1.000 | 0.000 | 4832.8 | 16727.0 |
| `2026-11-15T22:48:11` | `followups-rewrite-11` | 11 | 0 | 0.636 | 0.909 | 1.000 | 0.7610 | 1.000 | 0.000 | 18481.5 | 23502.2 |
| `2026-11-15T23:01:16` | `followups-rewrite-11b` | 11 | 0 | 0.636 | 0.818 | 0.909 | 0.7300 | 1.000 | 0.000 | 11028.7 | 21535.5 |
| `2026-11-16T23:06:22` | `followups-rewrite-11c-a` | 11 | 0 | 0.636 | 0.818 | 1.000 | 0.7530 | 1.000 | 0.000 | 12163.8 | 21937.0 |
| `2026-11-16T23:08:20` | `followups-rewrite-11c-b` | 11 | 0 | 0.455 | 0.818 | 1.000 | 0.6470 | 1.000 | 0.000 | 7112.1 | 17983.0 |
| `2026-11-21T18:57:33` | `after-2-5` | 28 | 0 | 0.929 | 1.000 | 1.000 | 0.9580 | 1.000 | 0.000 | 1725.5 | 3740.8 |
| `2026-11-21T18:59:52` | `followups-after-2-5` | 11 | 0 | 0.727 | 0.818 | 0.909 | 0.7800 | 1.000 | 0.000 | 11322.6 | 22355.2 |

### Key Benchmark Insights
- **Cross-Encoder Reranking (`rerank20`)**: Dramatically elevated `Hit@1` from `0.643` (fused-only) to `0.929` and `MRR` from `0.805` to `0.964` across 28 evaluation queries.
- **Query Rewriting (`followups-after-2-5`)**: Conversational contextual rewriting improved followup resolution, achieving `0.727` Hit@1 and `0.909` Hit@5 on multi-turn dialogue benchmarks.
- **Latency Optimization**: Caching with RRF and warm embeddings dropped end-to-end P95 retrieval latency from `23,383 ms` down to `3,740.8 ms` in `after-2-5`.
