# Week 3 - Day 4 Interview Notes

## What are Background Tasks?

Background Tasks execute time-consuming work after sending the response to the client.

---

## Why did you use Background Tasks?

- Faster response.
- Better user experience.
- Avoids making users wait for PDF processing.

---

## Why not process the PDF inside the request?

Large PDFs take time to process. Background Tasks keep the API responsive.

---

## Why create a new database session?

The request session is closed after the response. The background task creates its own `SessionLocal` to safely access the database.

---

## What document statuses did you implement?

- processing
- completed
- failed

---

## What happens when processing fails?

The exception is logged, the document status is updated to `failed`, and the database session is closed.

---

## How will the frontend know when processing is complete?

The frontend calls:

GET `/documents/{document_id}`

every few seconds (polling) until the status changes from `processing` to `completed` or `failed`.

---

## Background Processing Flow

Upload PDF

↓

Save Document

↓

Return Response

↓

Background Task

↓

Extract Text

↓

Chunk Text

↓

Generate Embeddings

↓

Store Chunks

↓

Update Status

---

## Interview Questions

### Q1. What are Background Tasks?
They execute long-running work after returning the API response.

### Q2. Why did you use them?
To make document uploads faster and improve user experience.

### Q3. Why create a new database session?
Because the request session is closed after the response.

### Q4. Why track document status?
So the frontend knows whether processing is in progress, completed, or failed.

### Q5. How does the frontend know when processing finishes?
By polling the document status endpoint until it changes.