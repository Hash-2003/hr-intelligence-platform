from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.graph.workflow import HRWorkflow
from app.schemas.request_schema import UserRequest, UserRequestResponse

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", response_model=UserRequestResponse)
def handle_request(
    payload: UserRequest,
    db: Session = Depends(get_db),
) -> UserRequestResponse:
    """Handle a natural language HR request through the LangGraph workflow."""
    workflow = HRWorkflow(db)

    result = workflow.run(
        user_id=payload.user_id,
        message=payload.message,
    )

    return UserRequestResponse(
        request_id=result["request_id"],
        intent=result.get("intent", "clarification"),
        confidence=result.get("confidence", 0.0),
        agent=result.get("selected_agent", "clarification_agent"),
        response=result.get(
            "response",
            "I’m sorry, I could not complete the request right now.",
        ),
        memory_used=result.get("memory_used", False),
    )