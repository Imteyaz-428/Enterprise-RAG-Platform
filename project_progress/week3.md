# Week 3 - Day 1: Source Citations

## Completed

- Added source citation support to RAG responses.
- Created `RetrievalResult` dataclass to carry chunk, document, and similarity score.
- Updated `RetrievalService` to return structured retrieval results.
- Modified `PromptService` to build context using `RetrievalResult`.
- Updated `ChatService` to generate citations from retrieved document metadata.
- Added `CitationResponse` schema to the chat API.
- Chat API now returns both the AI answer and corresponding source citations.
- Tested citation generation with single and multiple document retrieval.

## Current Status

- ✅ Enterprise RAG chat with conversation history
- ✅ Semantic search using pgvector
- ✅ Multi-provider LLM fallback
- ✅ Source citations


# Week 3 - Day 2: Streaming AI Responses

## Completed

- Added streaming support to all AI providers (Groq, Gemini, DeepSeek).
- Extended `BaseProvider` with a `stream()` method.
- Refactored `AIService` to support both normal and streaming responses.
- Added `stream_answer()` with provider fallback support.
- Refactored `ChatService` using `_prepare_chat()` to reduce duplicate code.
- Implemented `chat_stream()` for real-time response streaming.
- Streamed source citations and session metadata using Server-Sent Events (SSE).
- Added `/chat/stream` endpoint using FastAPI `StreamingResponse`.
- Successfully tested end-to-end streaming with Groq.

## Current Status

- Multi-provider AI with retry & fallback
- Enterprise RAG Chat
- Source Citations
- Real-time Streaming Responses (SSE)
```


# Week 3 - Day 3: Redis Caching

## Completed

- Installed and configured Redis.
- Ran Redis using Docker.
- Created `RedisService` for Redis operations.
- Added `get()`, `set()`, and `delete()` methods.
- Integrated Redis into `ChatService`.
- Implemented cache key generation using SHA-256.
- Cached normal chat responses.
- Cached streaming chat responses.
- Added Redis cache hit/miss logging.
- Successfully tested Redis caching.

## Current Status

- Enterprise RAG Chat
- Source Citations
- Streaming AI Responses
- Redis Caching


# Week 3 - Day 4: Background Tasks

## Completed

- Implemented FastAPI Background Tasks.
- Moved document processing to a separate background service.
- Created a separate database session using `SessionLocal`.
- Added document processing status.
- Status values:
  - processing
  - completed
  - failed
- Updated document status after processing.
- Added error handling and logging.
- Created API to get document details and status.
- Successfully tested background processing.

## Current Status

- Background document processing
- Document status tracking
- Ready for frontend polling

# Day 4 - Dockerization

## Completed

- Added Docker support for the FastAPI backend.
- Created a Dockerfile for the application.
- Created docker-compose.yml.
- Containerized:
  - FastAPI
  - PostgreSQL (pgvector)
  - Redis
- Configured environment variables using `.env`.
- Mounted project files using Docker volumes.
- Exposed backend on port 8000.
- Added PostgreSQL health check.
- Added Redis health check.
- Successfully built Docker image.
- Successfully ran the complete application using Docker Compose.
- Verified all APIs work correctly inside Docker.