# Week 1 - Day 7: Document Management

---

## Q1. Why did you create a Document model?

**Answer**

The Document model stores metadata about uploaded files.

Instead of storing the actual PDF inside the database, we store information such as:

- Title
- Original Filename
- Stored Filename
- File Path
- File Size
- Upload Time
- Organization
- Uploaded By

This keeps the database lightweight while allowing efficient file management.

---

## Q2. Why don't we store PDFs directly inside PostgreSQL?

**Answer**

Storing large files inside the database increases database size and reduces performance.

Instead:

- Store the PDF on disk (or cloud storage).
- Store only metadata inside PostgreSQL.

Benefits:

- Better performance
- Easier backups
- Better scalability

---

## Q3. Why do we use UUID for file names?

**Answer**

UUID guarantees that every uploaded file has a unique filename.

Example:

```text
Original:
resume.pdf

Stored:
550e8400-e29b-41d4-a716-446655440000.pdf
```

Benefits:

- Prevents filename collisions
- Improves security
- Avoids accidental overwrites

---

## Q4. Why do we validate uploaded files?

**Answer**

Validation protects the application.

Checks performed:

- File type (PDF only)
- File size
- Empty files

Benefits:

- Better security
- Prevents invalid uploads
- Saves storage

---

### Follow-up Question

**Why shouldn't we trust the client?**

**Answer**

A client can send:

- Wrong file types
- Extremely large files
- Malicious files

Server-side validation ensures only valid files are processed.

---

## Q5. Why did you use PyMuPDF?

**Answer**

PyMuPDF is a fast and efficient library for extracting text from PDF documents.

After upload:

```text
PDF
   │
   ▼
PyMuPDF
   │
   ▼
Extracted Text
```

The extracted text is later used for chunking and embedding generation.

---

## Q6. What is the difference between storing metadata and storing file content?

**Answer**

Metadata contains information **about** the file.

Example:

- Title
- File Path
- Upload Time
- File Size

File content is the actual PDF data.

In our project:

- Metadata → PostgreSQL
- PDF File → Local Storage

---

## Q7. Why is Document related to Organization?

**Answer**

Each uploaded document belongs to an organization.

This supports multi-tenancy.

Example:

```text
Organization A
├── PDF 1
├── PDF 2

Organization B
├── PDF 3
```

Users can only access documents belonging to their own organization.

---

## Q8. Why is Document related to User?

**Answer**

Each document stores who uploaded it.

Benefits:

- Audit trail
- Ownership
- User activity tracking

Example:

```text
Document

↓

Uploaded By

↓

User
```

---

## Q9. Explain the Document Upload Flow.

**Answer**

```text
User Uploads PDF
        │
        ▼
Validate File
        │
        ▼
Generate UUID Filename
        │
        ▼
Store PDF
        │
        ▼
Save Metadata in PostgreSQL
        │
        ▼
Extract Text using PyMuPDF
```

This prepares the document for the RAG pipeline.

---

## Revision Summary

- Document Metadata
- File Storage
- UUID Filenames
- PDF Validation
- PyMuPDF
- Metadata vs File Content
- Organization Relationship
- User Relationship
- Document Upload Flow