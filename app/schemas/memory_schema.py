from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    """Request body for manually adding memory."""

    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    memory_type: str = Field(..., pattern="^(stm|ltm)$")
    significance: float | None = Field(default=None, ge=0.0, le=1.0)


class MemoryRecord(BaseModel):
    """Memory record returned through the API."""

    id: int
    user_id: str
    content: str
    memory_type: str
    significance: float | None = None
    created_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class UserMemoryResponse(BaseModel):
    """All memory records for a given user."""

    user_id: str
    short_term_memory: list[MemoryRecord]
    long_term_memory: list[MemoryRecord]