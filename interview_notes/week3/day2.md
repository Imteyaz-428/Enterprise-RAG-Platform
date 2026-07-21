# Week 3 - Day 2 Interview Notes: Streaming AI Responses

## 1. What is Streaming?

Streaming is a technique where the server sends the response to the client in small chunks as soon as they are generated, instead of waiting for the complete response.

Example:
- Normal Response: Wait 5–10 seconds, then receive the entire answer.
- Streaming Response: Receive the first token immediately, followed by the remaining tokens in real time.

---

## 2. Why is Streaming Used?

- Improves user experience.
- Reduces perceived latency.
- Makes AI applications feel faster.
- Used by ChatGPT, Claude, Gemini, and Perplexity.

---

## 3. What is Server-Sent Events (SSE)?

Server-Sent Events (SSE) is an HTTP-based protocol where:
- Client sends one request.
- Server keeps the connection open.
- Server continuously streams data.
- Client receives updates in real time.

Content-Type:

```http
text/event-stream
```

---

## 4. Why SSE Instead of WebSockets?

SSE:
- One-way communication (Server → Client).
- Simpler implementation.
- Ideal for AI response streaming.

WebSockets:
- Two-way communication.
- Suitable for chat applications, games, and collaborative editing.

For AI-generated responses, SSE is sufficient because only the server streams data after receiving the user's request.

---

## 5. What is StreamingResponse in FastAPI?

`StreamingResponse` allows FastAPI to send data continuously instead of waiting for the entire response.

Example Flow:

Client
↓
Router
↓
StreamingResponse
↓
Generator
↓
Client receives tokens continuously

---

## 6. Difference Between return and yield

return:
- Ends the function.
- Returns a single value.

yield:
- Pauses the function.
- Returns one value at a time.
- Continues execution when called again.

Streaming uses `yield` to send each token immediately.

---

## 7. Why Add stream() Instead of Modifying generate()?

To keep backward compatibility.

Current APIs continue using:

```python
generate()
```

Streaming APIs use:

```python
stream()
```

This follows the Open/Closed Principle by extending functionality without breaking existing code.

---

## 8. Provider Pattern for Streaming

BaseProvider exposes two methods:

```python
generate(prompt)
stream(prompt)
```

Implemented in:
- GroqProvider
- GeminiProvider
- DeepSeekProvider

This ensures every provider supports both normal and streaming responses.

---

## 9. AIService Changes

Refactored provider execution into:

```python
_execute_with_fallback()
```

Used by:

```python
generate_answer()
stream_answer()
```

Benefits:
- No duplicate retry logic.
- Same fallback mechanism for all providers.
- Easy to add future AI providers.

---

## 10. Why _prepare_chat()?

Both `chat()` and `chat_stream()` shared the same logic:

- Create/Get session
- Save user message
- Load history
- Retrieve document chunks
- Build prompt
- Generate citations

Moving this into `_prepare_chat()` removed duplicate code and improved maintainability.

---

## 11. Why Save the Assistant Message After Streaming?

Streaming sends tokens one by one.

Saving each token separately would create hundreds of database rows.

Instead:
- Collect all streamed tokens.
- Join them into one response.
- Save a single assistant message after streaming completes.

---

## 12. SSE Event Structure

Three events are streamed:

Metadata:

```text
event: metadata
data: {
    "session_id": 1,
    "citations": [...]
}
```

Token:

```text
event: token
data: Hello
```

Done:

```text
event: done
data: {}
```

---

## 13. Complete Streaming Flow

User
↓
POST /chat/stream
↓
Router
↓
ChatService
↓
_prepare_chat()
↓
AIService.stream_answer()
↓
Provider.stream()
↓
StreamingResponse
↓
Frontend receives tokens in real time

---

## 14. Advantages of Streaming

- Faster perceived response.
- Better user experience.
- Lower waiting time.
- Modern AI application behavior.
- Real-time token generation.

---

## 15. Interview Questions

### Q1. What is response streaming?
Streaming sends data continuously instead of waiting for the complete response.

### Q2. Why use StreamingResponse?
To send AI-generated tokens to the client as soon as they are generated.

### Q3. Why use yield?
Because it produces values one at a time without ending the function.

### Q4. Why use SSE?
SSE is lightweight, HTTP-based, and ideal for one-way AI response streaming.

### Q5. Why not WebSockets?
WebSockets are designed for two-way communication, while AI streaming only requires server-to-client communication.

### Q6. Why implement stream() in every provider?
To maintain a consistent provider interface and ensure retry/fallback works regardless of which provider is active.

### Q7. Why refactor into _execute_with_fallback()?
To reuse the same retry and fallback logic for both `generate()` and `stream()`.

### Q8. Why create _prepare_chat()?
To remove duplicate business logic shared between normal and streaming chat flows.

### Q9. Why save the response after streaming completes?
To store one complete assistant message instead of saving each streamed token separately.

### Q10. What was implemented today?
- Added streaming support to all AI providers.
- Implemented provider fallback for streaming.
- Added StreamingResponse with SSE.
- Refactored ChatService to remove duplicate code.
- Added `/chat/stream` endpoint.
- Successfully tested end-to-end streaming.