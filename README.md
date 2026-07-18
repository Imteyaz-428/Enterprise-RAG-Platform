# 🚀 Enterprise Multi-Tenant RAG Platform

> An enterprise-grade Retrieval-Augmented Generation (RAG) platform that enables organizations to securely upload documents, build a private knowledge base, and interact with them using AI-powered semantic search.

**Project Status:** 🚧 Active Development

---

## ✨ Overview

This project is designed to simulate a production-ready Enterprise AI Knowledge Base.

Organizations can securely upload PDF documents, which are processed into searchable vector embeddings. Users can then ask natural language questions, and the system retrieves the most relevant document sections before generating accurate AI-powered answers.

The project focuses on scalability, clean architecture, security, and enterprise best practices.

---

# ✨ Features

## 🔐 Authentication & Security

- JWT Authentication
- Secure Password Hashing (bcrypt)
- OAuth2 Bearer Authentication
- Role-Based Access Control (RBAC)
- Organization Isolation (Multi-Tenant)
- Protected REST APIs

---

## 🏢 Organization Management

- Create Organization
- Update Organization
- Delete Organization
- Multi-Tenant Architecture
- Organization-level Data Isolation

---

## 👥 User Management

- User Registration
- Secure Login
- Admin & Employee Roles
- Protected User APIs
- Profile Management

---

## 📄 Document Management

- Secure PDF Upload
- PDF Validation
- Metadata Storage
- Organization-specific Documents
- PostgreSQL Storage

---

## 📚 PDF Processing

- PDF Text Extraction (PyMuPDF)
- Manual Text Chunking
- Chunk Metadata Storage

---

## 🤖 AI / RAG

- Voyage AI Embeddings
- pgvector Integration
- Semantic Search
- Cosine Similarity Search
- Prompt Builder
- AI Chat Endpoint
- Retrieval-Augmented Generation (RAG)

---

## 🧠 AI Service Layer

- Provider Abstraction
- Gemini Integration
- Groq Integration
- DeepSeek Integration
- Retry Mechanism
- Automatic Provider Fallback
- Lazy Initialization

---

## 🚧 Upcoming Features

- Conversation History
- Streaming Responses
- React Frontend
- Docker Deployment
- Kubernetes Deployment
- Redis Caching

---

# 🏗️ System Architecture

```text
                    User
                      │
             JWT Authentication
                      │
           Role-Based Authorization
                      │
            Upload / Select Document
                      │
             Generate Query Embedding
                      │
               Voyage AI Embeddings
                      │
            PostgreSQL + pgvector
                      │
             Semantic Vector Search
                      │
          Retrieve Top-K Relevant Chunks
                      │
                Prompt Builder
                      │
                AI Service Layer
                      │
      Gemini / Groq / DeepSeek Provider
                      │
               AI Generated Answer
```

---

# 🔄 Complete RAG Pipeline

```text
Upload PDF
      │
      ▼
Validate PDF
      │
      ▼
Extract Text
      │
      ▼
Chunk Text
      │
      ▼
Generate Embeddings
      │
      ▼
Store in PostgreSQL + pgvector
      │
      ▼
User Question
      │
      ▼
Generate Query Embedding
      │
      ▼
Semantic Search
      │
      ▼
Retrieve Top-K Chunks
      │
      ▼
Build Prompt
      │
      ▼
AI Provider
      │
      ▼
Generate Final Answer
```

---

# 🛠️ Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT Authentication
- OAuth2

---

## AI / RAG

- Voyage AI
- pgvector
- PyMuPDF
- Gemini
- Groq
- DeepSeek

---

## Database

- PostgreSQL
- pgvector Extension

---

## Tools

- Docker (Upcoming)
- Git
- VS Code

---

# 📂 Project Structure

```text
backend/
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── ai_service.py
│
├── crud/
│
├── database/
│
├── dependencies/
│
├── models/
│
├── routers/
│
├── schemas/
│
├── utils/
│   ├── embedding.py
│   ├── chunking.py
│   ├── prompt_builder.py
│   └── pdf_extractor.py
│
├── uploads/
│
└── app.py
```

---

# 📌 API Endpoints

## Authentication

- POST `/auth/register`
- POST `/auth/login`

---

## Organizations

- POST `/organizations`
- GET `/organizations`
- PUT `/organizations/{id}`
- DELETE `/organizations/{id}`

---

## Users

- POST `/users`
- GET `/users/me`

---

## Documents

- POST `/documents/upload`
- GET `/documents`

---

## Chat

- POST `/chat`

Example Request

```json
{
    "document_id": 1,
    "question": "Summarize this document."
}
```

Example Response

```json
{
    "answer": "..."
}
```

---

# 📊 Current Progress

## Backend

- [x] PostgreSQL Integration
- [x] SQLAlchemy Models
- [x] CRUD Operations
- [x] JWT Authentication
- [x] RBAC
- [x] Multi-Tenant Architecture

---

## Documents

- [x] PDF Upload
- [x] PDF Validation
- [x] Metadata Storage
- [x] PDF Text Extraction
- [x] Manual Chunking

---

## AI / RAG

- [x] Voyage Embeddings
- [x] pgvector Integration
- [x] Semantic Search
- [x] Prompt Builder
- [x] AI Chat Endpoint
- [x] Multi-Provider AI Service
- [x] Retry Mechanism
- [x] Provider Fallback

---

## Remaining

- [ ] Conversation History
- [ ] Streaming Responses
- [ ] React Frontend
- [ ] Docker Deployment
- [ ] Kubernetes
- [ ] Redis Cache

---

# 💡 Design Decisions

- Multi-Tenant Architecture for organization isolation
- Service Layer for AI integration
- Provider Pattern for multiple LLMs
- Retry & Fallback for reliability
- Semantic Search using pgvector
- Prompt Builder to reduce hallucinations
- Separation of Concerns using CRUD architecture
- Dependency Injection with FastAPI

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/your-username/enterprise-rag-platform.git
```

Navigate to the backend

```bash
cd enterprise-rag-platform/backend
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate the environment

### macOS/Linux

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```env
DATABASE_URL=postgresql://username:password@localhost/database

SECRET_KEY=your_secret_key

ALGORITHM=HS256

VOYAGE_API_KEY=your_voyage_api_key

GEMINI_API_KEY=your_gemini_api_key

GROQ_API_KEY=your_groq_api_key

DEEPSEEK_API_KEY=your_deepseek_api_key
```

Run the application

```bash
uvicorn app:app --reload
```

---

# 📖 API Documentation

After starting the server:

```
http://localhost:8000/docs
```

Swagger UI provides interactive API documentation.

---

# 📚 What I Learned

Through this project, I gained hands-on experience with:

- Enterprise Backend Development
- Multi-Tenant Architecture
- JWT Authentication
- Role-Based Access Control
- PostgreSQL
- Vector Databases (pgvector)
- Semantic Search
- Retrieval-Augmented Generation (RAG)
- Prompt Engineering
- AI Provider Abstraction
- Retry & Fallback Strategies
- Clean Architecture Principles
- FastAPI Dependency Injection

---

# 🗺️ Roadmap

- [ ] Conversation Memory
- [ ] Source Citations
- [ ] Streaming AI Responses
- [ ] React Dashboard
- [ ] Docker Compose
- [ ] Kubernetes Deployment
- [ ] Redis Caching
- [ ] Monitoring & Logging

---

# 📄 License

This project is licensed under the **MIT License**.