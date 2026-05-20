from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.document_schema import DocumentChunkResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    """Retrieve ingested HR document metadata."""
    service = DocumentService(db)
    documents = service.get_documents(limit=limit)

    return [
        DocumentResponse.model_validate(document)
        for document in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Retrieve one ingested HR document by ID."""
    service = DocumentService(db)
    document = service.get_document_by_id(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
) -> list[DocumentChunkResponse]:
    """Retrieve text chunks for one ingested HR document."""
    service = DocumentService(db)
    document = service.get_document_by_id(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = service.get_document_chunks(document_id)

    return [
        DocumentChunkResponse.model_validate(chunk)
        for chunk in chunks
    ]