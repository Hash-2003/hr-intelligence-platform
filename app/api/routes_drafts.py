from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.draft_schema import DraftResponseOut, DraftUpdateRequest, DraftResponseListOut
from app.services.draft_response_service import DraftResponseService
from app.core.exceptions import InvalidStateTransitionError
from app.core.auth import CurrentUser, require_roles
from app.core.constants import UserRole

router = APIRouter(prefix="/drafts", tags=["Draft Responses"])

def _raise_invalid_transition_error(error: InvalidStateTransitionError) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "message": str(error),
            "resource_type": error.resource_type,
            "resource_id": error.resource_id,
            "current_status": error.current_status,
            "attempted_action": error.attempted_action,
        },
    )

@router.get("", response_model=DraftResponseListOut)
def get_drafts(
    status: str | None = None,
    review_required: bool | None = None,
    review_priority: str | None = None,
    review_action: str | None = None,
    recipient_email: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(UserRole.HR_REVIEWER, UserRole.ADMIN)
    ),
) -> DraftResponseListOut:
    """Retrieve draft responses with optional filters and pagination metadata."""
    service = DraftResponseService(db)
    drafts, total = service.get_drafts(
        status=status,
        review_required=review_required,
        review_priority=review_priority,
        review_action=review_action,
        recipient_email=recipient_email,
        limit=limit,
        offset=offset,
    )

    return DraftResponseListOut(
        items=[
            DraftResponseOut.model_validate(draft)
            for draft in drafts
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


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

    try:
        draft = service.update_draft_body(
            draft_id=draft_id,
            body=payload.body,
        )
    except InvalidStateTransitionError as error:
        _raise_invalid_transition_error(error)

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft response not found.",
        )

    return DraftResponseOut.model_validate(draft)


@router.post("/{draft_id}/approve", response_model=DraftResponseOut)
def approve_draft(
    draft_id: str,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Approve a draft response."""
    service = DraftResponseService(db)

    try:
        draft = service.approve_draft(draft_id)
    except InvalidStateTransitionError as error:
        _raise_invalid_transition_error(error)

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

    try:
        draft = service.reject_draft(draft_id)
    except InvalidStateTransitionError as error:
        _raise_invalid_transition_error(error)

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

    try:
        draft = service.send_draft(draft_id)
    except InvalidStateTransitionError as error:
        _raise_invalid_transition_error(error)

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft response not found.",
        )

    return DraftResponseOut.model_validate(draft)