# Week 2 - Day 1: Text Processing Pipeline (Chunking)

---

## Q1. Why do we need Chunking in a RAG system?

**Answer**

Large Language Models (LLMs) and embedding models have input size limits.

A PDF may contain thousands of words, which cannot be processed as a single input.

Chunking divides the document into smaller pieces so that:

- Embeddings can be generated efficiently.
- Relevant information can be retrieved accurately.
- Token limits of embedding models and LLMs are respected.

Example:

```text
Large PDF

↓

Chunk 1

Chunk 2

Chunk 3

Chunk 4
```

---

## Q2. What happens if we don't use Chunking?

**Answer**

Without chunking:

- Very large documents may exceed model limits.
- Retrieval quality decreases.
- The embedding represents the entire document instead of specific topics.
- The LLM receives unnecessary information.

This reduces the accuracy of the RAG system.

---

## Q3. Why can't we generate one embedding for the entire document?

**Answer**

One embedding represents the overall meaning of the document.

Suppose a PDF contains:

- Introduction
- Machine Learning
- Database Design
- Conclusion

A single embedding mixes all these topics together.

During retrieval, the system cannot identify which specific section answers the user's question.

Chunk-level embeddings allow retrieval of only the relevant section.

---

## Q4. How did you implement chunking?

**Answer**

I implemented a custom chunking utility.

Workflow:

```text
Extracted Text

↓

Split into smaller chunks

↓

Store chunks in a list

↓

Generate embedding for each chunk
```

This helped me understand the internal working of RAG before using frameworks like LangChain.

---

## Q5. What is Chunk Size?

**Answer**

Chunk size determines the maximum amount of text inside one chunk.

Example:

```text
Chunk Size = 500 characters
```

Larger chunks:

- More context
- Higher token usage

Smaller chunks:

- More precise retrieval
- Less context

Choosing the correct chunk size is a balance between context and retrieval accuracy.

---

## Q6. What is Chunk Overlap?

**Answer**

Chunk overlap means repeating a small portion of text between consecutive chunks.

Example:

```text
Chunk 1

Sentence A
Sentence B
Sentence C

Chunk 2

Sentence C
Sentence D
Sentence E
```

This prevents important information from being split across chunk boundaries.

---

### Follow-up Question

**Did your project use Chunk Overlap?**

**Answer**

Initially, I implemented manual chunking without overlap to understand the fundamentals of RAG.

Once the manual implementation is complete, I plan to replace it with production-ready text splitters such as LangChain's RecursiveCharacterTextSplitter, which supports configurable overlap.

---

## Q7. Why did you manually implement chunking instead of using LangChain?

**Answer**

I wanted to understand the complete RAG pipeline from scratch.

Implementing chunking manually helped me understand:

- Why chunking is required.
- How chunk size affects retrieval.
- How embeddings are generated for each chunk.

After understanding these concepts, replacing the implementation with LangChain becomes much easier.

---

## Q8. Explain the text processing pipeline in your project.

**Answer**

```text
PDF Upload

↓

Extract Text (PyMuPDF)

↓

Chunk Text

↓

Generate Embeddings

↓

Store Embeddings
```

This prepares documents for semantic search.

---

## Revision Summary

- Chunking
- Chunk Size
- Chunk Overlap
- Document Segmentation
- Why Chunking is Required
- Manual Chunking
- RAG Text Processing Pipeline