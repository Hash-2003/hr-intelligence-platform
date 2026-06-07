from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.webhook_schema import EmailEventListOut, EmailEventOut
from app.services.email_event_service import EmailEventService

router = APIRouter(prefix="/email-events", tags=["Email Events"])


@router.get("", response_model=EmailEventListOut)
def get_email_events(
    status: str | None = None,
    sender_email: str | None = None,
    source: str | None = None,
    linked_request_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EmailEventListOut:
    """Retrieve stored email webhook events with filters and pagination metadata."""
    service = EmailEventService(db)
    events, total = service.get_email_events(
        status=status,
        sender_email=sender_email,
        source=source,
        linked_request_id=linked_request_id,
        limit=limit,
        offset=offset,
    )

    return EmailEventListOut(
        items=[
            EmailEventOut.model_validate(event)
            for event in events
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=EmailEventOut)
def get_email_event(
    event_id: str,
    db: Session = Depends(get_db),
) -> EmailEventOut:
    """Retrieve one stored email webhook event."""
    service = EmailEventService(db)
    event = service.get_email_event_by_id(event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Email event not found.")

    return EmailEventOut.model_validate(event)