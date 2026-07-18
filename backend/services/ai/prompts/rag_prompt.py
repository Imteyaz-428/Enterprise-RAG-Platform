from models.document_chunk import DocumentChunk


def build_rag_prompt(
    question: str,
    chunks: list[DocumentChunk]
) -> str:

    context = "\n\n".join(
        chunk.chunk_text
        for chunk in chunks
    )

    return f"""

You are a helpful AI assistant.

Use ONLY the information provided in the context below to answer the user's question.

Guidelines:

- Do not use outside knowledge.

- If the answer is not present in the context, respond:

  "I couldn't find the answer in the uploaded documents."

- Keep the answer clear, concise, and accurate.

- If appropriate, summarize information instead of copying it verbatim.

Context:

{context}

Question:

{question}

Answer:
""".strip()