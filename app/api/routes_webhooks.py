from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.graph.workflow import HRWorkflow
from app.schemas.webhook_schema import EmailWebhookRequest, EmailWebhookResponse
from app.services.email_event_service import EmailEventService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/email", response_model=EmailWebhookResponse)
def process_email_webhook(
    payload: EmailWebhookRequest,
    db: Session = Depends(get_db),
) -> EmailWebhookResponse:
    """Process an incoming email-like HR request webhook."""
    email_service = EmailEventService(db)

    event = email_service.create_event(
        sender_email=str(payload.sender_email),
        sender_name=payload.sender_name,
        subject=payload.subject,
        body=payload.body,
        received_at=payload.received_at,
    )

    workflow_message = (
        f"Email subject: {payload.subject}\n\n"
        f"Email body: {payload.body}"
    )

    workflow = HRWorkflow(db)
    result = workflow.run(
        user_id=str(payload.sender_email),
        message=workflow_message,
    )

    email_service.mark_processed(
        event_id=event.event_id,
        linked_request_id=result["request_id"],
    )

    return EmailWebhookResponse(
        event_id=event.event_id,
        request_id=result["request_id"],
        intent=result.get("intent", "clarification"),
        agent=result.get("selected_agent", "clarification_agent"),
        response=result.get("response", ""),
        status="processed",
    )