# 🚀 Enterprise Multi-Tenant RAG Platform

> A production-ready AI Knowledge Management Platform that enables organizations to upload documents, perform semantic search, and chat with their private knowledge base using Retrieval-Augmented Generation (RAG).

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue)
![Redis](https://img.shields.io/badge/Redis-Caching-red)
![License](https://img.shields.io/badge/License-MIT-orange)

---

# 📖 Overview

Enterprise RAG Platform is a production-oriented backend system built with **FastAPI**, **PostgreSQL**, and **pgvector**.

Organizations can upload PDF documents, automatically generate vector embeddings, and interact with their documents through AI-powered conversations.

The platform follows enterprise software engineering principles including:

- Multi-Tenant Architecture
- Role-Based Access Control (RBAC)
- Service Layer Architecture
- Provider Pattern
- Retrieval-Augmented Generation (RAG)
- Background Processing
- Redis Caching
- Streaming AI Responses

The goal of this project is to demonstrate how modern AI-powered enterprise knowledge systems are designed and implemented.

---

# ✨ Features

## 🔐 Authentication & Security

- JWT Authentication
- OAuth2 Bearer Authentication
- Password Hashing (bcrypt)
- Role-Based Access Control (RBAC)
- Protected REST APIs
- Organization-level Data Isolation

---

## 🏢 Multi-Tenant Architecture

- Organization Management
- User Management
- Organization-specific Documents
- Organization-specific Chat Sessions
- Secure Resource Isolation

---

## 📄 Document Processing

- PDF Upload
- PDF Validation
- UUID File Storage
- Background Processing
- Document Status Tracking
- PDF Text Extraction (PyMuPDF)
- Manual Chunking
- Voyage AI Embeddings
- pgvector Storage

---

## 🤖 AI & RAG

- Semantic Search
- Cosine Similarity Search
- Multi-document Retrieval
- Prompt Builder
- Source Citations
- Hallucination Reduction

---

## 💬 Chat System

- Persistent Chat Sessions
- Conversation History
- Streaming AI Responses (SSE)
- Automatic Session Creation
- Chat Title Generation

---

## ⚡ Performance

- Redis Response Caching
- Background Tasks
- AI Provider Retry
- Automatic Provider Fallback

---

# 🛠️ Tech Stack

### Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- Redis
- Pydantic

### AI

- Voyage AI
- Gemini
- Groq
- DeepSeek
- PyMuPDF

### Security

- JWT
- OAuth2
- bcrypt

### DevOps

- Docker *(Coming Soon)*
- Kubernetes *(Coming Soon)*

---

# 🏗️ Architecture

```text
                           User
                             │
                             ▼
                     Authentication
                             │
                             ▼
                     FastAPI Router
                             │
                             ▼
                      ChatService
                             │
      ┌──────────────────────┴──────────────────────┐
      ▼                                             ▼
RetrievalService                             Session Service
      │
      ▼
Prompt Service
      │
      ▼
AI Service
      │
 ┌────┴─────────────┐
 ▼                  ▼
Gemini          Groq / DeepSeek
      │
      ▼
Generated Response
```

---

# 🔄 RAG Pipeline

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
Semantic Search
     │
     ▼
Retrieve Top-K Chunks
     │
     ▼
Prompt Builder
     │
     ▼
AI Service
     │
     ▼
Generated Answer
```

---

# 📂 Project Structure

```text
Enterprise-RAG-Platform/
│
├── backend/
│   ├── core/
│   ├── crud/
│   ├── database/
│   ├── dependencies/
│   ├── models/
│   ├── router/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── app.py
│
├── frontend/      (Coming Soon)
│
└── README.md
```

---

# 📡 API Overview

## Authentication

| Method | Endpoint |
|---------|----------|
| POST | `/auth/register` |
| POST | `/auth/login` |

---

## Documents

| Method | Endpoint |
|---------|----------|
| POST | `/documents/upload` |
| GET | `/documents/{id}` |
| GET | `/documents` |

---

## Chat

| Method | Endpoint |
|---------|----------|
| POST | `/chat` |
| POST | `/chat/stream` |
| GET | `/chat/sessions` |
| GET | `/chat/sessions/{id}` |

---

# 🚀 Quick Start

```bash
git clone https://github.com/Imteyaz-428/enterprise-rag-platform.git

cd enterprise-rag-platform/backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

uvicorn app:app --reload
```

Create a `.env` file:

```env
DATABASE_URL=

SECRET_KEY=

VOYAGE_API_KEY=

GEMINI_API_KEY=

GROQ_API_KEY=

DEEPSEEK_API_KEY=

REDIS_HOST=localhost
REDIS_PORT=6379
```
---

# 🧪 Example Workflow

```text
Register User
      │
      ▼
Login
      │
      ▼
Upload PDF
      │
      ▼
Background Processing
      │
      ├── Extract Text
      ├── Chunk Document
      ├── Generate Embeddings
      └── Store in pgvector
      │
      ▼
Ask Question
      │
      ▼
Semantic Search
      │
      ▼
Retrieve Relevant Chunks
      │
      ▼
Generate AI Response
      │
      ▼
Store Chat History
      │
      ▼
Return Response with Citations
```

---

# 📸 Screenshots

> *(Add screenshots after completing the frontend.)*

### Authentication

<img width="100%" src="screenshots/login.png">

---

### Dashboard

<img width="100%" src="screenshots/dashboard.png">

---

### Document Upload

<img width="100%" src="screenshots/upload.png">

---

### AI Chat

<img width="100%" src="screenshots/chat.png">

---

### Swagger API

<img width="100%" src="screenshots/swagger.png">

---

# 📊 Project Status

## ✅ Completed

### Backend

- JWT Authentication
- Multi-Tenant Architecture
- RBAC
- User Management
- Organization Management

### Document Processing

- PDF Upload
- PDF Validation
- Background Processing
- Document Status Tracking
- Text Extraction
- Manual Chunking
- Voyage AI Embeddings
- pgvector Integration

### AI & RAG

- Semantic Search
- Multi-Document Retrieval
- Prompt Builder
- Source Citations
- Multi-Provider AI Support
- Retry & Provider Fallback

### Chat

- Persistent Chat Sessions
- Conversation History
- Streaming Responses (SSE)

### Performance

- Redis Caching
- Background Tasks

---

## 🚧 In Progress

- React Frontend
- Docker Compose
- Deployment

---

## 📅 Planned

- Kubernetes Deployment
- Deep Learning Document Classification
- Monitoring & Logging

---

# 🗺️ Roadmap

## ✅ Phase 1 — Backend

- Authentication
- RBAC
- Multi-Tenant Architecture
- Document Processing
- RAG Pipeline
- Chat System
- Streaming Responses
- Redis Caching
- Background Tasks

---

## 🚧 Phase 2 — Frontend

- React Dashboard
- Authentication Pages
- Document Management
- Chat Interface
- Source Citation UI

---

## 📦 Phase 3 — Deployment

- Docker
- Docker Compose
- Frontend Deployment
- Backend Deployment

---

## 🚀 Phase 4 — Production Improvements

- Kubernetes
- Monitoring
- Logging
- Rate Limiting
- CI/CD

---

# 📚 Key Learnings

This project helped me gain practical experience with:

- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Vector Embeddings
- Prompt Engineering
- JWT Authentication
- Multi-Tenant Architecture
- Provider Pattern
- Service Layer Architecture
- Background Tasks
- Redis Caching
- Streaming Responses (SSE)

---

# 🤝 Contributing

Contributions, suggestions, and feedback are welcome.

1. Fork the repository.
2. Create a new branch.
3. Commit your changes.
4. Push to your fork.
5. Open a Pull Request.

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 👨‍💻 Author

**Imteyaz Alam**

B.Tech – Artificial Intelligence & Machine Learning

Backend Developer | AI Engineer

### Connect with Me

- GitHub: https://github.com/Imteyaz-428
- LinkedIn: https://linkedin.com/in/imteyaz428

---

## ⭐ Support

If you found this project useful, please consider giving it a ⭐ on GitHub.