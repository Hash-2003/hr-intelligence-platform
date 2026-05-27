from datetime import datetime

from pydantic import BaseModel, Field


class DraftResponseOut(BaseModel):
    """Draft response returned through the API."""

    id: int
    draft_id: str
    request_id: str
    email_event_id: str | None
    recipient_email: str | None
    subject: str | None
    body: str
    status: str

    review_action: str
    review_required: bool
    review_priority: str
    review_reason: str
    review_decision_source: str

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class DraftUpdateRequest(BaseModel):
    """Request body for updating a draft response."""

    body: str = Field(..., min_length=1, max_length=10000)