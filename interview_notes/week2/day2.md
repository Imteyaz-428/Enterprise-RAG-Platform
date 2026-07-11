# Week 2 - Day 2: Embedding Pipeline

---

## Q1. What is an Embedding?

**Answer**

An embedding is a numerical vector representation of text.

Instead of storing words as plain text, embedding models convert them into vectors that capture semantic meaning.

Example:

```text
Machine Learning

↓

[-0.12, 0.41, ..., 0.25]
```

These vectors allow computers to compare meaning instead of exact words.

---

## Q2. Why do we need Embeddings?

**Answer**

Computers cannot understand the meaning of raw text.

Embeddings transform text into vectors where semantically similar sentences are placed close together.

This enables semantic search.

---

## Q3. Why can't SQL LIKE perform semantic search?

**Answer**

SQL LIKE performs keyword matching.

Example:

Document:

```text
Artificial Intelligence
```

User Query:

```text
AI
```

SQL LIKE:

```sql
WHERE text LIKE '%AI%'
```

Returns nothing.

Embedding search understands that "AI" and "Artificial Intelligence" have similar meanings and retrieves the correct document.

---

## Q4. What embedding model did you use?

**Answer**

I used **Voyage AI** (`voyage-3-large`) to generate document embeddings.

The model converts text chunks into 1024-dimensional vectors.

These vectors are stored inside PostgreSQL using pgvector.

---

## Q5. Why did you choose Voyage AI?

**Answer**

I chose Voyage AI because it provides high-quality embeddings suitable for Retrieval-Augmented Generation (RAG).

It supports:

- High semantic accuracy
- Batch embedding generation
- Integration with Python

The embedding dimension also matches the pgvector column configuration in my project.

---

## Q6. What is Batch Embedding?

**Answer**

Instead of sending one chunk at a time:

```text
Chunk 1

↓

API Call

Chunk 2

↓

API Call

Chunk 3

↓

API Call
```

I generate embeddings for all chunks together:

```text
Chunks

↓

One API Call

↓

Multiple Embeddings
```

Benefits:

- Fewer API requests.
- Better performance.
- Lower latency.

---

## Q7. Why should the embedding dimension match the Vector column?

**Answer**

The Vector column has a fixed dimension.

Example:

```python
Vector(1024)
```

Every stored embedding must contain exactly 1024 values.

If dimensions do not match, PostgreSQL raises an error.

---

## Q8. Explain your embedding generation pipeline.

**Answer**

```text
Chunk Text

↓

Voyage AI

↓

Embedding Vector

↓

Store in PostgreSQL (pgvector)
```

Each chunk receives its own embedding.

---

## Q9. What is the difference between one embedding and batch embeddings?

| One Embedding | Batch Embeddings |
|---------------|-----------------|
| One text | Multiple texts |
| One API request per chunk | One API request for multiple chunks |
| Slower | Faster |
| Higher API usage | Lower API usage |

---

### Follow-up Question

**Why did you change from single embedding generation to batch embedding generation?**

**Answer**

Initially, I generated one embedding for each chunk to understand the process.

Later, I switched to batch embedding generation because it reduces the number of API calls, improves performance, and is the recommended approach for production systems.

---

## Revision Summary

- Embeddings
- Semantic Representation
- Vector Space
- Voyage AI
- Batch Embeddings
- Embedding Dimensions
- Semantic Search
- Embedding Pipeline