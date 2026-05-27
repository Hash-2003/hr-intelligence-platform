from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.draft_schema import DraftResponseOut, DraftUpdateRequest
from app.services.draft_response_service import DraftResponseService

router = APIRouter(prefix="/drafts", tags=["Draft Responses"])


@router.get("", response_model=list[DraftResponseOut])
def get_drafts(
    status: str | None = None,
    review_required: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[DraftResponseOut]:
    """Retrieve draft responses."""
    service = DraftResponseService(db)
    drafts = service.get_drafts(
        status=status,
        review_required=review_required,
        limit=limit,
    )

    return [
        DraftResponseOut.model_validate(draft)
        for draft in drafts
    ]


@router.get("/{draft_id}", response_model=DraftResponseOut)
def get_draft(
    draft_id: str,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Retrieve one draft response."""
    service = DraftResponseService(db)
    draft = service.get_draft_by_id(draft_id)

    if draft is None:
        raise HTTPException(status_code=404, detail="Draft response not found.")

    return DraftResponseOut.model_validate(draft)


@router.patch("/{draft_id}", response_model=DraftResponseOut)
def update_draft(
    draft_id: str,
    payload: DraftUpdateRequest,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Update a draft response body."""
    service = DraftResponseService(db)
    draft = service.update_draft_body(
        draft_id=draft_id,
        body=payload.body,
    )

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft response not found or cannot be edited.",
        )

    return DraftResponseOut.model_validate(draft)


@router.post("/{draft_id}/approve", response_model=DraftResponseOut)
def approve_draft(
    draft_id: str,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Approve a draft response."""
    service = DraftResponseService(db)
    draft = service.approve_draft(draft_id)

    if draft is None:
        raise HTTPException(status_code=404, detail="Draft response not found.")

    return DraftResponseOut.model_validate(draft)


@router.post("/{draft_id}/reject", response_model=DraftResponseOut)
def reject_draft(
    draft_id: str,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Reject a draft response."""
    service = DraftResponseService(db)
    draft = service.reject_draft(draft_id)

    if draft is None:
        raise HTTPException(status_code=404, detail="Draft response not found.")

    return DraftResponseOut.model_validate(draft)

@router.post("/{draft_id}/send", response_model=DraftResponseOut)
def send_draft(
    draft_id: str,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Simulate sending an approved draft response."""
    service = DraftResponseService(db)
    draft = service.send_draft(draft_id)

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft response not found or cannot be sent.",
        )

    return DraftResponseOut.model_validate(draft)