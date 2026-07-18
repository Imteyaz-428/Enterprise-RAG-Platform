from sqlalchemy.orm import Session
from fastapi import HTTPException
from crud.document_chunk import search_similar_chunks
from services.ai import ai_service
from services.ai.prompts.rag_prompt import build_rag_prompt
from utils.embedding import generate_embedding
from schemas.chat import ChatResponse
from models.user import User
from crud.document import  get_accessible_document


def generate_rag_answer(db: Session,current_user: User,document_id: int,question: str) -> ChatResponse:
    # check access
    document = get_accessible_document(
        db=db,
        document_id=document_id,
        organization_id=current_user.organization_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found or access denied."
        )


    # Step 1: Generate embedding for the user's question
    query_embedding = generate_embedding(question)

    # Step 2: Retrieve similar chunks
    chunks = search_similar_chunks(
        db=db,
        document_id=document_id,
        query_embedding=query_embedding,
    )

    # Step 3: Handle no results
    if not chunks:
        return ChatResponse(
            answer="I couldn't find any relevant information in the uploaded document."
        )

    # Step 4: Build prompt
    prompt = build_rag_prompt(
        question=question,
        chunks=chunks,
    )

    # Step 5: Generate answer
    

    answer = ai_service.generate_answer(prompt)

    # Step 6: Return response
    return ChatResponse(
        answer=answer
    )