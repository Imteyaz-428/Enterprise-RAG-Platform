# Enterprise RAG Platform - Interview Notes

---

# Week 1

## Day 1 - Project Planning

### Q1. What is the difference between Functional and Non-Functional Requirements?

**Answer**

Functional Requirements define **what the system should do**.

Examples:
- User Registration
- User Login
- Upload PDF
- Chat with Documents

Non-Functional Requirements define **how the system should perform**.

Examples:
- Security
- Scalability
- Performance
- Reliability
- Availability

> **Interview Tip**
>
> Functional = Features
>
> Non-Functional = Quality Attributes

---

### Q2. Why do we design the System Architecture before coding?

**Answer**

System Architecture acts as the blueprint of the application. It defines:

- Major components
- Communication between components
- Data flow
- Technology choices

Designing the architecture before implementation reduces development mistakes and makes the system easier to scale and maintain.

---

### Q3. Explain the architecture of your Enterprise RAG Platform.

**Answer**

The project follows a layered architecture.

```text
Client
   │
   ▼
FastAPI (Routes)
   │
   ▼
CRUD Layer (Business Logic)
   │
   ▼
SQLAlchemy ORM
   │
   ▼
PostgreSQL + pgvector
```

Each layer has a single responsibility, making the application modular and maintainable.

---

### Follow-up Question

**Why didn't you write database queries directly inside the routes?**

**Answer**

Separating business logic from routes follows the Separation of Concerns principle.

Benefits:

- Better readability
- Easier testing
- Reusable CRUD functions
- Cleaner architecture

---

### Revision Summary

- Functional Requirements → What the system does
- Non-Functional Requirements → How well the system performs
- System Architecture → Blueprint of the application
- Layered Architecture → Better maintainability