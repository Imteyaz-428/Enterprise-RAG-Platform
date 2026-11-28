# Week 6 - Day 3: Interview Notes: Final Metrics, War Stories and How to Present the Project

## 1. Metrics master table

| Claim | Before | After | Notes |
|---|---|---|---|
| Hit@1 (retrieval) | 78.6% (fused only, cleaned corpus) | **92.9%** | 28 questions, with reranker |
| MRR | 0.878 | **0.958** | same |
| Hit@1 including ingestion cleanup | 64.3% (original corpus) | 92.9% | corpus was re-uploaded, not a perfectly controlled comparison |
| Follow-up Hit@5 | 87.5% | **100%** | 8 questions; rewriting |
| Follow-up Hit@1 | 62.5% | 75% | 8 questions; 11-question runs varied from 0.455 to 0.727 |
| Correct "not found" answers | - | **33 / 33** | 24 trap trials + 9 unanswerable trials |
| False refusals | - | **0 / 28** | answerable questions |
| Answers with citations | - | 28 / 28 | |
| Mean retrieval latency | 3.15 s | 1.73 s | cached embeddings; indexes and cleanup changed together |
| Backend memory (idle) | out of memory at 512 MB (PyTorch) | **171.6 MiB** | Docker stats |
| Reranker | PyTorch + sentence-transformers | 22 MB int8 ONNX | Spearman 0.971, top-5 overlap 100% |
| Rerank time (20 chunks) | - | 0.36 s | measured in the container |
| Tests | 105 | **211 backend** + frontend vitest | pytest, vitest |

Say "on my evaluation set". Do not say "93% accuracy", "production-ready" or "enterprise-grade".

---

## 2. Honesty notes

- The benchmark is small (28 and 8 questions) and uses two synthetic documents plus a university lab document; questions were written by me.
- Hit@K is a retrieval metric, not answer correctness.
- The original pipeline (which reranked 5 into 5) was never run on the final dataset, so the Hit@1 gain is "with the reranker versus without it".
- The 33 of 33 figure counts trials of a stochastic model; one extra scope rule's effect was not isolated.
- Memory figures are measured; the PyTorch footprint figure is an estimate.
- Follow-up numbers move between runs because the LLM wording changes.
- Free tier limits: Voyage 3 requests per minute without billing, Gemini 20 requests per day, Render cold starts, ephemeral disk (uploaded files disappear on redeploy; chunks stay in the database).

---

## 3. War stories (symptom, cause, fix, lesson)

1. **All questions were dataset errors.** Documents were in a different organization/database than the benchmark used. Lesson: verify the data first.
2. **Rate-limited ingestion.** Large PDFs failed on a 3 requests per minute limit. Fix: token-bounded batching, pacing and backoff.
3. **Reranker re-ordered only 5 chunks.** Candidates equal to top-k. Fix: 20 candidates.
4. **Rewriter hallucination.** A finance question became a medical question once. Fix: content-word overlap guard.
5. **Instruction leaked into the answer.** Two conflicting prompt rules. Fix: one rule and answer normalisation. The benchmark had hidden it because the validator only checked the start of the string.
6. **Number check passed a wrong answer** (FY2026 revenue). Fix: scope rule, trap questions; the lesson is that grounding checks are not faithfulness checks.
7. **Fail-open hid a measurement problem.** Voyage rerank calls failed quietly; the run looked like "reranking did not help". Lesson: read the warnings.
8. **Out of memory on Render.** PyTorch → int8 ONNX, proven with `docker run --memory=512m`.
9. **Startup crashes from environment variables.** `REDIS_EXPIRE=3600s`, short `SECRET_KEY`.
10. **CI failed only in CI.** Import-time client needing a key; secrets and model files missing; "re-run" runs the old commit.
11. **Repository hygiene.** Committed archive with `.env`, ignore patterns, tracked `node_modules`, symlink.
12. **Frontend bugs.** Wrong `setUser`, trimmed tokens, missing error event, blank page, object rendered as React child.
13. **Trusting reports.** An agent's claim that a prompt rule fixed a hallucination was not supported by its own "before" run, and one of my own guesses (a chunk lacked a figure) was wrong because of chunk overlap. Lesson: verify with data and admit mistakes.

---

## 4. How an AI coding agent was used

An agentic IDE was used to implement scoped tasks. The working method:

- One task per branch with explicit acceptance criteria.
- Every task ended with tests and, for retrieval changes, the same benchmark before and after.
- Diffs of security-sensitive files (authentication, embedding client, chat service) were reviewed by hand.
- Reports were checked against raw outputs.
- I can explain each design decision and result in this document.

If asked: "AI helped with implementation speed; evaluation design, trade-offs and verification were my responsibility."

---

## 5. Resume bullets

- Built a multi-tenant document Q&A platform (FastAPI, PostgreSQL/pgvector, Redis, React) with hybrid retrieval (vector + full-text, RRF) and a cross-encoder reranker, raising Hit@1 from 78.6% to 92.9% (MRR 0.88 → 0.96) on a 28-question evaluation set.
- Added LLM query rewriting for follow-up questions (Hit@5 87.5% → 100%) and a citation validator with page-level sources; 33/33 correct "not found" answers on unanswerable questions with 0 false refusals on 28 answerable ones.
- Cut backend memory to about 170 MiB by replacing PyTorch with a 22 MB int8 ONNX reranker at the same accuracy, enabling free-tier deployment (Render, Neon, Vercel); Gemini → Groq → DeepSeek LLM fallback.
- Implemented hierarchical RBAC, JWT refresh tokens, organization-level data isolation, Alembic migrations and a React UI with SSE streaming and clickable citations; 210+ tests, Docker and GitHub Actions CI.

---

## 6. Interview Questions

### Q1. What is the best result you can claim?
Hit@1 improved from 78.6% to 92.9% with reranking on a 28-question set, with equal accuracy after moving to a 22 MB int8 model.

### Q2. What is the biggest weakness of your evaluation?
Small sample, synthetic documents, author-written questions.

### Q3. Which story shows engineering judgment?
Moving from PyTorch to int8 ONNX under a 512 MB constraint, with measured parity.

### Q4. Which story shows you question your own results?
The fail-open reranker run and the unproven scope-rule effect.

### Q5. How do you describe your use of AI tools?
As an accelerator with strict review: tests, benchmarks, diffs and verification were mine.