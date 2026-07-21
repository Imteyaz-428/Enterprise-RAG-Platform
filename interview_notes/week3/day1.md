# Week 3 - Day 1: Interview Notes

## 1. What are Source Citations?

Source citations indicate which document and chunk were used to generate an AI response. They help users verify the information and increase trust in the system.

---

## 2. Why are Source Citations important?

- Improve transparency.
- Help users verify AI-generated answers.
- Reduce the impact of hallucinations.
- Widely used in enterprise RAG systems.

---

## 3. Why shouldn't the LLM generate citations?

The LLM can hallucinate document names or references. The backend already knows which chunks were retrieved from the vector database, so citations should be generated from retrieval metadata instead of the model.

---

## 4. What is RetrievalResult?

`RetrievalResult` is a dataclass that stores:

- DocumentChunk
- Document
- Similarity Score

It replaces anonymous tuples with a structured object.

---

## 5. Why use RetrievalResult instead of tuples?

Instead of:

```python
(chunk, document, score)
```

we use:

```python
result.chunk
result.document
result.score
```

Benefits:

- Better readability.
- Type safety.
- Easier maintenance.
- Easy to extend with fields like page number or rerank score.

---

## 6. Why is RetrievalResult placed inside services/chat?

It is an internal object used only by the service layer.

- Not a database model.
- Not an API request/response schema.
- Used to transfer retrieval data between services.

---

## 7. Which service generates citations?

`ChatService`

Reason:

ChatService orchestrates the complete chat workflow and prepares the final API response, making it the appropriate place to assemble citations.

---

## 8. Responsibility of each layer

**CRUD**
- Fetches data from PostgreSQL.

**RetrievalService**
- Generates query embeddings.
- Performs semantic search.

**PromptService**
- Builds the final prompt for the LLM.

**AIService**
- Generates the AI response.

**ChatService**
- Coordinates the workflow.
- Creates the final response.
- Generates source citations.

---

## 9. What information does a citation contain?

Current version:

```json
{
    "document": "os_file_4.pdf",
    "chunk_index": 6
}
```

Future improvements may include page number or relevance score.

---

## 10. RAG Flow with Citations

User Question

↓

Generate Query Embedding

↓

Vector Search (pgvector)

↓

Retrieve Relevant Chunks

↓

Build Prompt

↓

LLM

↓

Generate Answer

↓

Generate Source Citations

↓

Return API Response

---

## 11. Why include document names in the prompt?

Providing the document name along with the chunk text gives the LLM additional context, especially when multiple documents are retrieved.

---

## 12. What was implemented today?

- Added `RetrievalResult` dataclass.
- Updated RetrievalService to return structured retrieval results.
- Updated PromptService to use `RetrievalResult`.
- Updated ChatService to generate citations.
- Added `CitationResponse` schema.
- Chat API now returns answers along with source citations.