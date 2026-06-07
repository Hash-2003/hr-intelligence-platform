from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.audit_schema import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    user_id: str | None = None,
    request_id: str | None = None,
    event_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Retrieve audit logs with optional filters."""
    service = AuditService(db)
    logs = service.get_logs(
        user_id=user_id,
        request_id=request_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        limit=limit,
    )

    return [
        AuditLogResponse.model_validate(log)
        for log in logs
    ]