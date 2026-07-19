# Enterprise RAG Platform - Concepts Learned

## Week 1

### Day 1 - Project Planning

- Difference between Functional and Non-Functional Requirements.
- How enterprise applications are designed before coding.
- Understanding High-Level System Architecture.
- Understanding complete request flow from Client → API → Database → Response.
- Choosing technology stack based on project requirements.

---

### Day 2 - Database Design

- Why relational databases are suitable for structured enterprise applications.
- Difference between Primary Key and Foreign Key.
- One-to-Many relationship implementation.
- Why ER Diagrams are important before database implementation.
- Importance of proper database normalization.

---

### Day 3 - Project Setup

- FastAPI project architecture and folder organization.
- SQLAlchemy Engine, Session and Base architecture.
- Dependency Injection using FastAPI Depends().
- Database Session lifecycle.
- Auto-generated API documentation using Swagger.

---

### Day 4 - Organization Module

- Difference between SQLAlchemy Models and Pydantic Schemas.
- Why CRUD logic should be separated from API routes.
- ORM Relationships using relationship().
- Input validation using Pydantic.
- Clean project architecture.

---

### Day 5 - User Module

- Difference between Hashing and Encryption.
- Why passwords should never be stored as plain text.
- How bcrypt generates one-way password hashes.
- User registration workflow.
- Secure password verification process.

---

### Day 6 - Authentication & Authorization

- Complete JWT Authentication flow.
- Stateless Authentication vs Session Authentication.
- Access Token generation and verification.
- OAuth2PasswordBearer workflow.
- Difference between Authentication and Authorization.
- Role-Based Access Control (RBAC).
- Protecting APIs using Dependencies.

---

### Day 7 - Document Management

- Secure file upload implementation.
- Why UUID is used instead of original filenames.
- PDF validation techniques.
- Difference between storing files and storing metadata.
- Text extraction from PDFs using PyMuPDF.
- File management in FastAPI.

---

## Week 2

### Day 1 - Text Processing Pipeline

- Why LLMs cannot process very large documents directly.
- Importance of document chunking in RAG.
- Choosing chunk size and overlap.
- Manual chunking implementation.
- Effect of chunk size on retrieval quality.

---

### Day 2 - Embedding Pipeline

- What embeddings are and why they represent semantic meaning.
- Difference between text and vector representations.
- Batch embedding generation.
- Voyage AI embedding workflow.
- Why embedding dimensions must match the Vector column size.
- Difference between generating one embedding and batch embeddings.

---

### Day 3 - Vector Database Integration

- Difference between PostgreSQL and pgvector.
- Why pgvector can be used instead of a separate Vector Database for small and medium RAG systems.
- How pgvector stores embeddings inside PostgreSQL.
- Docker-based PostgreSQL setup.
- Document ingestion pipeline.
- Complete flow:
  PDF
  → Extract Text
  → Chunk Text
  → Generate Embeddings
  → Store Embeddings
- Debugging PostgreSQL, pgvector and SQLAlchemy integration.

---

### Day 4 - Retrieval Pipeline

- Difference between Keyword Search and Semantic Search.
- Why SQL LIKE cannot perform semantic retrieval.
- Query Embedding generation.
- Why user queries are converted into vectors.
- Cosine Distance and semantic similarity.
- Why smaller cosine distance means more relevant results.
- pgvector `<=>` operator.
- Top-K Retrieval.
- Why RAG retrieves multiple chunks instead of only one.
- SQLAlchemy Vector Search using cosine_distance().
- Mapping SQL queries into SQLAlchemy ORM.
- Returning multiple columns using db.query().
- Tuple Unpacking in Python.
- Difference between Distance and Similarity Score.


# Week 2

## Day 5 - AI Service Architecture

### AI Service
- Understood why AI-related business logic should be separated from API routes.
- Learned how an AI Service acts as a single entry point for interacting with multiple LLM providers.
- Understood how provider abstraction makes the application independent of a specific AI model.

---

### Object-Oriented Design
- Understood the purpose of Abstract Base Classes (ABC).
- Learned how abstract methods define a common interface for all AI providers.
- Understood polymorphism through a common `generate()` method.
- Learned the Provider Pattern for supporting multiple AI providers.

---

### Provider Management
- Understood Provider Registry using a dictionary.
- Learned why dictionary lookup is preferred over multiple `if-else` statements.
- Understood the Open/Closed Principle by adding new providers without modifying existing logic.

---

### Lazy Initialization & Caching
- Learned Lazy Initialization to create provider instances only when needed.
- Understood Provider Instance Caching to reuse existing clients across requests.
- Learned the difference between eager initialization and lazy initialization.
- Understood the performance benefits of caching provider instances.

---

### Reliability
- Learned Retry Mechanism for handling temporary failures.
- Understood Provider Fallback to automatically switch providers when one fails.
- Learned the difference between Retry and Fallback.

---

### Logging & Error Handling
- Understood the importance of structured logging in production applications.
- Learned why logging is preferred over `print()` statements.
- Learned how custom exceptions improve error handling and API responses.

---

### Software Engineering Principles
- Separation of Concerns (SoC)
- Single Responsibility Principle (SRP)
- Open/Closed Principle (OCP)
- Encapsulation using private methods (`_method`)
- Interface-based design using Abstract Base Classes

---

### AI Request Flow

Application

↓

AIService

↓

Provider Registry

↓

Provider Cache

↓

Selected Provider

↓

Retry

↓

Fallback (if needed)

↓

LLM Response

# Week 2 - Day 6 (Concepts Learned)

## 📅 Date
18 July 2026

---

## 1. Retrieval-Augmented Generation (RAG)

RAG combines semantic retrieval with an LLM.

Flow:

```
Question
    ↓
Embedding
    ↓
Semantic Search
    ↓
Top-K Chunks
    ↓
Prompt
    ↓
LLM
    ↓
Answer
```

---

## 2. Query Embeddings

- Convert user questions into vectors.
- Capture semantic meaning instead of exact words.
- Used for vector similarity search.

---

## 3. Semantic Search

Unlike SQL keyword search, semantic search retrieves information based on meaning using vector similarity.

---

## 4. Cosine Distance

- Lower distance → Higher similarity.
- Used to rank retrieved document chunks.

---

## 5. Top-K Retrieval

Instead of sending the whole document to the LLM:

- Retrieve only the most relevant chunks.
- Faster responses.
- Lower token usage.
- Better answer quality.

---

## 6. Prompt Engineering

A good RAG prompt contains:

- Instructions
- Retrieved Context
- User Question

This helps reduce hallucinations.

---

## 7. Hallucination Prevention

The prompt instructs the LLM to:

- Use only retrieved context.
- Avoid outside knowledge.
- Clearly state when information is unavailable.

---

## 8. AI Service Layer

The application communicates with AI providers through `AIService`.

Benefits:

- Loose coupling
- Easier maintenance
- Provider independence

---

## 9. Provider Abstraction

Every provider exposes the same interface.

```
Gemini
Groq
DeepSeek
```

The application can switch providers without changing business logic.

---

## 10. Retry & Fallback

Retry handles temporary API failures.

Fallback switches to another provider if the current provider fails.

---

## 11. Document Authorization

Before retrieval:

- Verify document exists.
- Verify user belongs to the same organization.

This prevents unauthorized access.

---

## 12. Clean Architecture

Responsibilities:

- Router → Handle HTTP requests
- CRUD → Business logic
- Prompt Builder → Build prompts
- AIService → AI communication
- Provider → Call LLM APIs

---

## Today's Key Learning

Today I completed the first end-to-end RAG pipeline that converts a user's question into an embedding, retrieves relevant document chunks using semantic search, builds a grounded prompt, sends it to an LLM, and returns an AI-generated answer.


# Week 2 - Day 7
# Concepts Learned

---

# 1. Why Service Layer?

Initially, all business logic was inside the FastAPI router.

Problems:

- Large router files
- Hard to maintain
- Difficult to test
- Mixed responsibilities

Solution:

Move business logic into Service classes.

Final Flow:

```
Request
    │
    ▼
Router
    │
    ▼
Service
    │
    ▼
CRUD
    │
    ▼
Database
```

Router only handles HTTP requests.

Service contains business logic.

CRUD only performs database operations.

---

# 2. ChatService

ChatService is the central orchestrator of the chat workflow.

Responsibilities:

- Create or load chat session
- Save user messages
- Retrieve conversation history
- Retrieve relevant document chunks
- Build prompt
- Generate AI response
- Save assistant response
- Return final response

ChatService does not know how embeddings, prompts, or AI providers work internally.

It simply coordinates the entire workflow.

---

# 3. Separation of Concerns (SoC)

Each class should have only one responsibility.

RetrievalService

Only responsible for:

- Generate query embeddings
- Perform semantic search
- Return relevant chunks

PromptService

Only responsible for:

- Format conversation history
- Format retrieved context
- Build final prompt

AIService

Only responsible for:

- Call LLM providers
- Retry failed requests
- Fallback between providers
- Return AI response

ChatService

Only responsible for orchestrating the workflow.

---

# 4. Router Responsibilities

Router should only:

- Receive HTTP request
- Validate request
- Authenticate user
- Call Service layer
- Return response

Router should never contain business logic.

---

# 5. Conversation Persistence

Instead of treating every request independently, conversations are stored permanently.

Database stores:

ChatSession

Represents one conversation.

ChatMessage

Stores every user and assistant message.

This allows:

- Multi-turn conversations
- Chat history
- Continue previous sessions

---

# 6. Chat Session

A ChatSession represents one conversation.

Example:

Chat Session

```
Leave Policy Discussion
```

Messages inside:

```
User:
Explain leave policy.

Assistant:
...

User:
How many casual leaves?

Assistant:
...
```

Every conversation has its own unique session_id.

---

# 7. Session Lifecycle

New Chat

```
No session_id
        │
        ▼
Create Session
```

Existing Chat

```
session_id
      │
      ▼
Load Session
```

This is how applications like ChatGPT maintain conversations.

---

# 8. Dependency Injection

Instead of creating dependencies directly inside a class:

```
self.ai = AIService()
```

Use constructor injection.

```
def __init__(
    ai_service=None
)
```

Advantages:

- Easier testing
- Easier mocking
- More flexible architecture
- Better scalability

---

# 9. Enterprise Multi-Document Retrieval

Old Architecture

```
Question
      │
      ▼
document_id
      │
      ▼
Search One PDF
```

Problem:

The AI can only search inside one document.

New Architecture

```
Question
      │
      ▼
organization_id
      │
      ▼
Search Every Document
      │
      ▼
Top Matching Chunks
```

Benefits:

- Search across all uploaded documents
- Better user experience
- Enterprise-ready retrieval

---

# 10. SQL JOIN

DocumentChunk only stores:

```
document_id
```

Organization information is stored in:

```
Document
```

Therefore, searching by organization requires joining both tables.

Concept:

```
DocumentChunk
      │
      ▼
Document
      │
      ▼
organization_id
```

JOIN allows filtering chunks using the organization's documents.

---

# 11. Chat Workflow

Complete execution flow:

```
User Question
        │
        ▼
Chat Router
        │
        ▼
ChatService
        │
        ▼
Create / Load Session
        │
        ▼
Save User Message
        │
        ▼
Retrieve Conversation History
        │
        ▼
Generate Query Embedding
        │
        ▼
Semantic Search
        │
        ▼
Build Prompt
        │
        ▼
AIService
        │
        ▼
Gemini / Groq / DeepSeek
        │
        ▼
Save Assistant Message
        │
        ▼
Return Response
```

---

# 12. Why Store Chat History?

Benefits:

- Follow-up questions
- Context-aware responses
- Better user experience
- Conversation continuity
- ChatGPT-like behavior

Without history:

Every request is independent.

With history:

The AI remembers previous messages.

---

# 13. Multi-Turn Conversation

Example

User

```
What is leave policy?
```

Assistant

```
...
```

User

```
How many casual leaves?
```

The second question depends on the previous conversation.

This is called a Multi-Turn Conversation.

---

# 14. Orchestration Pattern

ChatService follows the Orchestrator pattern.

It does not perform every task itself.

Instead, it coordinates multiple specialized services.

```
ChatService
      │
      ├──────────► RetrievalService
      │
      ├──────────► PromptService
      │
      └──────────► AIService
```

This keeps the code modular and maintainable.

---

# 15. Production Architecture

Final architecture after today's work:

```
Frontend
      │
      ▼
FastAPI Router
      │
      ▼
ChatService
      │
      ├───────────────┐
      ▼               ▼
Session CRUD    RetrievalService
      │               │
      ▼               ▼
Message CRUD   Vector Search
                      │
                      ▼
               PromptService
                      │
                      ▼
                 AIService
                      │
                      ▼
        Gemini / Groq / DeepSeek
```

This architecture follows enterprise backend design principles and is scalable for future features.