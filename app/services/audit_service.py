from sqlalchemy import desc
from sqlalchemy.orm import Session

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
        """Create an append-only audit log entry."""
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
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def get_logs(
        self,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Retrieve audit logs, optionally filtered by user."""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()