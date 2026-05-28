from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.webhook_schema import EmailEventOut
from app.services.email_event_service import EmailEventService

router = APIRouter(prefix="/email-events", tags=["Email Events"])


@router.get("", response_model=list[EmailEventOut])
def get_email_events(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[EmailEventOut]:
    """Retrieve stored email webhook events."""
    service = EmailEventService(db)
    events = service.get_email_events(status=status, limit=limit)

    return [
        EmailEventOut.model_validate(event)
        for event in events
    ]


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