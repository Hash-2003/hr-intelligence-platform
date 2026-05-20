from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.memory_schema import MemoryCreate, MemoryRecord, UserMemoryResponse
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post("", response_model=MemoryRecord)
def create_memory(
    payload: MemoryCreate,
    db: Session = Depends(get_db),
) -> MemoryRecord:
    """Manually add short-term or long-term memory for testing."""
    service = MemoryService(db)

    if payload.memory_type == "stm":
        memory = service.add_short_term_memory(
            user_id=payload.user_id,
            content=payload.content,
            intent=None,
        )

        return MemoryRecord(
            id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            memory_type="stm",
            significance=None,
            created_at=memory.created_at,
        )

    significance = payload.significance if payload.significance is not None else 0.5

    memory = service.add_long_term_memory(
        user_id=payload.user_id,
        content=payload.content,
        significance_score=significance,
    )

    return MemoryRecord(
        id=memory.id,
        user_id=memory.user_id,
        content=memory.content,
        memory_type="ltm",
        significance=memory.significance_score,
        created_at=memory.created_at,
    )


@router.get("/{user_id}", response_model=UserMemoryResponse)
def get_user_memory(
    user_id: str,
    db: Session = Depends(get_db),
) -> UserMemoryResponse:
    """Retrieve short-term and long-term memory for a user."""
    service = MemoryService(db)

    stm_records = service.get_short_term_memory(user_id)
    ltm_records = service.get_long_term_memory(user_id)

    short_term = [
        MemoryRecord(
            id=record.id,
            user_id=record.user_id,
            content=record.content,
            memory_type="stm",
            significance=None,
            created_at=record.created_at,
        )
        for record in stm_records
    ]

    long_term = [
        MemoryRecord(
            id=record.id,
            user_id=record.user_id,
            content=record.content,
            memory_type="ltm",
            significance=record.significance_score,
            created_at=record.created_at,
        )
        for record in ltm_records
    ]

    return UserMemoryResponse(
        user_id=user_id,
        short_term_memory=short_term,
        long_term_memory=long_term,
    )