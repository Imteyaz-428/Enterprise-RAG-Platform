# Interview Notes — Week 2 Day 8
## Enterprise Multi-Tenant RAG Platform

---

# 1. Why did you create a ChatService?

Instead of placing all business logic inside the FastAPI router, I created a ChatService to separate business logic from HTTP handling.

The router only receives requests, validates them, authenticates users, and forwards them to ChatService.

ChatService coordinates the complete chat workflow, making the code cleaner, easier to test, and easier to maintain.

---

# 2. What is the responsibility of ChatService?

ChatService acts as the orchestrator of the chat system.

Its responsibilities include:

- Create or load chat sessions
- Save user messages
- Retrieve conversation history
- Perform semantic retrieval
- Build prompts
- Generate AI responses
- Save assistant responses
- Return the final response

It does not directly communicate with the database. Instead, it uses CRUD modules.

---

# 3. What is RetrievalService?

RetrievalService is responsible only for retrieving relevant document chunks.

Workflow:

Question
↓

Generate Query Embedding
↓

Semantic Search
↓

Return Top-K Chunks

Keeping retrieval separate follows the Single Responsibility Principle.

---

# 4. What is PromptService?

PromptService builds the final prompt that is sent to the LLM.

It combines:

- System Instructions
- Retrieved Context
- Conversation History
- User Question

This keeps prompt engineering separate from business logic.

---

# 5. Why not build prompts directly inside ChatService?

Prompt building is a separate concern.

Separating PromptService allows:

- Better maintainability
- Easier prompt experimentation
- Independent testing
- Cleaner architecture

---

# 6. Why did you separate CRUD from Services?

CRUD modules only perform database operations.

Services contain business logic.

Example:

Router
↓

Service
↓

CRUD
↓

Database

This separation makes the project scalable and follows clean architecture principles.

---

# 7. Explain the complete chat workflow.

1. User sends a question.
2. Router authenticates the user.
3. ChatService creates or loads a chat session.
4. User message is saved.
5. Conversation history is retrieved.
6. RetrievalService performs semantic search.
7. PromptService builds the final prompt.
8. AIService generates the response.
9. Assistant message is saved.
10. Final response is returned.

---

# 8. Why store conversation history?

Conversation history enables multi-turn conversations.

Example:

User:
What is the leave policy?

Assistant:
...

User:
How many casual leaves are allowed?

The second question depends on the first one.

Without history, the model would lose context.

---

# 9. Why create ChatSession and ChatMessage separately?

A ChatSession represents an entire conversation.

A ChatMessage represents a single message.

Relationship:

ChatSession
    │
    ├── Message 1
    ├── Message 2
    ├── Message 3
    └── Message N

This design supports unlimited messages per conversation.

---

# 10. Why use Cascade Delete?

When a chat session is deleted, all associated messages should also be deleted automatically.

Benefits:

- No orphan records
- Better database consistency
- Cleaner data management

---

# 11. Why use organization_id instead of document_id during retrieval?

Initially, retrieval searched within a single document.

Now retrieval searches across every document belonging to the organization.

Benefits:

- Enterprise search
- Better user experience
- Users don't need to select a document
- Supports organization-wide knowledge bases

---

# 12. How does semantic search work?

Workflow:

Question
↓

Generate Embedding

↓

Compare with Stored Embeddings

↓

Cosine Similarity

↓

Retrieve Top-K Chunks

↓

Return Context

Unlike keyword search, semantic search understands meaning.

---

# 13. Why use pgvector?

PostgreSQL cannot efficiently compare vectors by default.

pgvector adds:

- Vector data type
- Cosine similarity
- Euclidean distance
- Inner product search
- Efficient vector indexing

This enables semantic search directly inside PostgreSQL.

---

# 14. Why use Top-K Retrieval?

Instead of sending the entire document to the LLM, only the most relevant chunks are retrieved.

Advantages:

- Faster responses
- Lower token usage
- Better answer quality
- Lower API cost

---

# 15. Why save assistant responses?

Saving assistant responses allows:

- Complete conversation history
- Chat restoration
- Follow-up questions
- Better user experience

---

# 16. Why return 404 instead of 403 for unauthorized chat sessions?

Returning 404 hides whether the resource exists.

If another user's session returned 403, an attacker could discover valid session IDs.

Returning 404 prevents resource enumeration attacks.

---

# 17. Which design patterns are used in your project?

- Service Layer Pattern
- Provider Pattern
- Repository-style CRUD Pattern
- Orchestrator Pattern
- Dependency Injection
- Strategy-like Provider Selection

---

# 18. Explain your backend architecture.

User Request
↓

Router

↓

Service Layer

↓

CRUD Layer

↓

Database

For AI requests:

ChatService
↓

RetrievalService

↓

PromptService

↓

AIService

↓

Gemini / Groq / DeepSeek

Each layer has a single responsibility.

---

# 19. What principles did you follow while designing the project?

- Separation of Concerns
- Single Responsibility Principle
- Dependency Injection
- Loose Coupling
- High Cohesion
- Modular Design
- Clean Architecture

---

# 20. What did you learn today?

- Designing a service-layer architecture
- Building persistent multi-turn conversations
- Organizing business logic into dedicated services
- Managing chat sessions and messages
- Designing secure REST APIs
- Implementing organization-wide semantic retrieval
- Applying enterprise software engineering principles in an AI application