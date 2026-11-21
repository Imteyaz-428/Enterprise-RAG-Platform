import hashlib
from fastapi import (
    UploadFile,
    File,
    Form,
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
)
from pathlib import Path
import shutil
import uuid
from sqlalchemy.orm import Session

from models.document import Document
from models.user import User
from schemas.document import DocumentResponse

from crud.document import (
    create_document,
    get_document_by_id,
    delete_document,
    get_documents,
    get_accessible_document,
    get_document_by_hash,
)

from core.dependencies import (
    get_current_user,
    require_role,
    has_role,
    is_platform_admin,
    UserRole,
)
from dependencies.database import get_db
from services.background.document_processor import process_document

UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentResponse,
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MANAGER)),
):
    if not has_role(current_user, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required",
        )
    title = file.filename.rsplit(".", 1)[0]
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB.",
        )

    if file.size is not None and file.size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty.",
        )

    # Verify %PDF- magic bytes
    file.file.seek(0)
    magic = file.file.read(5)
    if magic != b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file format.",
        )

    # Compute sha256
    file.file.seek(0)
    hasher = hashlib.sha256()
    total_bytes = 0
    while chunk := file.file.read(65536):
        hasher.update(chunk)
        total_bytes += len(chunk)

    if total_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB.",
        )

    if total_bytes == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty.",
        )

    file_hash = hasher.hexdigest()
    file_size = file.size if file.size is not None else total_bytes

    # Check for duplicate within the SAME organization
    duplicate_doc = get_document_by_hash(
        db=db,
        organization_id=current_user.organization_id,
        file_hash=file_hash,
    )
    if duplicate_doc:
        raise HTTPException(
            status_code=409,
            detail="A document with this content already exists in your organization.",
        )

    extension = Path(file.filename).suffix or ".pdf"
    stored_filename = f"{uuid.uuid4()}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    file.file.seek(0)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
        title=title,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_size=file_size,
        file_hash=file_hash,
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
    )

    saved_document = create_document(
        db=db,
        document=document,
    )

    background_tasks.add_task(
        process_document,
        saved_document.id,
        str(file_path),
    )

    return saved_document


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_by_id(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if (
        document.organization_id
        != current_user.organization_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied."
        )

    return document


@router.get(
    "",
    response_model=list[DocumentResponse],
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_documents(
        db=db,
        organization_id=current_user.organization_id,
    )


@router.delete("/{document_id}")
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MANAGER)),
):
    if not has_role(current_user, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required",
        )

    is_platform = is_platform_admin(current_user)
    doc = get_document_by_id(
        db=db,
        document_id=document_id,
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if not is_platform and doc.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied.",
        )

    delete_document(
        db=db,
        document=doc,
    )

    return {
        "message": "Document deleted successfully"
    }
