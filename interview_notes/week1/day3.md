# Week 1 - Day 3: Project Setup

---

## Q1. Why did you choose FastAPI?

**Answer**

I chose FastAPI because it provides:

- High performance.
- Automatic Swagger documentation.
- Built-in request validation using Pydantic.
- Dependency Injection.
- Easy API development.
- Modern async support.

It is one of the most suitable frameworks for backend APIs in AI applications.

---

### Follow-up Question

**Why not Flask or Django?**

**Answer**

Flask is lightweight but requires additional libraries for validation and documentation.

Django is a full-stack framework and includes many features that are unnecessary for an API-only backend.

FastAPI provides excellent performance and built-in features for REST APIs.

---

## Q2. What is SQLAlchemy?

**Answer**

SQLAlchemy is a Python ORM (Object Relational Mapper).

Instead of writing SQL queries manually, we interact with Python objects.

Example:

Instead of writing:

```sql
SELECT * FROM users;
```

We write:

```python
db.query(User).all()
```

SQLAlchemy converts Python code into SQL automatically.

---

### Follow-up Question

**What are the advantages of using an ORM?**

**Answer**

- Cleaner code.
- Better maintainability.
- Database independence.
- Protection against SQL Injection.
- Easier CRUD operations.

---

## Q3. What is SQLAlchemy Engine?

**Answer**

The Engine is responsible for creating and managing connections to the database.

It acts as the communication layer between the application and PostgreSQL.

---

## Q4. What is a Session?

**Answer**

A Session is a workspace for interacting with the database.

It is used to:

- Add records.
- Update records.
- Delete records.
- Execute queries.
- Commit transactions.

Example:

```python
db.add(user)
db.commit()
db.refresh(user)
```

---

### Follow-up Question

**Why do we commit a session?**

**Answer**

Changes remain temporary until `commit()` is called.

`commit()` permanently saves changes to the database.

---

## Q5. What is Dependency Injection in FastAPI?

**Answer**

Dependency Injection allows FastAPI to automatically provide required objects to route functions.

Example:

```python
db: Session = Depends(get_db)
```

FastAPI automatically creates and closes the database session.

Benefits:

- Cleaner code.
- Reusable dependencies.
- Better testing.

---

## Q6. Why did you separate Models, Schemas, CRUD, and Routes?

**Answer**

This follows the Separation of Concerns principle.

Each layer has a different responsibility.

**Models**
- Database tables.

**Schemas**
- Request and response validation.

**CRUD**
- Database operations.

**Routes**
- API endpoints.

This architecture improves readability, maintainability, and scalability.

---

### Follow-up Question

**Why not write everything inside one file?**

**Answer**

For small projects it is possible.

However, enterprise applications become difficult to maintain if everything is placed in one file.

Separating responsibilities makes the project modular and easier to scale.

---

## Q7. What is Swagger?

**Answer**

Swagger is an automatically generated API documentation interface.

It allows developers to:

- View all endpoints.
- Test APIs.
- Read request and response schemas.
- Debug APIs without external tools.

FastAPI generates Swagger automatically.

---

## Revision Summary

- FastAPI is a high-performance API framework.
- SQLAlchemy is an ORM.
- Engine manages database connections.
- Session performs database operations.
- Dependency Injection provides reusable objects.
- Project structure improves maintainability.
- Swagger simplifies API testing and documentation.