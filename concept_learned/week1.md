# Week 1 - Concepts Learned

## 📅 Duration
Week 1

---

# Goal

Build a strong understanding of enterprise backend development by learning project planning, database design, FastAPI architecture, authentication, authorization, and secure document management.

---

# Day 1 — Project Planning

## Concepts Learned

### Functional Requirements

- Functional requirements describe **what the system should do**.
- They define the core features of the application.
- Examples:
  - User Registration
  - Login
  - Upload PDF
  - Ask Questions
  - AI Chat

---

### Non-Functional Requirements

- Non-functional requirements describe **how the system should perform**.
- They focus on quality rather than functionality.

Examples:

- Security
- Scalability
- Performance
- Reliability
- Maintainability

---

### High-Level System Architecture

Learned how an enterprise application is designed before writing code.

Typical flow:

```
Client
    │
    ▼
FastAPI
    │
    ▼
Business Logic
    │
    ▼
Database
    │
    ▼
Response
```

---

### Request Lifecycle

Understood how every request travels through the application.

```
Client
    │
    ▼
API Endpoint
    │
    ▼
Business Logic
    │
    ▼
Database
    │
    ▼
API Response
```

---

### Technology Stack Selection

Learned why different technologies were chosen for this project.

- FastAPI for backend APIs
- PostgreSQL for relational data
- SQLAlchemy ORM
- JWT for authentication
- PyMuPDF for PDF extraction
- Voyage AI for embeddings
- pgvector for vector search

---

# Day 2 — Database Design

## Concepts Learned

### Relational Databases

Learned why relational databases are suitable for structured enterprise applications.

Benefits:

- Structured data
- Relationships
- ACID transactions
- Data consistency

---

### Primary Key

- Uniquely identifies every record.
- Cannot contain duplicate values.
- Cannot be NULL.

Example:

```
User
----
id
name
email
```

---

### Foreign Key

A Foreign Key connects two tables together.

Example:

```
Organization

id

↓

User

organization_id
```

---

### One-to-Many Relationship

One organization can have many users.

```
Organization
        │
        ├────────► User
        ├────────► User
        ├────────► User
```

---

### ER Diagram

Learned why Entity Relationship diagrams should be created before implementation.

Benefits:

- Better planning
- Easier database design
- Fewer future modifications

---

### Database Normalization

Learned why normalization is important.

Benefits:

- Reduces redundancy
- Prevents duplicate data
- Improves consistency
- Makes maintenance easier

---

# Day 3 — Project Setup

## Concepts Learned

### FastAPI Project Structure

Learned how to organize an enterprise FastAPI project into multiple modules.

```
router/
models/
schemas/
crud/
core/
database/
utils/
services/
```

Each folder has a single responsibility.

---

### SQLAlchemy Architecture

Understood the purpose of:

- Engine
- Session
- Base

Engine

- Connects Python to PostgreSQL.

Session

- Executes database operations.

Base

- Parent class for all models.

---

### Dependency Injection

Learned how FastAPI injects dependencies using `Depends()`.

Benefits:

- Loose coupling
- Cleaner code
- Better testing
- Reusability

---

### Database Session Lifecycle

Every request:

```
Open Session
      │
      ▼
Execute Query
      │
      ▼
Commit / Rollback
      │
      ▼
Close Session
```

---

### Swagger Documentation

Learned that FastAPI automatically generates API documentation.

Benefits:

- Interactive API testing
- Automatic documentation
- Faster backend development

---

# Day 4 — Organization Module

## Concepts Learned

### SQLAlchemy Models

Models represent database tables.

Responsibilities:

- Table structure
- Relationships
- Database mapping

---

### Pydantic Schemas

Schemas represent API request and response validation.

Responsibilities:

- Input validation
- Output serialization
- Data conversion

---

### Difference Between Model and Schema

Model

- Database representation

Schema

- API representation

Keeping them separate improves maintainability.

---

### CRUD Architecture

Learned why database operations should be separated from API routes.

CRUD layer handles:

- Create
- Read
- Update
- Delete

Benefits:

- Reusability
- Cleaner code
- Better testing

---

### ORM Relationships

Learned how SQLAlchemy `relationship()` connects related tables.

Benefits:

- Easier navigation between tables
- Cleaner queries
- Automatic relationship handling

---

### Input Validation

Learned how Pydantic validates incoming requests before business logic executes.

Benefits:

- Prevents invalid data
- Better error messages
- Improved API security

---

### Clean Architecture

Learned the importance of separating responsibilities.

```
Router
    │
    ▼
CRUD
    │
    ▼
Database
```

Each layer performs only one responsibility.

---

# Day 5 — User Module

## Concepts Learned

### Hashing vs Encryption

Hashing

- One-way process
- Cannot be reversed
- Used for passwords

Encryption

- Two-way process
- Can be decrypted with a key
- Used for sensitive data

---

### Password Security

Passwords should never be stored as plain text.

Instead:

```
Password
      │
      ▼
bcrypt Hash
      │
      ▼
Database
```

---

### bcrypt

Learned how bcrypt securely hashes passwords.

Benefits:

- Salt generation
- Slow hashing
- Protection against brute-force attacks

---

### User Registration Workflow

```
User Input
      │
      ▼
Validate Data
      │
      ▼
Hash Password
      │
      ▼
Save User
```

---

### Password Verification

Login process:

```
User Password
      │
      ▼
bcrypt Verify
      │
      ▼
Stored Hash
```

Passwords are verified without ever decrypting them.

---

# Day 6 — Authentication & Authorization

## Concepts Learned

### JWT Authentication

Understood the complete JWT authentication flow.

```
Login
      │
      ▼
Generate JWT
      │
      ▼
Return Token
      │
      ▼
Protected API
      │
      ▼
Verify Token
```

---

### Stateless Authentication

Unlike session-based authentication, JWT stores user information inside the token.

Benefits:

- Scalable
- No server-side session storage
- Better for APIs

---

### OAuth2PasswordBearer

Learned how FastAPI extracts bearer tokens automatically from request headers.

---

### Authentication vs Authorization

Authentication

- Who are you?

Authorization

- What are you allowed to do?

---

### Role-Based Access Control (RBAC)

Learned how user roles restrict access to specific APIs.

Example:

```
Admin
 ├── Create Organization
 ├── Manage Users

Employee
 ├── View Documents
 └── Chat with AI
```

---

### Protecting APIs

Used dependencies to protect routes.

Benefits:

- Centralized security
- Reusable authentication logic
- Cleaner API code

---

# Day 7 — Document Management

## Concepts Learned

### Secure File Upload

Learned how to securely upload PDF files.

Validation includes:

- File type
- File size
- Upload restrictions

---

### UUID File Naming

Instead of storing files using user-provided names:

```
resume.pdf
```

Store as:

```
9b1ef5d7-acde-4d9d.pdf
```

Benefits:

- Prevents filename conflicts
- Improves security
- Avoids overwriting existing files

---

### PDF Validation

Validated:

- MIME type
- File extension
- Maximum file size

This prevents invalid uploads.

---

### File Storage vs Metadata

Actual PDF:

Stored on disk.

Metadata:

Stored inside PostgreSQL.

Metadata includes:

- Title
- Original Filename
- Stored Filename
- File Size
- Upload Time

---

### PDF Text Extraction

Used **PyMuPDF** to extract text from uploaded PDFs.

Flow:

```
Upload PDF
      │
      ▼
Extract Text
      │
      ▼
Store Metadata
```

---

### File Management in FastAPI

Learned how FastAPI handles uploaded files efficiently using `UploadFile`.

Benefits:

- Memory efficient
- Supports large files
- Faster uploads

---

# Week 1 Summary

During Week 1, I built the complete backend foundation of the Enterprise RAG Platform. I learned enterprise project planning, relational database design, FastAPI architecture, SQLAlchemy ORM, dependency injection, CRUD architecture, secure authentication using JWT, role-based authorization, and secure PDF document management. This foundation prepared the project for implementing Retrieval-Augmented Generation (RAG) in the following weeks.