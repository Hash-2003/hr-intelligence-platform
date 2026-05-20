from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Audit log record returned through the API."""

    id: int
    request_id: str
    user_id: str
    message: str
    classified_intent: str | None
    confidence: float | None
    selected_agent: str | None
    response_summary: str | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }