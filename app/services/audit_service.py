import json

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.constants import AuditEventType, ResourceType
from app.database import AuditLog


class AuditService:
    """Service layer for append-only audit logging."""

    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        request_id: str,
        user_id: str,
        message: str,
        classified_intent: str | None,
        confidence: float | None,
        selected_agent: str | None,
        response_summary: str | None,
        status: str = "success",
        error_message: str | None = None,
    ) -> AuditLog:
        """Create an append-only request-level audit log entry."""
        log = AuditLog(
            request_id=request_id,
            user_id=user_id,
            message=message,
            classified_intent=classified_intent,
            confidence=confidence,
            selected_agent=selected_agent,
            response_summary=response_summary,
            status=status,
            error_message=error_message,
            event_type=AuditEventType.REQUEST_PROCESSED.value,
            resource_type=ResourceType.HR_REQUEST.value,
            resource_id=request_id,
            details_json=None,
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def create_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        user_id: str = "system",
        request_id: str | None = None,
        details: dict | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> AuditLog:
        """Create a generic append-only audit event."""
        log = AuditLog(
            request_id=request_id or resource_id,
            user_id=user_id,
            message=f"Audit event: {event_type}",
            classified_intent=None,
            confidence=None,
            selected_agent=None,
            response_summary=None,
            status=status,
            error_message=error_message,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details or {}, default=str),
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def get_logs(
            self,
            user_id: str | None = None,
            request_id: str | None = None,
            event_type: str | None = None,
            resource_type: str | None = None,
            resource_id: str | None = None,
            status: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit logs with filters and pagination metadata."""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if request_id:
            query = query.filter(AuditLog.request_id == request_id)

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)

        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)

        if status:
            query = query.filter(AuditLog.status == status)

        total = query.count()

        logs = (
            query.order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return logs, total