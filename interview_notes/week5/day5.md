# Week 5 - Day 5: Interview Notes: Memory Limits, ONNX Quantization and Free-Tier Engineering

## 1. The problem: out of memory on a free host

The free Render instance has **512 MB** RAM. The backend loaded PyTorch, sentence-transformers and the cross-encoder at startup. Logs showed:

```text
==> Out of memory (used over 512Mi)
==> No open ports detected
```

"No open ports" happened because the process was slow to start (importing torch and loading the model) and was killed before it started listening. A rough estimate (not measured): app libraries 150–250 MB, PyTorch and transformers 300–500 MB, model weights about 90 MB plus load-time copies, totalling roughly 600–900 MB.

---

## 2. Configurable reranker backend

`RERANKER_BACKEND` selects the implementation:

| Value | Behaviour |
|---|---|
| `local` | PyTorch cross-encoder (development and tests) |
| `voyage` | Voyage hosted rerank API |
| `onnx` | int8 ONNX model (default in the Docker image) |
| `none` | no reranking, fused order only |

Torch is imported only inside the `local` backend, lazily; a test checks in a subprocess that `torch` is not in `sys.modules` otherwise. Any rerank failure **fails open** to the fused order.

---

## 3. What the Voyage free tier really allows

Read from the provider's pricing and rate-limit pages:

- Without a payment method: **3 requests per minute and 10,000 tokens per minute**.
- Reranking 20 chunks is about 5,000+ tokens, so roughly one rerank per minute is possible.
- Free tokens apply to current models; the embedding model used here (`voyage-3-large`) is listed among older models without free tokens.

Effect: in one benchmark run about 26 of 28 rerank calls failed and fell back to the fused order, so that run's Hit@1 (0.821) mostly measured the fused order. Fail-open kept the system working but could have produced a wrong conclusion if the warnings had not been read.

---

## 4. Free solution: int8 ONNX reranker

- Same model: `cross-encoder/ms-marco-MiniLM-L-6-v2`, using the repository's quantized ONNX file (about 22 MB).
- ONNX Runtime on CPU, the Rust `tokenizers` library (max length 512), one intra-op thread.
- Lazy, thread-safe loading cached for the process lifetime.
- Model and tokenizer files are **downloaded at Docker build time** and baked into the image, so nothing is downloaded at runtime.

Quantization: weights are stored as 8-bit integers instead of 32-bit floats, making the model about four times smaller and faster on CPU with a small accuracy change. It was **measured**, not assumed:

- Spearman rank correlation with the PyTorch scores: **0.971** (10 questions × 20 pairs).
- Top-5 overlap: **100%**.
- Benchmark: Hit@1 0.929, MRR 0.958, identical to the PyTorch reranker.

| Backend | Hit@1 | Hit@3 | MRR |
|---|---|---|---|
| none (fused) | 0.786 | 0.964 | 0.878 |
| PyTorch | 0.929 | 1.0 | 0.958 |
| ONNX int8 | 0.929 | 1.0 | 0.958 |

Memory, measured with Docker: backend idle **171.6 MiB** of a 512 MiB limit; container **108.6 MiB** while reranking 20 chunks; rerank time **0.36 seconds**.

---

## 5. Free-tier-aware embeddings

- `VOYAGE_MIN_INTERVAL_SECONDS`: a process-wide lock keeps consecutive Voyage calls apart.
- `EMBED_BATCH_TOKENS` (default 6000): chunks are split into batches by estimated tokens (`len(text) / 3`) and embedded batch by batch.
- 429 responses: exponential backoff, up to 5 attempts, during ingestion.
- Query embedding: one retry after 5 seconds, then a clear 503 "Search is busy, please retry in a few seconds".
- Before this, larger PDFs failed because one embedding call exceeded the per-minute token limit.

---

## 6. Hosting options considered (as found in November 2026)

- Render free: 512 MB, sleeps after 15 minutes idle (cold start 30–60 seconds).
- Hugging Face Docker Spaces: creating them requires a paid plan.
- Google Cloud Run: free monthly allowance but needs a billing card; cold starts.
- Oracle Cloud Always Free: up to 24 GB RAM, but sign-up and capacity are difficult.
- Fly.io: no free tier for new accounts.

Because the target was zero cost and no card, the architecture was made small instead of buying more RAM.

---

## 7. Interview Questions

### Q1. Why did the service run out of memory?
PyTorch, transformers and the model together needed more than the 512 MB limit.

### Q2. Why did Render report "no open ports"?
Startup (importing torch and loading the model) was slow and the process was killed before listening.

### Q3. What is quantization?
Storing weights with fewer bits (int8 instead of float32) to shrink the model and speed up CPU inference.

### Q4. How do you know quantization did not hurt quality?
Spearman 0.971 versus PyTorch, 100% top-5 overlap, and identical benchmark metrics.

### Q5. Why ONNX Runtime?
It runs the model on CPU without PyTorch, with a small footprint.

### Q6. Why bake the model into the image?
No download at runtime, faster and more reliable cold starts.

### Q7. What does fail-open mean for the reranker?
If reranking fails, results are returned in fused order instead of returning an error.

### Q8. How did you handle the free embedding rate limit?
Token-based batching, pacing, retries with backoff, and a clear 503 for queries.

### Q9. What did you measure and what did you estimate?
Measured: the OOM log, 171.6 MiB idle, 108.6 MiB during rerank, 0.36 seconds, Spearman 0.971. Estimated: PyTorch's total memory of about 600–900 MB.