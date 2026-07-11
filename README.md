# Enterprise Multi-Tenant RAG Platform

An enterprise-grade Retrieval-Augmented Generation (RAG) platform that enables organizations to securely upload documents, build a private knowledge base, and interact with them using AI-powered semantic search and question answering.

> 🚧 **Project Status:** Under Active Development

---

## Features

### Authentication & Authorization
- JWT Authentication
- Role-Based Access Control (RBAC)
- Protected REST APIs
- Organization-based Multi-Tenancy

### Organization Management
- Create, Update, Delete Organizations
- Organization Isolation
- Admin-only Organization Management

### User Management
- User Registration & Login
- Secure Password Hashing (bcrypt)
- Role Management (Admin / Employee)
- Protected User APIs

### Document Management
- Secure PDF Upload
- PDF Validation
- File Metadata Storage
- PostgreSQL Integration
- Organization-specific Document Access

### PDF Processing
- Text Extraction using PyMuPDF
- Document Validation

### Coming Soon
- Text Chunking
- Embedding Generation
- pgvector Integration
- Semantic Search
- AI Chat with Documents
- Conversation History
- Streaming Responses
- Docker Deployment

---

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT Authentication
- Pydantic

### AI / RAG
- PyMuPDF
- LangChain *(Upcoming)*
- OpenAI API *(Upcoming)*
- pgvector *(Upcoming)*

### DevOps
- Docker *(Upcoming)*

---

## Project Structure

```text
backend/
│
├── core/
├── crud/
├── database/
├── dependencies/
├── models/
├── routers/
├── schemas/
├── utils/
├── uploads/
└── app.py
```

---

## Current Architecture

```text
User
   │
   ▼
JWT Authentication
   │
   ▼
Role Verification
   │
   ▼
Upload PDF
   │
   ▼
Validate PDF
   │
   ▼
Store File
   │
   ▼
Extract Text
   │
   ▼
Save Metadata (PostgreSQL)
```

---

## Planned RAG Pipeline

```text
PDF Upload
      │
      ▼
Text Extraction
      │
      ▼
Chunking
      │
      ▼
Embeddings
      │
      ▼
pgvector
      │
      ▼
Semantic Search
      │
      ▼
LLM
      │
      ▼
AI Response
```

---

## Installation

```bash
git clone https://github.com/your-username/enterprise-rag-platform.git

cd enterprise-rag-platform/backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

Run

```bash
uvicorn app:app --reload
```

---

## API Documentation

```
http://localhost:8000/docs
```

---

## Current Progress

- [x] PostgreSQL Integration
- [x] SQLAlchemy Models
- [x] CRUD Operations
- [x] JWT Authentication
- [x] RBAC
- [x] Multi-Tenant Organizations
- [x] Secure PDF Upload
- [x] File Validation
- [x] Metadata Storage
- [x] PDF Text Extraction
- [ ] Chunking
- [ ] Embeddings
- [ ] pgvector
- [ ] Semantic Search
- [ ] Chat with Documents
- [ ] Docker Deployment

---

## License

MIT License