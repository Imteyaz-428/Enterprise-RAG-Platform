# Week 3 - Day 1: Concepts Learned

## 1. Source Citations in RAG
- Source citations show the document and chunk used to generate an AI response.
- They improve transparency and allow users to verify AI-generated answers.

## 2. Why Citations Matter
- Increase user trust.
- Reduce hallucinations by grounding responses in retrieved documents.
- Common feature in enterprise AI systems.

## 3. Retrieval Metadata
- Each retrieved chunk contains:
  - Chunk text
  - Document metadata
  - Similarity score
- Metadata flows through the RAG pipeline and is used to generate citations.

## 4. RetrievalResult
- Introduced `RetrievalResult` to replace anonymous tuples.
- Improves readability, type safety, and maintainability.

## 5. Separation of Responsibilities
- **CRUD:** Retrieves data from the database.
- **RetrievalService:** Performs semantic search.
- **PromptService:** Builds the LLM prompt.
- **AIService:** Generates the final answer.
- **ChatService:** Orchestrates the workflow and prepares the API response.

## 6. Backend-Generated Citations
- Citations are generated in the backend instead of by the LLM.
- Prevents hallucinated document names and ensures citations always match retrieved chunks.

## 7. Enterprise RAG Flow

User Question
→ Generate Query Embedding
→ Vector Search (pgvector)
→ Retrieve Relevant Chunks
→ Build Prompt
→ LLM
→ Generate Answer
→ Attach Source Citations
→ Return Response


# Week 3 - Day 2: Streaming AI Responses

## Concepts Learned

### 1. Streaming Responses
- Streaming sends the AI response in small chunks instead of waiting for the complete answer.
- It improves user experience by reducing perceived latency.

### 2. Server-Sent Events (SSE)
- SSE is a one-way communication protocol where the server continuously sends data to the client over a single HTTP connection.
- Used `text/event-stream` as the response content type.
- Streamed three event types:
  - `metadata`
  - `token`
  - `done`

### 3. FastAPI StreamingResponse
- `StreamingResponse` allows FastAPI to send data as it is generated.
- It works with Python generators that use `yield`.

### 4. Python Generators
- Learned the difference between `return` and `yield`.
- Used generators to stream AI tokens one by one.

### 5. Provider Pattern Extension
- Extended the `BaseProvider` interface by adding a `stream()` method.
- Implemented streaming in Groq, Gemini, and DeepSeek providers while keeping `generate()` unchanged.

### 6. AI Service Refactoring
- Replaced provider-specific execution with a generic `_execute_with_fallback()` method.
- Reused the same retry and fallback mechanism for both normal and streaming responses.

### 7. Chat Service Refactoring
- Created `_prepare_chat()` to remove duplicate logic.
- Shared the same preparation flow between `chat()` and `chat_stream()`.

### 8. Token Accumulation
- Streamed tokens to the client while collecting them in memory.
- Saved the complete assistant response to the database only after streaming finished.

### 9. Streaming Metadata
- Sent chat session information and source citations before AI tokens.
- This allows the frontend to receive required metadata immediately.

### 10. Production Streaming Architecture
- Built a streaming pipeline:
  - Client
  - FastAPI Router
  - ChatService
  - AIService
  - AI Provider (Groq/Gemini/DeepSeek)
  - StreamingResponse
  - Frontend

## Interview Takeaways

- Difference between normal API responses and streaming responses.
- Why SSE is preferred over WebSockets for AI response streaming.
- Why `yield` is used instead of `return`.
- Benefits of `StreamingResponse` in FastAPI.
- Why providers expose both `generate()` and `stream()` methods.
- Why common logic was moved to `_prepare_chat()` and `_execute_with_fallback()`.
- Why the complete response is stored only after streaming completes.
```

# Week 3 - Day 3: Redis Caching

## Concepts Learned

### 1. What is Redis?
- Redis is an in-memory key-value database.
- It is mainly used for caching and fast data access.

### 2. Why Use Redis?
- Reduces repeated AI calls.
- Improves response time.
- Reduces API cost.
- Improves user experience.

### 3. Cache Hit
- Data is found in Redis.
- Return the cached response without calling the AI model.

### 4. Cache Miss
- Data is not found in Redis.
- Generate a new response using the RAG pipeline.
- Store the response in Redis.

### 5. Cache Key
- Created a unique cache key using:
  - Organization ID
  - User Question
- Used SHA-256 hashing to generate a fixed-length key.

### 6. Redis Service
Created a reusable Redis service with:
- get()
- set()
- delete()

### 7. Chat Response Caching
Cached:
- AI Answer
- Source Citations

Did not cache:
- Chat History
- Embeddings
- Documents

### 8. Streaming Cache
- Added Redis support to both normal chat and streaming chat.
- Cached responses can also be streamed to the frontend.

### 9. Cache Invalidation
- Learned that cached data becomes outdated after new document uploads.
- Simple solution: clear Redis after document upload.