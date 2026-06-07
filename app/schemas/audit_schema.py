from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Audit log returned through the API."""

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

    event_type: str | None
    resource_type: str | None
    resource_id: str | None
    details_json: str | None

    created_at: datetime

    model_config = {
        "from_attributes": True
    }