from models.document_chunk import DocumentChunk


def build_prompt(
    question: str,
    chunks: list[DocumentChunk]
) -> str:

    context = "\n\n".join(
        chunk.chunk_text
        for chunk in chunks
    )

    return f"""
You are an AI assistant for an Enterprise RAG Platform.

Answer ONLY using the provided context.

If the answer cannot be found in the context, say:

"I couldn't find the answer in the uploaded documents."

Context:
{context}

Question:
{question}

Answer:
""".strip()