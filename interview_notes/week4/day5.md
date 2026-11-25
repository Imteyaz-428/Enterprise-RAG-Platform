# Week 4 - Day 5: Interview Notes: Query Rewriting and Conversation History

## 1. The problem

Follow-up questions such as "What is its retention rate?" or "What if it is doubled?" contain no topic words. Retrieval based on the raw question returns weak or unrelated chunks.

Baseline on 8 multi-turn questions (no rewriting): Hit@1 0.625, Hit@5 0.875, MRR 0.729. One question retrieved a chunk from a completely different document.

---

## 2. The solution: standalone question rewriting

`rewrite_query(history, question)`:

- If the history is empty, return the question unchanged and make **no LLM call**.
- Otherwise use the last **4 messages**, each truncated to **500 characters**.
- Ask an LLM for one standalone question (under 40 words) that resolves pronouns and references, without answering it.
- Clean the output (strip quotes, newlines, label prefixes; cap at 300 characters).
- On any failure return the original question (it never raises).

The rewritten question is used for **retrieval and the cache key**. The user's original question is what is saved and shown in the final prompt.

---

## 3. Why the cache key must use the rewritten question

Before: key = organization + raw question. Two different follow-ups with the same words in different conversations could return another conversation's cached answer.

After: key = `cache:{org_id}:{sha256(standalone question)}`. The organization id remains in the key, so tenants never share cached answers.

---

## 4. Results (8 multi-turn questions)

| | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Raw follow-up | 0.625 | 0.875 | 0.875 | 0.729 |
| With rewriting | 0.75 | 1.0 | 1.0 | 0.854 |

Example: "What if it is doubled?" became a question about the token budget, and the correct chunk was found.

---

## 5. Hardening the rewriter

- **Timeout**: 5 seconds, one attempt per provider, at most one fallback provider. A rewrite must not be slower than the main answer.
- **Prompt rule**: "If the follow-up question already makes sense on its own, return it exactly as written." Three topic-switch tests check that independent questions are not polluted with the old topic.
- **Output guard**: in one run the LLM rewrote an unrelated finance question into a question about medical side effects. Guard added:
  1. Extract content words (stopwords removed) from the original question.
  2. At least half must appear in the rewrite (5-character prefix matching handles inflections).
  3. Otherwise use the original question and log a warning.

The guard works even when the cause is an external model anomaly. The anomaly appeared once and did not reproduce in 20 repeated calls.

---

## 6. Noise and free-tier effects

- LLM rewrites differ between runs, so Hit@1 on 11 questions varied from 0.455 to 0.727. Hit@5 stayed at 0.91 to 1.0.
- Gemini's free quota was exhausted, so rewrites were made by Groq. Different providers phrase questions differently, which also moves the numbers.
- A cache of rewrite results would make comparisons deterministic (listed as a next step).

---

## 7. Interview Questions

### Q1. Why rewrite follow-up questions?
Retrieval needs a self-contained question; follow-ups lack the topic words.

### Q2. When is the LLM not called?
When there is no conversation history.

### Q3. Why use the rewritten question for the cache key?
So two follow-ups that mean the same thing share an entry, and different conversations do not collide.

### Q4. How do you protect against a bad rewrite?
A content-word overlap guard falls back to the original question, plus a 5 second timeout and failure fallback.

### Q5. How did you prove it helps?
Hit@5 improved from 87.5% to 100% on 8 multi-turn questions, with topic-switch tests to prove it does not hurt independent questions.

### Q6. What is the limitation?
Small sample and LLM variance; results are quoted with the sample size.

### Q7. Why keep the original question in the saved message?
The conversation history must show what the user actually typed.