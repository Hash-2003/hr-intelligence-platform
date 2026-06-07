from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import DraftResponse
from app.services.audit_service import AuditService
from app.services.review_decision_service import ReviewDecision


class DraftResponseService:
    """Service layer for human-reviewable draft responses."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def create_draft(
        self,
        request_id: str,
        body: str,
        review_decision: ReviewDecision,
        email_event_id: str | None = None,
        recipient_email: str | None = None,
        subject: str | None = None,
    ) -> DraftResponse:
        """Create a draft response for review."""
        draft = DraftResponse(
            draft_id=str(uuid4()),
            request_id=request_id,
            email_event_id=email_event_id,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status="draft",
            review_action=review_decision.action,
            review_required=review_decision.review_required,
            review_priority=review_decision.priority,
            review_reason=review_decision.reason,
            review_decision_source=review_decision.decision_source,
        )

        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)

        self._create_draft_audit_event(
            event_type="draft_created",
            draft=draft,
        )

        return draft

    def get_drafts(
            self,
            status: str | None = None,
            review_required: bool | None = None,
            review_priority: str | None = None,
            review_action: str | None = None,
            recipient_email: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> tuple[list[DraftResponse], int]:
        """Retrieve draft responses with filters and pagination metadata."""
        query = self.db.query(DraftResponse)

        if status:
            query = query.filter(DraftResponse.status == status)

        if review_required is not None:
            query = query.filter(DraftResponse.review_required == review_required)

        if review_priority:
            query = query.filter(DraftResponse.review_priority == review_priority)

        if review_action:
            query = query.filter(DraftResponse.review_action == review_action)

        if recipient_email:
            query = query.filter(DraftResponse.recipient_email == recipient_email)

        total = query.count()

        drafts = query.order_by(desc(DraftResponse.created_at)).offset(offset).limit(limit).all()

        return cast(list[DraftResponse], drafts), total

    def get_draft_by_id(self, draft_id: str) -> DraftResponse | None:
        """Retrieve one draft by draft ID."""
        return cast(
            DraftResponse | None,
            self.db.query(DraftResponse)
            .filter(DraftResponse.draft_id == draft_id)
            .first(),
        )

    def update_draft_body(self, draft_id: str, body: str) -> DraftResponse | None:
        """Update the body of a draft response if it is still editable."""
        draft = self.get_draft_by_id(draft_id)

        if draft is None:
            return None

        if draft.status != "draft":
            return None

        draft.body = body
        draft.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(draft)

        self._create_draft_audit_event(
            event_type="draft_updated",
            draft=draft,
        )

        return draft

    def approve_draft(self, draft_id: str) -> DraftResponse | None:
        """Mark a draft as approved."""
        draft = self.get_draft_by_id(draft_id)

        if draft is None:
            return None

        draft.status = "approved"
        draft.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(draft)

        self._create_draft_audit_event(
            event_type="draft_approved",
            draft=draft,
        )

        return draft

    def reject_draft(self, draft_id: str) -> DraftResponse | None:
        """Mark a draft as rejected."""
        draft = self.get_draft_by_id(draft_id)

        if draft is None:
            return None

        draft.status = "rejected"
        draft.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(draft)

        self._create_draft_audit_event(
            event_type="draft_rejected",
            draft=draft,
        )

        return draft

    def send_draft(self, draft_id: str) -> DraftResponse | None:
        """Simulate sending an approved draft response."""
        draft = self.get_draft_by_id(draft_id)

        if draft is None:
            return None

        if draft.status != "approved":
            return None

        draft.status = "sent"
        draft.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(draft)

        self._create_draft_audit_event(
            event_type="draft_sent",
            draft=draft,
        )

        return draft

    def _create_draft_audit_event(
        self,
        event_type: str,
        draft: DraftResponse,
    ) -> None:
        """Create a generic audit event for draft lifecycle changes."""
        self.audit_service.create_event(
            event_type=event_type,
            resource_type="draft_response",
            resource_id=draft.draft_id,
            request_id=draft.request_id,
            user_id=draft.recipient_email or "system",
            details={
                "draft_id": draft.draft_id,
                "request_id": draft.request_id,
                "email_event_id": draft.email_event_id,
                "recipient_email": draft.recipient_email,
                "subject": draft.subject,
                "draft_status": draft.status,
                "review_action": draft.review_action,
                "review_required": draft.review_required,
                "review_priority": draft.review_priority,
                "review_reason": draft.review_reason,
                "review_decision_source": draft.review_decision_source,
            },
        )