from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Document metadata returned through the API."""

    id: int
    title: str
    document_type: str
    filename: str
    source_path: str
    source: str
    content_hash: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class DocumentChunkResponse(BaseModel):
    """Document chunk returned through the API."""

    id: int
    document_id: int
    chunk_index: int
    content: str
    token_estimate: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }