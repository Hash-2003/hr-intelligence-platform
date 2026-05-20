from datetime import datetime

from pydantic import BaseModel


class HRRequestResponse(BaseModel):
    """HR request/case record returned through the API."""

    id: int
    request_id: str
    user_id: str
    source_type: str
    subject: str | None
    message: str
    intent: str | None
    confidence: float | None
    selected_agent: str | None
    response: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class AgentRunResponse(BaseModel):
    """Agent run record returned through the API."""

    id: int
    request_id: str
    agent_name: str
    input_summary: str | None
    output_summary: str | None
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {
        "from_attributes": True
    }