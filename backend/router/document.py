from fastapi import UploadFile, File, Form, APIRouter,Depends, HTTPException
from pathlib import Path
import shutil
import uuid
from models.document import Document
from crud.document import create_document
from models.user import User
from core.dependencies import get_current_user
from dependencies.database import get_db
from sqlalchemy.orm import Session
from schemas.document import DocumentResponse
from utils.pdf import extract_text_from_pdf
from utils.chunker import chunk_text
from utils.embedding import generate_embeddings
from crud.document_chunk import create_document_chunk

UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@router.post( "/upload", response_model=DocumentResponse)

def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )
    
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB."
        )
    
    if file.size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )
    
    extension = Path(file.filename).suffix
    stored_filename = f"{uuid.uuid4()}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
    title=title,
    original_filename=file.filename,
    stored_filename=stored_filename,
    file_path=str(file_path),
    file_size=file.size,
    organization_id=current_user.organization_id,
    uploaded_by=current_user.id)
    
    
    saved_document = create_document(db=db,document=document)
    text = extract_text_from_pdf(str(file_path))

    chunks = chunk_text(text)

    embeddings = generate_embeddings(chunks)

    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        create_document_chunk(
            db=db,
            document_id=saved_document.id,
            chunk_index=index,
            chunk_text=chunk,
            embedding=embedding
        )
        
    return saved_document