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