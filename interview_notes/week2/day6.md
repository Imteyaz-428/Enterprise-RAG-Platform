# Week 2 - Day 6 (Interview Notes)

## 📅 Date
18 July 2026

---

# 1. What is Retrieval-Augmented Generation (RAG)?

### Answer

RAG is an AI architecture that combines semantic retrieval with a Large Language Model.

Instead of relying only on the model's pretrained knowledge, it first retrieves relevant information from external documents and then provides that information as context to the LLM before generating the answer.

---

# 2. Explain the complete RAG pipeline.

### Answer

```
User Question
      ↓
Generate Query Embedding
      ↓
Vector Similarity Search
      ↓
Retrieve Top-K Chunks
      ↓
Prompt Builder
      ↓
LLM
      ↓
Final Answer
```

This allows the model to answer using document-specific information.

---

# 3. Why do we generate embeddings?

### Answer

Embeddings convert text into dense numerical vectors.

These vectors capture semantic meaning, allowing similar texts to have similar vector representations.

They make semantic search possible.

---

# 4. Why can't we directly search using text?

### Answer

Text matching only compares exact words.

Semantic search compares meanings.

Example:

Question:

```
Who developed Python?
```

Document:

```
Python was created by Guido van Rossum.
```

A normal SQL search may fail.

Vector search correctly identifies them as similar.

---

# 5. What is Semantic Search?

### Answer

Semantic Search retrieves documents based on meaning rather than exact keywords.

It compares vector embeddings instead of text strings.

---

# 6. Why use pgvector?

### Answer

pgvector extends PostgreSQL to store and compare vector embeddings.

It supports similarity search using functions such as:

- Cosine Distance
- Euclidean Distance
- Inner Product

This enables efficient retrieval of relevant chunks.

---

# 7. What is Cosine Distance?

### Answer

Cosine distance measures similarity between two vectors.

Lower cosine distance means higher similarity.

The chunk with the lowest distance is considered the most relevant.

---

# 8. Why do we retrieve only Top-K chunks?

### Answer

Sending the entire document to the LLM is inefficient.

Instead, we retrieve only the most relevant chunks.

Benefits:

- Faster responses
- Lower token usage
- Lower API cost
- Better answer quality

---

# 9. Why do we filter by document_id?

### Answer

Without filtering, semantic search would compare the query against every document stored in the database.

This could retrieve unrelated information.

Filtering ensures retrieval happens only within the selected document.

---

# 10. What is Prompt Engineering?

### Answer

Prompt engineering is the process of designing structured prompts that guide an LLM to produce accurate and reliable responses.

A good prompt improves answer quality and reduces hallucinations.

---

# 11. What information does your prompt contain?

### Answer

The prompt contains:

- Retrieved Context
- User Question
- AI Instructions
- Hallucination Prevention Rules
- Final Answer Section

---

# 12. How do you reduce hallucinations?

### Answer

The prompt instructs the model to:

- Answer only from the provided context.
- Avoid making assumptions.
- Clearly state when information is unavailable.

---

# 13. What happens after retrieval?

### Answer

The retrieved chunks are combined into a single context.

The Prompt Builder creates a structured prompt.

This prompt is then sent to the AI Service.

---

# 14. Why did you create an AIService?

### Answer

AIService separates AI-related logic from business logic.

Instead of calling Gemini directly from CRUD functions:

```
CRUD

↓

AIService

↓

Provider
```

This improves maintainability and scalability.

---

# 15. Why use Provider Abstraction?

### Answer

Different LLM providers have different SDKs.

By creating provider classes with the same interface, the application can switch providers without changing business logic.

---

# 16. Why implement Retry?

### Answer

Sometimes API calls fail due to temporary issues.

Retry automatically attempts the request again before marking it as failed.

This improves reliability.

---

# 17. Why implement Fallback?

### Answer

If one provider fails completely:

```
Gemini

↓

Failed

↓

Groq

↓

Success
```

The user still receives a response.

---

# 18. What is Lazy Initialization?

### Answer

Providers are created only when first needed.

After creation, they are cached and reused.

Benefits:

- Faster startup
- Lower memory usage
- Better scalability

---

# 19. Explain your Chat API flow.

### Answer

```
POST /chat

↓

Authenticate User

↓

Generate Query Embedding

↓

Search Similar Chunks

↓

Build Prompt

↓

AIService

↓

Gemini / Groq / DeepSeek

↓

Return Final Answer
```

---

# 20. What is the responsibility of each layer?

### Router

Receives HTTP requests.

### CRUD

Handles business logic.

### Embedding Utility

Generates embeddings.

### Prompt Builder

Creates the prompt.

### AIService

Communicates with AI providers.

### Provider

Makes API calls to the selected LLM.

---

# 21. Why use dependency injection in FastAPI?

### Answer

Dependency Injection automatically provides required objects such as:

- Database session
- Current authenticated user
- Authorization checks

This keeps route functions clean and reusable.

---

# 22. Why store embeddings in PostgreSQL?

### Answer

Storing embeddings allows semantic search without regenerating vectors every time.

Benefits:

- Faster search
- Persistent storage
- Efficient retrieval
- Supports vector indexing

---

# 23. How does your system ensure security?

### Answer

- JWT Authentication
- OAuth2 Bearer Token
- Current User Dependency
- Organization Isolation
- Role-Based Access Control (RBAC)

Only authenticated users can query their own organization's documents.

---

# 24. Which design principles did you follow?

### Answer

- Single Responsibility Principle (SRP)
- Separation of Concerns (SoC)
- Dependency Injection
- Provider Pattern
- Strategy Pattern
- Lazy Initialization
- Failover Architecture

---

# 25. What was today's biggest learning?

### Answer

Today I completed the first end-to-end version of my Retrieval-Augmented Generation pipeline.

I learned how user queries are converted into embeddings, how semantic search retrieves relevant document chunks using pgvector, how structured prompts improve LLM responses, and how a modular AI service with retry and fallback mechanisms creates a reliable and scalable RAG application.