# Week 2 - Day 4: Retrieval Pipeline (Semantic Search)

---

## Q1. What is Retrieval in RAG?

**Answer**

Retrieval is the process of finding the most relevant document chunks for a user's question before sending the context to the LLM.

Workflow:

```text
User Question

↓

Generate Query Embedding

↓

Vector Similarity Search

↓

Retrieve Top-K Chunks

↓

LLM
```

Retrieval is the core component of every RAG system.

---

## Q2. What is Semantic Search?

**Answer**

Semantic Search retrieves information based on **meaning**, not exact keywords.

Instead of matching words, it compares vector embeddings.

This allows the system to understand synonyms and related concepts.

---

## Q3. Why not use SQL LIKE?

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

SQL:

```sql
LIKE '%AI%'
```

Returns nothing.

Vector Search compares semantic meaning.

Since "AI" and "Artificial Intelligence" have similar embeddings, semantic search retrieves the correct document.

---

## Q4. What is a Query Embedding?

**Answer**

A Query Embedding is the vector representation of the user's question.

Example:

```text
"What is Machine Learning?"

↓

Embedding

↓

[0.12, -0.34, ...]
```

The query embedding is compared with stored document embeddings.

---

## Q5. What is Cosine Distance?

**Answer**

Cosine Distance measures how similar two vectors are.

Smaller distance means:

- Higher similarity
- More relevant chunk

Larger distance means:

- Lower similarity
- Less relevant chunk

---

### Follow-up Question

**Why did you use Cosine Distance instead of Euclidean Distance?**

**Answer**

Voyage AI embeddings are optimized for cosine similarity.

Cosine Distance compares the direction of vectors rather than their magnitude, making it more suitable for semantic text similarity.

---

## Q6. What does the `<=>` operator do in pgvector?

**Answer**

The `<=>` operator calculates the cosine distance between two vectors.

Example:

```sql
ORDER BY embedding <=> query_embedding
```

PostgreSQL automatically sorts results from most similar to least similar.

---

## Q7. Why do we retrieve Top-K chunks instead of only one?

**Answer**

A single chunk may not contain the complete answer.

Retrieving multiple relevant chunks provides richer context to the LLM.

This improves answer quality and reduces the chance of missing important information.

---

### Follow-up Question

**How many chunks should we retrieve?**

**Answer**

There is no fixed number.

Common values:

- Top 3
- Top 5
- Top 10

The choice depends on:

- Chunk size
- LLM context window
- Retrieval quality

---

## Q8. Why does SQLAlchemy return tuples in your retrieval query?

**Answer**

My query retrieves:

- DocumentChunk
- Cosine Distance

Since two values are selected, SQLAlchemy returns tuples.

Example:

```python
(
    DocumentChunk(...),
    0.08
)
```

This allows access to both the retrieved chunk and its distance score.

---

## Q9. Explain Tuple Unpacking.

**Answer**

Python allows unpacking tuples directly.

Example:

```python
for chunk, score in results:
```

Internally Python performs:

```python
chunk = DocumentChunk(...)
score = 0.08
```

This makes the code more readable.

---

## Q10. Explain the Retrieval Pipeline in your project.

**Answer**

```text
User Query

↓

Generate Query Embedding

↓

Cosine Similarity Search (pgvector)

↓

Retrieve Top-K Chunks

↓

Return Relevant Context
```

The retrieved chunks are later passed to the LLM to generate the final answer.

---

## Revision Summary

- Retrieval
- Semantic Search
- Query Embeddings
- Cosine Distance
- pgvector `<=>`
- Top-K Retrieval
- SQLAlchemy Vector Queries
- Tuple Unpacking
- Retrieval Pipeline