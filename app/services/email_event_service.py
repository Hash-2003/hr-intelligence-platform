from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import EmailEvent


class EmailEventService:
    """Service layer for email-like webhook event persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self,
        sender_email: str,
        sender_name: str | None,
        subject: str,
        body: str,
        received_at,
        source: str = "webhook",
    ) -> EmailEvent:
        """Create an incoming email event record."""
        event = EmailEvent(
            event_id=str(uuid4()),
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body=body,
            received_at=received_at,
            source=source,
            status="received",
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def mark_processed(
        self,
        event_id: str,
        linked_request_id: str,
    ) -> EmailEvent | None:
        """Mark an email event as processed and link it to an HR request."""
        event = (
            self.db.query(EmailEvent)
            .filter(EmailEvent.event_id == event_id)
            .first()
        )

        if event is None:
            return None

        event.linked_request_id = linked_request_id
        event.status = "processed"

        self.db.commit()
        self.db.refresh(event)

        return event

    def get_email_events(
            self,
            status: str | None = None,
            sender_email: str | None = None,
            source: str | None = None,
            linked_request_id: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> tuple[list[EmailEvent], int]:
        """Retrieve email events with filters and pagination metadata."""
        query = self.db.query(EmailEvent)

        if status:
            query = query.filter(EmailEvent.status == status)

        if sender_email:
            query = query.filter(EmailEvent.sender_email == sender_email)

        if source:
            query = query.filter(EmailEvent.source == source)

        if linked_request_id:
            query = query.filter(EmailEvent.linked_request_id == linked_request_id)

        total = query.count()

        events = (
            query.order_by(desc(EmailEvent.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return events, total

    def get_email_event_by_id(self, event_id: str) -> EmailEvent | None:
        """Retrieve one email event by event ID."""
        return (
            self.db.query(EmailEvent)
            .filter(EmailEvent.event_id == event_id)
            .first()
        )