from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailWebhookRequest(BaseModel):
    """Incoming email-like webhook payload."""

    sender_email: EmailStr
    sender_name: str | None = Field(default=None, max_length=255)
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=5000)
    received_at: datetime | None = None


class EmailWebhookResponse(BaseModel):
    """Response returned after processing an email-like webhook event."""

    event_id: str
    request_id: str
    draft_id: str
    intent: str
    agent: str
    response: str
    status: str
    review_action: str
    review_required: bool
    review_priority: str
    review_reason: str
    review_decision_source: str