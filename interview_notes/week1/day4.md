# Week 1 - Day 4: Organization Module

---

## Q1. Why did you create a separate Organization model?

**Answer**

In an Enterprise RAG Platform, multiple organizations (tenants) can use the same application.

Instead of storing all users and documents together, each organization has its own data.

Example:

```text
Organization A
├── Users
├── Documents
└── Chat History

Organization B
├── Users
├── Documents
└── Chat History
```

This design supports **multi-tenancy**, where each organization's data remains isolated.

---

### Follow-up Question

**What is Multi-Tenancy?**

**Answer**

Multi-tenancy is an architecture where a single application serves multiple organizations (tenants), while keeping each tenant's data isolated and secure.

For example:

- Company A cannot access Company B's documents.
- Each organization has its own users and uploaded PDFs.

---

## Q2. Why did you use SQLAlchemy Models?

**Answer**

SQLAlchemy Models define how data is stored in the database.

Each model represents a database table.

Example:

```python
class Organization(Base):
    __tablename__ = "organizations"
```

SQLAlchemy automatically maps the Python class to the PostgreSQL table.

---

## Q3. Why did you create Pydantic Schemas if SQLAlchemy Models already exist?

**Answer**

SQLAlchemy Models and Pydantic Schemas have different responsibilities.

**SQLAlchemy Models**
- Define database structure.
- Store data in PostgreSQL.

**Pydantic Schemas**
- Validate incoming requests.
- Format outgoing responses.

Keeping them separate improves security, validation, and maintainability.

---

### Follow-up Question

**Can we use SQLAlchemy Models directly in API requests?**

**Answer**

Technically possible, but not recommended.

Reasons:

- No proper request validation.
- Database structure becomes exposed.
- Difficult to control request/response fields.

Using Pydantic Schemas keeps the API independent of the database implementation.

---

## Q4. Why did you separate CRUD operations from Routes?

**Answer**

Routes should only handle HTTP requests and responses.

Business logic should be placed inside CRUD functions.

Benefits:

- Cleaner routes.
- Better code reuse.
- Easier testing.
- Better maintainability.

---

### Follow-up Question

**What happens if CRUD logic is written inside routes?**

**Answer**

Routes become very large and difficult to maintain.

Business logic gets duplicated across endpoints.

Testing also becomes more difficult.

---

## Q5. What is `relationship()` in SQLAlchemy?

**Answer**

`relationship()` defines how two models are connected.

Example:

```python
organization = relationship(
    "Organization",
    back_populates="users"
)
```

Now SQLAlchemy allows:

```python
organization.users
```

instead of manually writing SQL JOIN queries.

---

## Q6. What is `back_populates`?

**Answer**

`back_populates` creates a two-way relationship.

Example:

```text
Organization

↓

Users
```

From Organization:

```python
organization.users
```

From User:

```python
user.organization
```

Both sides remain synchronized.

---

## Q7. Why do we validate input?

**Answer**

Validation ensures only correct data enters the application.

Examples:

- Empty organization name
- Invalid slug
- Duplicate organization

Validation prevents bad data from reaching the database.

---

## Revision Summary

- Multi-Tenancy
- SQLAlchemy Models
- Pydantic Schemas
- CRUD Pattern
- SQLAlchemy Relationships
- back_populates
- Input Validation