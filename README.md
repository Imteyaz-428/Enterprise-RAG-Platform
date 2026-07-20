# 🚀 Enterprise Multi-Tenant RAG Platform

> A production-ready, multi-tenant Retrieval-Augmented Generation (RAG) platform that enables organizations to build a secure AI-powered knowledge base from their documents using semantic search and Large Language Models.

![Status](https://img.shields.io/badge/Status-Active%20Development-blue)
![Backend](https://img.shields.io/badge/FastAPI-Enterprise-green)
![Database](https://img.shields.io/badge/PostgreSQL-pgvector-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

---

# 📖 Overview

The **Enterprise Multi-Tenant RAG Platform** is a production-oriented backend system designed to simulate how modern enterprises build secure AI-powered knowledge management systems.

Organizations can upload PDF documents, automatically process them into vector embeddings, and interact with their private knowledge base through natural language conversations.

Unlike a traditional chatbot, this platform retrieves the most relevant document sections using semantic search before generating responses, reducing hallucinations and improving answer accuracy.

The project follows enterprise backend principles including:

- Multi-Tenant Architecture
- Clean Service Layer Architecture
- Dependency Injection
- Provider Pattern
- Enterprise Authentication & Authorization
- Modular AI Integration
- Scalable RAG Pipeline

This project is being built as a production-level portfolio project to demonstrate enterprise backend engineering, AI integration, and Retrieval-Augmented Generation (RAG) concepts.

---

# ✨ Key Features

## 🔐 Authentication & Security

- JWT Authentication
- OAuth2 Bearer Authentication
- Secure Password Hashing (bcrypt)
- Role-Based Access Control (RBAC)
- Protected REST APIs
- Organization-level Data Isolation

---

## 🏢 Multi-Tenant Architecture

- Organization Management
- Complete Tenant Isolation
- Organization-specific Users
- Organization-specific Documents
- Secure Data Access
- Multi-Document Knowledge Base

---

## 👥 User Management

- User Registration
- Secure Login
- Current User API
- Admin & Employee Roles
- Profile Management

---

## 📄 Document Management

- Secure PDF Upload
- PDF Validation
- Metadata Storage
- UUID-based File Storage
- Organization-specific Documents
- PostgreSQL Metadata Management

---

## 📚 Document Processing Pipeline

- PDF Text Extraction using PyMuPDF
- Manual Text Chunking
- Chunk Overlap Strategy
- Configurable Chunk Size
- Chunk Metadata Storage

---

## 🧠 AI & Retrieval-Augmented Generation (RAG)

- Voyage AI Embeddings
- pgvector Integration
- Semantic Search
- Cosine Similarity Search
- Multi-Document Retrieval
- Query Embedding Generation
- Prompt Engineering
- Hallucination Prevention
- Enterprise RAG Pipeline

---

## 🤖 Enterprise AI Service

- Provider Abstraction
- Gemini Integration
- Groq Integration
- DeepSeek Integration
- Retry Mechanism
- Automatic Provider Fallback
- Lazy Initialization
- Provider Instance Caching
- Centralized AI Service

---

## 💬 Conversation System

- Persistent Chat Sessions
- Conversation History
- Multi-turn Conversations
- Automatic Session Creation
- Chat Title Generation
- Chat Session Management APIs

---

## 🏗️ Enterprise Backend Architecture

- Clean Service Layer
- CRUD Layer
- Dependency Injection
- Separation of Concerns
- Orchestrator Pattern
- Provider Pattern
- Repository-style CRUD Organization

---

# 🚀 Current Features

### ✅ Authentication

- JWT Login
- Protected APIs
- RBAC
- Current User Authentication

### ✅ Organization Management

- Create Organization
- Update Organization
- Delete Organization
- Organization Isolation

### ✅ User Management

- User CRUD
- Login
- Password Hashing
- Role Management

### ✅ Document Management

- Upload PDF
- Validate PDF
- Extract Text
- Store Metadata

### ✅ AI Pipeline

- Voyage Embeddings
- pgvector
- Semantic Search
- Prompt Builder
- AI Response Generation

### ✅ Enterprise Chat

- Chat Sessions
- Conversation History
- Multi-turn Chat
- Multi-document Retrieval

---

# 🚧 Upcoming Features

- Source Citations
- React Chat Dashboard
- Streaming AI Responses
- Redis Caching
- LangChain Integration
- Deep Learning Document Classification
- Docker Deployment
- Kubernetes Deployment
- Monitoring & Logging

---

# 🏗️ System Architecture

```text
                           User
                             │
                             ▼
                    JWT Authentication
                             │
                             ▼
                 Role-Based Authorization
                             │
                             ▼
                    FastAPI Router Layer
                             │
                             ▼
                      ChatService Layer
                             │
         ┌───────────────────┴────────────────────┐
         ▼                                        ▼
  Session Management                    Retrieval Service
         │                                        │
         ▼                                        ▼
 Message Management                    Semantic Vector Search
                                                  │
                                                  ▼
                                           Prompt Service
                                                  │
                                                  ▼
                                              AI Service
                                                  │
                            ┌───────────────┬───────────────┬───────────────┐
                            ▼               ▼               ▼
                         Gemini           Groq          DeepSeek
                                                  │
                                                  ▼
                                        AI Generated Response
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
                 Manual Chunking
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
          Create / Load Chat Session
                          │
                          ▼
         Retrieve Conversation History
                          │
                          ▼
          Generate Query Embedding
                          │
                          ▼
             Semantic Vector Search
                          │
                          ▼
            Retrieve Top-K Chunks
                          │
                          ▼
               Build RAG Prompt
                          │
                          ▼
                  AI Service Layer
                          │
                          ▼
        Gemini / Groq / DeepSeek Provider
                          │
                          ▼
              Generate AI Response
                          │
                          ▼
          Store Assistant Response
                          │
                          ▼
               Return Final Answer
```

---

# 🎯 Enterprise Design Goals

This project focuses on implementing real-world backend engineering practices rather than simply building a chatbot.

Key design goals include:

- Enterprise-grade architecture
- Multi-tenant security
- Scalable AI integration
- Production-ready RAG pipeline
- Modular service-based design
- High maintainability
- Clean separation of responsibilities
- Extensible provider architecture
- Efficient semantic retrieval
- Reliable AI response generation


# 🛠️ Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- JWT Authentication
- OAuth2
- bcrypt

---

## Database

- PostgreSQL
- pgvector

---

## AI & RAG

- Voyage AI
- Gemini
- Groq
- DeepSeek
- PyMuPDF

---

## Architecture & Design

- Multi-Tenant Architecture
- Service Layer Architecture
- Dependency Injection
- Provider Pattern
- Strategy Pattern
- Orchestrator Pattern
- Repository-style CRUD
- Separation of Concerns (SoC)

---

## Development Tools

- Docker (Upcoming)
- Kubernetes (Upcoming)
- Git
- GitHub
- VS Code
- pgAdmin

---

# 📂 Project Structure

```text
backend/
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── enums.py
│
├── crud/
│   ├── organization.py
│   ├── user.py
│   ├── document.py
│   ├── document_chunk.py
│   ├── chat_session.py
│   └── chat_message.py
│
├── database/
│   └── database.py
│
├── dependencies/
│   └── database.py
│
├── models/
│   ├── organization.py
│   ├── user.py
│   ├── document.py
│   ├── document_chunk.py
│   ├── chat_session.py
│   └── chat_message.py
│
├── router/
│   ├── auth.py
│   ├── organization.py
│   ├── user.py
│   ├── document.py
│   └── chat.py
│
├── schemas/
│   ├── auth.py
│   ├── organization.py
│   ├── user.py
│   ├── document.py
│   ├── document_chunk.py
│   ├── chat.py
│   ├── chat_session.py
│   └── chat_message.py
│
├── services/
│   ├── ai/
│   │   ├── ai_service.py
│   │   ├── provider.py
│   │   ├── gemini_provider.py
│   │   ├── groq_provider.py
│   │   ├── deepseek_provider.py
│   │   ├── retry.py
│   │   └── config.py
│   │
│   └── chat/
│       ├── chat_service.py
│       ├── retrieval_service.py
│       └── prompt_service.py
│
├── utils/
│   ├── embedding.py
│   ├── chunking.py
│   ├── pdf.py
│   └── logger.py
│
├── uploads/
│
├── app.py
│
├── requirements.txt
│
└── .env
```

---

# 🌐 API Endpoints

## Authentication

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Authenticate user and generate JWT |

---

## Organizations

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/organizations` | Create organization |
| GET | `/organizations` | Get organizations |
| PUT | `/organizations/{id}` | Update organization |
| DELETE | `/organizations/{id}` | Delete organization |

---

## Users

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/users` | Create user |
| GET | `/users/me` | Get current user profile |

---

## Documents

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/documents/upload` | Upload PDF |
| GET | `/documents` | Get uploaded documents |

---

## Chat

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/chat` | Ask questions to the knowledge base |
| GET | `/chat/sessions` | List all chat sessions |
| GET | `/chat/sessions/{session_id}` | Load conversation history |
| DELETE | `/chat/sessions/{session_id}` | Delete a chat session |

---

# 💬 Example Chat Request

### New Conversation

```json
{
    "question": "What is the leave policy?"
}
```

---

### Continue Existing Conversation

```json
{
    "session_id": 5,
    "question": "How many casual leaves are allowed?"
}
```

---

# 💬 Example Response

```json
{
    "session_id": 5,
    "answer": "Employees are entitled to 12 casual leaves per year."
}
```

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/your-username/enterprise-rag-platform.git
```

---

## Navigate to Project

```bash
cd enterprise-rag-platform/backend
```

---

## Create Virtual Environment

```bash
python -m venv .venv
```

---

## Activate Virtual Environment

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file.

```env
DATABASE_URL=postgresql://username:password@localhost/database

SECRET_KEY=your_secret_key

ALGORITHM=HS256

VOYAGE_API_KEY=your_voyage_api_key

GEMINI_API_KEY=your_gemini_api_key

GROQ_API_KEY=your_groq_api_key

DEEPSEEK_API_KEY=your_deepseek_api_key
```

---

## Run the Application

```bash
uvicorn app:app --reload
```

---

# 📖 API Documentation

After starting the server, open:

```
http://localhost:8000/docs
```

FastAPI automatically generates an interactive Swagger UI where every endpoint can be tested directly.

---

# 🧪 Example Workflow

```
1. Register User
        │
        ▼
2. Login
        │
        ▼
3. Upload PDF
        │
        ▼
4. PDF Processing
        │
        ▼
5. Generate Embeddings
        │
        ▼
6. Store Vector Embeddings
        │
        ▼
7. Ask Question
        │
        ▼
8. Semantic Retrieval
        │
        ▼
9. AI Response
        │
        ▼
10. Conversation Saved
```

# 📊 Current Progress

## ✅ Core Backend

- [x] FastAPI Project Setup
- [x] PostgreSQL Integration
- [x] SQLAlchemy ORM
- [x] Pydantic Schemas
- [x] CRUD Layer
- [x] Dependency Injection
- [x] Environment Configuration

---

## ✅ Authentication & Authorization

- [x] JWT Authentication
- [x] OAuth2 Bearer Authentication
- [x] Password Hashing (bcrypt)
- [x] User Registration
- [x] User Login
- [x] Current User API
- [x] Role-Based Access Control (RBAC)

---

## ✅ Multi-Tenant Architecture

- [x] Organization Management
- [x] Organization Isolation
- [x] Organization-specific Users
- [x] Organization-specific Documents
- [x] Secure Resource Authorization

---

## ✅ Document Management

- [x] PDF Upload
- [x] PDF Validation
- [x] Metadata Storage
- [x] UUID-based File Storage
- [x] PostgreSQL Integration

---

## ✅ PDF Processing

- [x] Text Extraction (PyMuPDF)
- [x] Manual Chunking
- [x] Chunk Metadata Storage
- [x] Configurable Chunk Size
- [x] Configurable Chunk Overlap

---

## ✅ AI & Retrieval-Augmented Generation

- [x] Voyage AI Embeddings
- [x] pgvector Integration
- [x] Vector Storage
- [x] Semantic Search
- [x] Cosine Similarity Search
- [x] Query Embeddings
- [x] Multi-Document Retrieval
- [x] Prompt Builder
- [x] Retrieval-Augmented Generation (RAG)

---

## ✅ Enterprise AI Service

- [x] Provider Abstraction
- [x] Gemini Integration
- [x] Groq Integration
- [x] DeepSeek Integration
- [x] Retry Mechanism
- [x] Automatic Provider Fallback
- [x] Lazy Initialization
- [x] Provider Instance Caching

---

## ✅ Conversation Management

- [x] Persistent Chat Sessions
- [x] Conversation History
- [x] Multi-turn Conversations
- [x] Session Management APIs
- [x] Automatic Chat Title Generation

---

## 🚧 In Progress

- [ ] Source Citations
- [ ] Streaming AI Responses

---

## 📅 Planned Features

- [ ] React Frontend
- [ ] Redis Caching
- [ ] LangChain Integration
- [ ] Docker Deployment
- [ ] Kubernetes Deployment
- [ ] Monitoring & Logging
- [ ] Deep Learning Document Classification

---

# 🏛️ Architecture Highlights

This project follows a production-oriented layered architecture to ensure scalability, maintainability, and clean separation of responsibilities.

### Multi-Tenant Architecture

Every organization has its own isolated users, documents, conversations, and AI knowledge base.

---

### Service Layer

Business logic is separated from API routes, making the application modular and easier to maintain.

---

### CRUD Layer

Database operations are isolated inside dedicated CRUD modules, keeping services independent of ORM implementation.

---

### Dependency Injection

FastAPI's dependency injection system is used to provide database sessions, authentication, and reusable services.

---

### Provider Pattern

Multiple LLM providers share a common interface, making it easy to switch or add providers.

Current providers include:

- Gemini
- Groq
- DeepSeek

---

### Orchestrator Pattern

The `ChatService` coordinates multiple specialized services:

- RetrievalService
- PromptService
- AIService

Each service has a single responsibility, resulting in cleaner and more maintainable code.

---

### Semantic Search

Instead of keyword matching, the platform retrieves information using vector similarity search powered by pgvector and Voyage AI embeddings.

---

### Enterprise Security

Security is enforced through:

- JWT Authentication
- OAuth2 Bearer Tokens
- Role-Based Authorization
- Organization Isolation
- Resource Ownership Validation

---

# 📚 Key Concepts Learned

Building this project provided hands-on experience with:

### Backend Development

- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- REST API Design
- Dependency Injection

---

### Artificial Intelligence

- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Vector Embeddings
- Prompt Engineering
- Large Language Model Integration

---

### Enterprise Software Engineering

- Multi-Tenant Architecture
- Service Layer Design
- Provider Pattern
- Orchestrator Pattern
- Repository-style CRUD
- Separation of Concerns
- Clean Architecture
- Scalable Backend Design

---

### Database

- PostgreSQL
- pgvector
- Vector Similarity Search
- Database Relationships
- SQL JOINs

---

### Security

- JWT Authentication
- OAuth2
- RBAC
- Password Hashing
- Secure API Design

---

# 🛣️ Roadmap

## Phase 1 — Core Backend ✅

- Authentication
- RBAC
- Multi-Tenant Architecture
- Document Upload
- PDF Processing
- Vector Database
- Semantic Search
- Enterprise AI Service
- Chat System

---

## Phase 2 — AI Enhancements 🚧

- Source Citations
- Streaming Responses
- Conversation Memory Improvements
- Better Prompt Optimization

---

## Phase 3 — Frontend

- React Dashboard
- Chat Interface
- Document Management UI
- Organization Dashboard
- Authentication Pages

---

## Phase 4 — Production Deployment

- Docker
- Docker Compose
- Kubernetes
- Nginx
- CI/CD Pipeline

---

## Phase 5 — Scalability

- Redis Caching
- Background Workers
- Async Processing
- Monitoring & Logging
- Rate Limiting

---

## Phase 6 — Advanced AI

- LangChain Integration
- Hybrid Search
- Deep Learning Document Classification
- Document Summarization
- Knowledge Graph Integration

---

# 🤝 Contributing

Contributions, suggestions, and feedback are always welcome.

If you'd like to improve this project:

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push to your fork.
5. Open a Pull Request.

---

# ⭐ Support

If you found this project helpful or interesting:

⭐ Star the repository

🍴 Fork the project

💬 Share your feedback

Your support helps motivate future improvements and open-source contributions.

---

# 📄 License

This project is licensed under the **MIT License**.

You are free to use, modify, and distribute this project under the terms of the MIT License.

---

# 👨‍💻 Author

**Imteyaz Alam**

B.Tech (Artificial Intelligence & Machine Learning)

Backend Developer • AI Engineer

### Connect with Me

- LinkedIn: https://linkedin.com/in/imteyaz428
- GitHub: https://github.com/Imteyaz-428

---

## ⭐ If you like this project, consider giving it a star on GitHub!