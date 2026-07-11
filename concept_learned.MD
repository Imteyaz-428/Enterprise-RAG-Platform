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