# Week 4 - Day 2: Interview Notes: Provider Fallback Hardening and the Streaming Contract

## 1. Provider fallback chain

Order: **Gemini 2.5 Flash → Groq → DeepSeek**, for both normal generation and streaming.

Rules implemented in `AIService._execute_with_fallback()`:

- Uniform **30 second** HTTP timeouts for every provider.
- **Transient errors** (429 rate limit, 503, timeouts): retry with exponential backoff.
- **Permanent errors** (401 auth, 402 billing): fail fast and move to the next provider.
- **Secret redaction**: API keys and bearer tokens in logs are replaced with `[REDACTED]`.
- When every provider fails, `AIProviderError` is raised and mapped to HTTP 503.

Tests: 12 unit tests plus live verification scripts.

---

## 2. Mid-stream integrity rule

Providers may be switched only **before the first token** is emitted. After token 1, the provider is committed.

Why: if a provider fails halfway and a second provider continues, the user would see mixed text from two models. A clean termination (error event) is better.

---

## 3. Provider cooldown (added later)

Problem: the Gemini free tier allows only about 20 requests per day. After that, every request wasted 1–2 seconds failing on Gemini before reaching Groq.

Fix:

- On a rate-limit or quota error, the provider is skipped for a cooldown.
- The cooldown uses the retry delay from the error when it can be parsed, capped at 15 minutes; otherwise 60 seconds.
- State is in memory and thread-safe; a fake clock is injectable for tests.
- If all providers are cooling down, they are still tried in order (never return nothing without trying).

`retry_request` gained optional `max_attempts` and `retry_predicate` parameters so quota errors can bypass retries and switch providers immediately, while normal calls behave exactly as before.

---

## 4. The SSE contract

Success:

event: metadata → event: token (repeated) → event: done

Failure:

event: metadata → event: error → event: done (no tokens after an error)

Example events:

```text
event: metadata
data: {"session_id": 2, "citations": [ ... ]}

event: token
data: Hello

event: done
data: {}
```

---

## 5. Streaming setup errors

Problem: in `chat_stream()` the helper `_prepare_chat()` (session, embedding, retrieval, reranking) ran lazily inside the generator. Once a `StreamingResponse` has started, the 200 status is already sent, so an exception there produced a broken stream with no explanation (and an `HTTPException` cannot change the status anymore).

Fix: wrap setup in try/except inside the generator and emit `event: error` followed by `event: done`.

---

## 6. SSE framing for newline tokens

Problem: an SSE event ends at a blank line. A token that contains `\n` (very common in markdown answers) broke the event and lost the newline.

Fix: follow the SSE specification. Split the token on `\n` and emit one `data:` line per piece. The client joins the `data:` lines with `\n`.

Examples:

- Token `a\nb` → `event: token\ndata: a\ndata: b\n\n`
- Tokens without a newline are byte-for-byte identical to before.

A helper `format_sse_event(event, data)` is used for live tokens, cached tokens and error events. Tests include a round trip through a spec-compliant parser.

---

## 7. Interview Questions

### Q1. Why switch providers only before the first token?
Switching after output has started would mix text from different models.

### Q2. Which errors are retried and which are not?
Transient errors (429, 503, timeouts) are retried with backoff. Permanent errors (401, 402) go straight to the next provider.

### Q3. Why add a provider cooldown?
To avoid wasting time on a provider that has already told us its quota is exhausted.

### Q4. Why can an exception inside a streaming generator not change the HTTP status?
Because the status line and headers are sent when streaming starts. Errors must be sent as events in the stream.

### Q5. What is the SSE rule for multi-line data?
Each line is sent as its own `data:` field. The client joins them with newline characters.

### Q6. Why are API keys redacted in logs?
Provider error messages can contain keys or bearer tokens. Logs are often shared.

### Q7. Why keep `generate()` and `stream()` behind the same fallback logic?
One tested implementation of retries and fallback is easier to maintain and avoids inconsistent behaviour.