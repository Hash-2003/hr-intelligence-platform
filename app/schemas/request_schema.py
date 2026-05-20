from pydantic import BaseModel, Field


class UserRequest(BaseModel):
    """Incoming natural language HR request."""

    user_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)


class UserRequestResponse(BaseModel):
    """Response returned after orchestration pipeline execution."""

    request_id: str
    intent: str
    confidence: float
    agent: str
    response: str
    memory_used: bool