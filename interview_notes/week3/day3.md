# Week 3 - Day 3 Interview Notes: Redis Caching

## What is Redis?

Redis is an in-memory key-value database used for caching, session storage, and fast data retrieval.

---

## Why Redis?

- Faster than querying the database or calling the AI model.
- Reduces response time.
- Reduces AI API usage.
- Improves scalability.

---

## What is Caching?

Caching stores frequently used data so future requests can be served quickly without recomputing the result.

---

## Cache Hit

The requested data is already available in Redis.

Flow:

User
↓
Redis
↓
Return Cached Response

---

## Cache Miss

The requested data is not available.

Flow:

User
↓
Redis
↓
RAG Pipeline
↓
LLM
↓
Store in Redis
↓
Return Response

---

## What Did We Cache?

- AI Answer
- Source Citations

---

## What Did We Not Cache?

- Chat History
- Documents
- Embeddings
- Vector Search Results

---

## Why Use SHA-256 for Cache Keys?

- Generates fixed-length keys.
- Avoids storing long questions as Redis keys.
- Reduces key collisions.

---

## Why Create RedisService?

- Keeps Redis logic separate from business logic.
- Makes the code reusable and easier to maintain.

---

## Cache Flow

User
↓
Create Chat Session
↓
Save User Message
↓
Check Redis
↓
Cache Hit?
├── Yes → Return Cached Response
└── No → Run RAG → Save in Redis → Return Response

---

## Cache Invalidation

Problem:
- After uploading a new document, cached responses may become outdated.

Simple Solution:
- Clear Redis after successful document upload.

---

## Interview Questions

### Q1. What is Redis?
An in-memory key-value database used for caching and fast data retrieval.

### Q2. Why did you use Redis?
To reduce repeated AI calls, improve response time, and lower API costs.

### Q3. What is a Cache Hit?
The requested data is already available in Redis.

### Q4. What is a Cache Miss?
The requested data is not available, so the system generates it and stores it in Redis.

### Q5. Why generate cache keys?
To uniquely identify cached responses for each organization and question.

### Q6. Why use SHA-256?
To create fixed-length unique cache keys.

### Q7. Why not cache everything?
Only AI responses benefit significantly from caching. Chat history and documents change frequently and are better retrieved from the database.

### Q8. What is cache invalidation?
Removing outdated cached data after the underlying knowledge base changes.

### Q9. What did you implement?
- Redis integration
- Redis service
- Cache key generation
- Chat response caching
- Streaming response caching
- Cache hit/miss logging