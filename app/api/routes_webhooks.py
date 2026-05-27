from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.graph.workflow import HRWorkflow
from app.schemas.webhook_schema import EmailWebhookRequest, EmailWebhookResponse
from app.services.email_event_service import EmailEventService
from app.services.draft_response_service import DraftResponseService
from app.services.review_decision_service import ReviewDecisionService
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
        source_type="email_webhook",
        subject=payload.subject,
        reference_datetime=payload.received_at,
    )

    email_service.mark_processed(
        event_id=event.event_id,
        linked_request_id=result["request_id"],
    )

    review_service = ReviewDecisionService()
    review_decision = review_service.decide(
        message=workflow_message,
        intent=result.get("intent"),
        confidence=result.get("confidence"),
        selected_agent=result.get("selected_agent"),
        policy_sources_used=result.get("policy_sources_used", []),
        status=result.get("status", "success"),
    )

    draft_service = DraftResponseService(db)
    draft = draft_service.create_draft(
        request_id=result["request_id"],
        email_event_id=event.event_id,
        recipient_email=str(payload.sender_email),
        subject=f"Re: {payload.subject}",
        body=result.get("response", ""),
        review_decision=review_decision,
    )

    return EmailWebhookResponse(
        event_id=event.event_id,
        request_id=result["request_id"],
        draft_id=draft.draft_id,
        intent=result.get("intent", "clarification"),
        agent=result.get("selected_agent", "clarification_agent"),
        response=result.get("response", ""),
        status="processed",
        review_action=review_decision.action,
        review_required=review_decision.review_required,
        review_priority=review_decision.priority,
        review_reason=review_decision.reason,
        review_decision_source=review_decision.decision_source,
    )