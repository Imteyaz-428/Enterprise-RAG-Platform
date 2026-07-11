# Week 1 - Day 2: Database Design

---

## Q1. Why did you choose PostgreSQL for your Enterprise RAG Platform?

**Answer**

I chose PostgreSQL because it is a powerful open-source relational database that provides:

- ACID compliance for reliable transactions.
- Strong support for relationships.
- Excellent indexing capabilities.
- High performance.
- Support for extensions like **pgvector**, which is essential for storing and searching embeddings in RAG applications.

It allows me to keep both relational data (users, organizations, documents) and vector embeddings in the same database.

---

### Follow-up Question

**Why not use MySQL?**

**Answer**

Both PostgreSQL and MySQL are excellent relational databases.

I chose PostgreSQL because:

- Native support for advanced data types.
- Better support for extensions like pgvector.
- Better suited for AI and data-intensive applications.

---

## Q2. What is a Database Schema?

**Answer**

A database schema is the logical structure of a database.

It defines:

- Tables
- Columns
- Data Types
- Constraints
- Relationships

The schema acts as the blueprint of the database.

---

## Q3. What is a Primary Key?

**Answer**

A Primary Key uniquely identifies each row in a table.

Characteristics:

- Unique
- Cannot be NULL
- Only one Primary Key per table

Example:

```text
Users

id = 1
id = 2
id = 3
```

Each user has a unique identifier.

---

### Follow-up Question

**Can two rows have the same Primary Key?**

**Answer**

No.

The database enforces uniqueness of the Primary Key.

---

## Q4. What is a Foreign Key?

**Answer**

A Foreign Key creates a relationship between two tables.

Example:

```text
Organization
--------------
id = 5

↓

User
--------------
organization_id = 5
```

Here, every user belongs to an organization.

---

### Follow-up Question

**Why do we use Foreign Keys?**

**Answer**

Foreign Keys maintain referential integrity.

They prevent invalid references and ensure related records exist.

---

## Q5. Explain the One-to-Many relationship in your project.

**Answer**

One organization can have multiple users.

```text
Organization

↓

User 1

User 2

User 3
```

But every user belongs to only one organization.

Similarly,

One document can have many document chunks.

---

## Q6. What is an ER Diagram?

**Answer**

ER (Entity Relationship) Diagram is a visual representation of database entities and their relationships.

It helps:

- Understand database structure.
- Identify relationships.
- Plan the database before implementation.

---

## Q7. What is Database Normalization?

**Answer**

Normalization is the process of organizing data to reduce redundancy and improve consistency.

Benefits:

- Eliminates duplicate data.
- Improves data integrity.
- Makes updates easier.

---

## Revision Summary

- PostgreSQL is suitable for relational + vector data.
- Primary Key uniquely identifies a row.
- Foreign Key connects tables.
- One-to-Many relationship is common in enterprise applications.
- ER Diagram helps design the database.
- Normalization reduces redundancy.