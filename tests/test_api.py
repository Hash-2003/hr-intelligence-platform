import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

from pathlib import Path
from datetime import date

from app.services.leave_date_service import LeaveDateService
from app.services.review_decision_service import ReviewDecisionService, ReviewDecision


client = TestClient(app)

REVIEWER_HEADERS = {
    "X-User-Id": "hr_reviewer_test",
    "X-User-Role": "hr_reviewer",
}

ADMIN_HEADERS = {
    "X-User-Id": "admin_test",
    "X-User-Role": "admin",
}

EMPLOYEE_HEADERS = {
    "X-User-Id": "employee_test",
    "X-User-Role": "employee",
}


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "service" in data
    assert "llm_configured" in data


def test_root_endpoint_returns_api_info():
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "HR Intelligence Platform API"
    assert data["docs"] == "/docs"


def test_create_long_term_memory():
    payload = {
        "user_id": "test_user_001",
        "content": "User prefers morning interviews.",
        "memory_type": "ltm",
        "significance": 0.9,
    }

    response = client.post("/memory", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == payload["user_id"]
    assert data["content"] == payload["content"]
    assert data["memory_type"] == "ltm"
    assert data["significance"] == 0.9


def test_create_short_term_memory():
    payload = {
        "user_id": "test_user_001",
        "content": "User asked about annual leave.",
        "memory_type": "stm",
    }

    response = client.post("/memory", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == payload["user_id"]
    assert data["content"] == payload["content"]
    assert data["memory_type"] == "stm"
    assert data["significance"] is None


def test_get_user_memory():
    response = client.get("/memory/test_user_001")

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "test_user_001"
    assert "short_term_memory" in data
    assert "long_term_memory" in data


def test_get_audit_logs():
    response = client.get("/audit", headers=REVIEWER_HEADERS)

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)



def test_protected_drafts_endpoint_requires_auth_headers():
    response = client.get("/drafts")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing X-User-Id header."


def test_employee_cannot_access_draft_queue():
    response = client.get(
        "/drafts",
        headers=EMPLOYEE_HEADERS,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions."


def test_reviewer_can_access_draft_queue():
    response = client.get(
        "/drafts",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200


def test_admin_can_access_audit_logs():
    response = client.get(
        "/audit",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200


def test_invalid_role_is_rejected():
    response = client.get(
        "/drafts",
        headers={
            "X-User-Id": "bad_role_user",
            "X-User-Role": "manager",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid user role."


def test_requests_endpoint_with_mocked_workflow(monkeypatch):
    class MockWorkflow:
        def __init__(self, db):
            self.db = db

        def run(self, user_id: str, message: str):
            return {
                "request_id": "mock-request-id",
                "intent": "leave",
                "confidence": 0.95,
                "selected_agent": "leave_agent",
                "response": "Mock leave response.",
                "memory_used": True,
            }

    monkeypatch.setattr(
        "app.api.routes_requests.HRWorkflow",
        MockWorkflow,
    )

    payload = {
        "user_id": "test_user_001",
        "message": "I want annual leave tomorrow.",
    }

    response = client.post("/requests", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["request_id"] == "mock-request-id"
    assert data["intent"] == "leave"
    assert data["confidence"] == 0.95
    assert data["agent"] == "leave_agent"
    assert data["response"] == "Mock leave response."
    assert data["memory_used"] is True

def test_get_hr_requests():
    response = client.get("/hr-requests")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)


def test_get_hr_request_by_id_with_mocked_workflow(monkeypatch):
    class MockWorkflow:
        def __init__(self, db):
            self.db = db

        def run(self, user_id: str, message: str):
            from app.services.hr_request_service import HRRequestService
            from uuid import uuid4

            request_id = str(uuid4())
            service = HRRequestService(self.db)

            service.create_request(
                request_id=request_id,
                user_id=user_id,
                message=message,
                source_type="api",
            )

            service.update_request_result(
                request_id=request_id,
                intent="leave",
                confidence=0.95,
                selected_agent="leave_agent",
                response="Mock leave response.",
                status="success",
                error_message=None,
            )

            service.create_agent_run(
                request_id=request_id,
                agent_name="leave_agent",
                input_summary=message,
                output_summary="Mock leave response.",
                status="success",
                error_message=None,
            )

            return {
                "request_id": request_id,
                "intent": "leave",
                "confidence": 0.95,
                "selected_agent": "leave_agent",
                "response": "Mock leave response.",
                "memory_used": True,
            }

    monkeypatch.setattr(
        "app.api.routes_requests.HRWorkflow",
        MockWorkflow,
    )

    payload = {
        "user_id": "test_user_002",
        "message": "I want annual leave tomorrow.",
    }

    request_response = client.post("/requests", json=payload)

    assert request_response.status_code == 200
    request_id = request_response.json()["request_id"]

    response = client.get(f"/hr-requests/{request_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["request_id"] == request_id
    assert data["user_id"] == "test_user_002"
    assert data["intent"] == "leave"
    assert data["selected_agent"] == "leave_agent"
    assert data["status"] == "success"


def test_get_agent_runs_for_hr_request(monkeypatch):
    class MockWorkflow:
        def __init__(self, db):
            self.db = db

        def run(self, user_id: str, message: str):
            from app.services.hr_request_service import HRRequestService
            from uuid import uuid4

            request_id = str(uuid4())
            service = HRRequestService(self.db)

            service.create_request(
                request_id=request_id,
                user_id=user_id,
                message=message,
                source_type="api",
            )

            service.update_request_result(
                request_id=request_id,
                intent="compliance",
                confidence=0.9,
                selected_agent="compliance_agent",
                response="Mock compliance response.",
                status="success",
                error_message=None,
            )

            service.create_agent_run(
                request_id=request_id,
                agent_name="compliance_agent",
                input_summary=message,
                output_summary="Mock compliance response.",
                status="success",
                error_message=None,
            )

            return {
                "request_id": request_id,
                "intent": "compliance",
                "confidence": 0.9,
                "selected_agent": "compliance_agent",
                "response": "Mock compliance response.",
                "memory_used": True,
            }

    monkeypatch.setattr(
        "app.api.routes_requests.HRWorkflow",
        MockWorkflow,
    )

    payload = {
        "user_id": "test_user_003",
        "message": "Can my manager ask me to work overtime?",
    }

    request_response = client.post("/requests", json=payload)

    assert request_response.status_code == 200
    request_id = request_response.json()["request_id"]

    response = client.get(f"/hr-requests/{request_id}/agent-runs")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["request_id"] == request_id
    assert data[0]["agent_name"] == "compliance_agent"
    assert data[0]["status"] == "success"

def test_document_service_chunk_text():
    from app.services.document_service import DocumentService

    text = "A" * 2500
    chunks = DocumentService.chunk_text(text, max_chars=1000, overlap=100)

    assert len(chunks) == 3
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_document_service_hash_text_is_stable():
    from app.services.document_service import DocumentService

    text = "Employees receive 14 days of annual leave."
    hash_one = DocumentService.hash_text(text)
    hash_two = DocumentService.hash_text(text)

    assert hash_one == hash_two
    assert len(hash_one) == 64


def test_get_documents_endpoint():
    response = client.get("/documents")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_ingest_local_document_and_retrieve_chunks():
    from app.database import SessionLocal, create_db_tables
    from app.services.document_service import DocumentService

    create_db_tables()

    db = SessionLocal()

    try:
        service = DocumentService(db)
        file_path = Path("data/hr_documents/leave_policy.md")

        document, chunks_created, changed = service.ingest_local_document(file_path)

        assert document.id is not None
        assert document.filename == "leave_policy.md"
        assert document.content_hash is not None
        assert chunks_created >= 0

        chunks = service.get_document_chunks(document.id)

        assert len(chunks) >= 1
        assert "Annual Leave" in chunks[0].content or "annual leave" in chunks[0].content

        response = client.get(f"/documents/{document.id}/chunks")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["document_id"] == document.id

    finally:
        db.close()


def test_get_missing_document_returns_404():
    response = client.get("/documents/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."

def test_intent_classifier_corrects_annual_leave_to_leave():
    from app.services.intent_classifier import IntentClassificationResult, IntentClassifier

    original = IntentClassificationResult(
        intent="compliance",
        confidence=0.8,
        reasoning_summary="Original LLM result.",
    )

    corrected = IntentClassifier._correct_obvious_intent(
        message="How many annual leave days do I get?",
        result=original,
    )

    assert corrected.intent == "leave"
    assert corrected.confidence >= 0.9

def test_get_policy_sources_for_hr_request(monkeypatch):
    class MockWorkflow:
        def __init__(self, db):
            self.db = db

        def run(self, user_id: str, message: str):
            from uuid import uuid4

            from app.database import Document, DocumentChunk
            from app.services.hr_request_service import HRRequestService

            request_id = str(uuid4())
            service = HRRequestService(self.db)

            service.create_request(
                request_id=request_id,
                user_id=user_id,
                message=message,
                source_type="api",
            )

            document = Document(
                title="Overtime Policy",
                document_type="policy",
                filename=f"test_overtime_policy_{request_id}.md",
                source_path="data/hr_documents/overtime_policy.md",
                source="local_seed",
                content_hash=f"test_hash_{request_id}",
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                content="Overtime must be approved before it is worked.",
                token_estimate=12,
            )
            self.db.add(chunk)
            self.db.commit()
            self.db.refresh(chunk)

            service.update_request_result(
                request_id=request_id,
                intent="compliance",
                confidence=0.9,
                selected_agent="compliance_agent",
                response="Mock compliance response.",
                status="success",
                error_message=None,
            )

            service.create_agent_run(
                request_id=request_id,
                agent_name="compliance_agent",
                input_summary=message,
                output_summary="Mock compliance response.",
                status="success",
                error_message=None,
            )

            service.create_policy_sources(
                request_id=request_id,
                policy_sources=[
                    {
                        "document_id": document.id,
                        "document_title": document.title,
                        "filename": document.filename,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "score": 5,
                    }
                ],
            )

            return {
                "request_id": request_id,
                "intent": "compliance",
                "confidence": 0.9,
                "selected_agent": "compliance_agent",
                "response": "Mock compliance response.",
                "memory_used": True,
            }

    monkeypatch.setattr(
        "app.api.routes_requests.HRWorkflow",
        MockWorkflow,
    )

    payload = {
        "user_id": "test_user_policy_sources",
        "message": "Can I work overtime first and get approval later?",
    }

    request_response = client.post("/requests", json=payload)

    assert request_response.status_code == 200
    request_id = request_response.json()["request_id"]

    response = client.get(f"/hr-requests/{request_id}/policy-sources")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["request_id"] == request_id
    assert data[0]["document_title"] == "Overtime Policy"
    assert data[0]["filename"].startswith("test_overtime_policy_")
    assert data[0]["chunk_index"] == 0
    assert data[0]["score"] == 5

def test_email_webhook_processes_email_like_request(monkeypatch):
    class MockWorkflow:
        def __init__(self, db):
            self.db = db

        def run(
                self,
                user_id: str,
                message: str,
                source_type: str = "api",
                subject: str | None = None,
                reference_datetime=None,
        ):
            assert user_id == "employee@example.com"
            assert source_type == "email_webhook"
            assert subject == "Annual leave request"
            assert reference_datetime is not None
            assert reference_datetime.year == 2026
            assert reference_datetime.month == 5
            assert reference_datetime.day == 20
            assert "Email subject: Annual leave request" in message
            assert "Email body:" in message

            from uuid import uuid4

            from app.services.hr_request_service import HRRequestService

            request_id = str(uuid4())
            service = HRRequestService(self.db)

            service.create_request(
                request_id=request_id,
                user_id=user_id,
                message=message,
                source_type=source_type,
                subject=subject,
            )

            service.update_request_result(
                request_id=request_id,
                intent="leave",
                confidence=0.95,
                selected_agent="leave_agent",
                response="Mock leave response generated from email.",
                status="success",
                error_message=None,
            )

            service.create_agent_run(
                request_id=request_id,
                agent_name="leave_agent",
                input_summary=message,
                output_summary="Mock leave response generated from email.",
                status="success",
                error_message=None,
            )

            return {
                "request_id": request_id,
                "intent": "leave",
                "confidence": 0.95,
                "selected_agent": "leave_agent",
                "response": "Mock leave response generated from email.",
                "memory_used": True,
            }

    monkeypatch.setattr(
        "app.api.routes_webhooks.HRWorkflow",
        MockWorkflow,
    )

    payload = {
        "sender_email": "employee@example.com",
        "sender_name": "Kasun Perera",
        "subject": "Annual leave request",
        "body": "I would like to apply for annual leave next Monday and Tuesday.",
        "received_at": "2026-05-20T10:30:00",
    }

    response = client.post("/webhooks/email", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "event_id" in data
    assert "request_id" in data
    assert data["intent"] == "leave"
    assert data["agent"] == "leave_agent"
    assert data["response"] == "Mock leave response generated from email."
    assert data["status"] == "processed"

def test_email_webhook_rejects_invalid_email():
    payload = {
        "sender_email": "not-an-email",
        "sender_name": "Invalid User",
        "subject": "Annual leave request",
        "body": "I would like to apply for annual leave.",
        "received_at": "2026-05-20T10:30:00",
    }

    response = client.post("/webhooks/email", json=payload)

    assert response.status_code == 422

def test_email_webhook_rejects_missing_body():
    payload = {
        "sender_email": "employee@example.com",
        "sender_name": "Kasun Perera",
        "subject": "Annual leave request",
        "received_at": "2026-05-20T10:30:00",
    }

    response = client.post("/webhooks/email", json=payload)

    assert response.status_code == 422

def test_resolves_tomorrow():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave tomorrow.",
        reference_date=date(2026, 5, 17),
    )

    assert facts.found_leave_dates is True
    assert facts.start_date == date(2026, 5, 18)
    assert facts.end_date == date(2026, 5, 18)
    assert facts.submission_deadline == date(2026, 5, 11)
    assert facts.notice_status == "missed"


def test_resolves_today():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave today.",
        reference_date=date(2026, 5, 17),
    )

    assert facts.found_leave_dates is True
    assert facts.start_date == date(2026, 5, 17)
    assert facts.end_date == date(2026, 5, 17)
    assert facts.submission_deadline == date(2026, 5, 10)
    assert facts.notice_status == "missed"


def test_next_monday_when_reference_date_is_monday_returns_following_monday():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave next Monday.",
        reference_date=date(2026, 5, 18),
    )

    assert facts.found_leave_dates is True
    assert facts.start_date == date(2026, 5, 25)
    assert facts.submission_deadline == date(2026, 5, 18)
    assert facts.notice_status == "deadline_today"


def test_invalid_zero_day_duration_defaults_to_one_day():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave for 0 days starting from next Monday.",
        reference_date=date(2026, 5, 17),
    )

    assert facts.found_leave_dates is True
    assert facts.start_date == date(2026, 5, 18)
    assert facts.duration_days == 1
    assert facts.end_date == date(2026, 5, 18)


def test_unsupported_duration_keeps_duration_as_one_day():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave for two days starting from next Monday.",
        reference_date=date(2026, 5, 17),
    )

    assert facts.found_leave_dates is True
    assert facts.start_date == date(2026, 5, 18)
    assert facts.duration_days == 1
    assert facts.end_date == date(2026, 5, 18)


def test_build_context_contains_notice_status_and_deadline():
    service = LeaveDateService()

    facts = service.resolve(
        message="I want annual leave for 2 days starting from a week after next Monday.",
        reference_date=date(2026, 5, 17),
    )

    context = service.build_context(facts)

    assert "Resolved leave date facts:" in context
    assert "requested start date: 2026-05-25 Monday" in context
    assert "requested end date: 2026-05-26 Tuesday" in context
    assert "latest standard submission date: 2026-05-18 Monday" in context
    assert "notice status: not_missed" in context

def test_intent_classifier_corrects_sick_leave_to_leave():
    from app.services.intent_classifier import IntentClassificationResult, IntentClassifier

    original = IntentClassificationResult(
        intent="compliance",
        confidence=0.7,
        reasoning_summary="Original LLM result.",
    )

    corrected = IntentClassifier._correct_obvious_intent(
        message="I need to apply for sick leave tomorrow.",
        result=original,
    )

    assert corrected.intent == "leave"
    assert corrected.confidence >= 0.9


def test_intent_classifier_corrects_interview_to_scheduling():
    from app.services.intent_classifier import IntentClassificationResult, IntentClassifier

    original = IntentClassificationResult(
        intent="clarification",
        confidence=0.7,
        reasoning_summary="Original LLM result.",
    )

    corrected = IntentClassifier._correct_obvious_intent(
        message="Please schedule an interview with Kasun tomorrow.",
        result=original,
    )

    assert corrected.intent == "scheduling"
    assert corrected.confidence >= 0.9


def test_intent_classifier_corrects_overtime_to_compliance():
    from app.services.intent_classifier import IntentClassificationResult, IntentClassifier

    original = IntentClassificationResult(
        intent="clarification",
        confidence=0.7,
        reasoning_summary="Original LLM result.",
    )

    corrected = IntentClassifier._correct_obvious_intent(
        message="Can I work overtime without approval?",
        result=original,
    )

    assert corrected.intent == "compliance"
    assert corrected.confidence >= 0.9


def test_intent_classifier_corrects_harassment_to_compliance():
    from app.services.intent_classifier import IntentClassificationResult, IntentClassifier

    original = IntentClassificationResult(
        intent="clarification",
        confidence=0.7,
        reasoning_summary="Original LLM result.",
    )

    corrected = IntentClassifier._correct_obvious_intent(
        message="I was harassed by my manager.",
        result=original,
    )

    assert corrected.intent == "compliance"
    assert corrected.confidence >= 0.9

def test_simple_leave_request_is_review_optional():
    service = ReviewDecisionService()

    decision = service.decide(
        message="I want to apply for annual leave next Monday.",
        intent="leave",
        confidence=0.95,
        selected_agent="leave_agent",
        policy_sources_used=[{"filename": "leave_policy.md"}],
        status="success",
    )

    assert decision.action == "review_optional"
    assert decision.review_required is False
    assert decision.priority == "medium"
    assert decision.decision_source == "deterministic"


def test_simple_policy_question_can_be_auto_response():
    service = ReviewDecisionService()

    decision = service.decide(
        message="What is the overtime approval policy?",
        intent="compliance",
        confidence=0.95,
        selected_agent="compliance_agent",
        policy_sources_used=[{"filename": "overtime_policy.md"}],
        status="success",
    )

    assert decision.action == "auto_response"
    assert decision.review_required is False
    assert decision.priority == "low"


def test_harassment_message_requires_human_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="I was harassed by my manager.",
        intent="compliance",
        confidence=0.95,
        selected_agent="compliance_agent",
        policy_sources_used=[{"filename": "code_of_conduct.md"}],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"


def test_legal_message_requires_human_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="I will contact a lawyer about this.",
        intent="compliance",
        confidence=0.95,
        selected_agent="compliance_agent",
        policy_sources_used=[{"filename": "policy.md"}],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"


def test_security_message_requires_human_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="My work laptop was hacked and files may have leaked.",
        intent="compliance",
        confidence=0.95,
        selected_agent="compliance_agent",
        policy_sources_used=[{"filename": "policy.md"}],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"


def test_salary_issue_requires_human_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="My salary payment is wrong.",
        intent="compliance",
        confidence=0.9,
        selected_agent="compliance_agent",
        policy_sources_used=[{"filename": "policy.md"}],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"


def test_safety_sensitive_message_escalates():
    service = ReviewDecisionService()

    decision = service.decide(
        message="I feel unsafe and this is an emergency.",
        intent="clarification",
        confidence=0.8,
        selected_agent="clarification_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "escalated"
    assert decision.review_required is True
    assert decision.priority == "critical"


def test_low_confidence_requires_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="Can you help me with that thing?",
        intent="clarification",
        confidence=0.5,
        selected_agent="clarification_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "medium"


def test_missing_policy_source_requires_review_for_leave():
    service = ReviewDecisionService()

    decision = service.decide(
        message="How many annual leave days do I get?",
        intent="leave",
        confidence=0.95,
        selected_agent="leave_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "medium"


def test_failed_workflow_requires_review():
    service = ReviewDecisionService()

    decision = service.decide(
        message="I want annual leave.",
        intent="leave",
        confidence=0.9,
        selected_agent="leave_agent",
        policy_sources_used=[{"filename": "leave_policy.md"}],
        status="failed",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"


def test_soft_risk_without_llm_falls_back_to_review_required():
    service = ReviewDecisionService()

    decision = service.decide(
        message="My manager is making me uncomfortable.",
        intent="clarification",
        confidence=0.8,
        selected_agent="clarification_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "medium"
    assert decision.decision_source == "deterministic_fallback"


def test_soft_risk_uses_llm_when_available():
    class MockLLMService:
        def chat_completion(self, system_prompt, user_prompt, temperature=0.0):
            return (
                '{"action": "review_required", '
                '"priority": "high", '
                '"reason": "Possible workplace conduct concern."}'
            )

    service = ReviewDecisionService(llm_service=MockLLMService())

    decision = service.decide(
        message="My manager is making me uncomfortable.",
        intent="clarification",
        confidence=0.8,
        selected_agent="clarification_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "high"
    assert decision.decision_source == "llm_assisted"


def test_llm_invalid_json_falls_back_to_review_required():
    class MockLLMService:
        def chat_completion(self, system_prompt, user_prompt, temperature=0.0):
            return "not valid json"

    service = ReviewDecisionService(llm_service=MockLLMService())

    decision = service.decide(
        message="My manager is making me uncomfortable.",
        intent="clarification",
        confidence=0.8,
        selected_agent="clarification_agent",
        policy_sources_used=[],
        status="success",
    )

    assert decision.action == "review_required"
    assert decision.review_required is True
    assert decision.priority == "medium"
    assert decision.decision_source == "deterministic_fallback"


def test_create_generic_audit_event():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        log = service.create_event(
            event_type="draft_created",
            resource_type="draft_response",
            resource_id="draft-123",
            request_id="request-123",
            user_id="employee@example.com",
            details={
                "draft_id": "draft-123",
                "draft_status": "draft",
                "review_action": "review_optional",
            },
        )

        assert log.id is not None
        assert log.event_type == "draft_created"
        assert log.resource_type == "draft_response"
        assert log.resource_id == "draft-123"
        assert log.request_id == "request-123"
        assert log.user_id == "employee@example.com"
        assert log.message == "Audit event: draft_created"
        assert log.status == "success"

        details = json.loads(log.details_json)

        assert details["draft_id"] == "draft-123"
        assert details["draft_status"] == "draft"
        assert details["review_action"] == "review_optional"

    finally:
        db.close()


def test_create_request_level_audit_log_sets_default_event_metadata():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        log = service.create_log(
            request_id="request-456",
            user_id="user-456",
            message="Test request message",
            classified_intent="leave",
            confidence=0.95,
            selected_agent="leave_agent",
            response_summary="Test response summary",
            status="success",
        )

        assert log.id is not None
        assert log.event_type == "request_processed"
        assert log.resource_type == "hr_request"
        assert log.resource_id == "request-456"
        assert log.request_id == "request-456"
        assert log.classified_intent == "leave"
        assert log.selected_agent == "leave_agent"

    finally:
        db.close()


def _create_test_hr_request_for_draft_audit(db) -> str:
    from app.services.hr_request_service import HRRequestService

    request_id = str(uuid4())
    service = HRRequestService(db)

    service.create_request(
        request_id=request_id,
        user_id="employee@example.com",
        message="I want annual leave next Monday.",
        source_type="api",
        subject="Annual leave request",
    )

    return request_id


def _test_review_decision_for_draft_audit() -> ReviewDecision:
    return ReviewDecision(
        action="review_optional",
        review_required=False,
        priority="medium",
        reason="Leave request detected; draft may be reviewed before action.",
        decision_source="deterministic",
    )


def test_create_draft_writes_draft_created_audit_event():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Generated draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            email_event_id=None,
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        audit_logs, _ = service.audit_service.get_logs(
            user_id="employee@example.com",
            limit=20,
        )

        draft_created_logs = [
            log for log in audit_logs
            if log.event_type == "draft_created"
            and log.resource_id == draft.draft_id
        ]

        assert len(draft_created_logs) == 1

        log = draft_created_logs[0]

        assert log.resource_type == "draft_response"
        assert log.resource_id == draft.draft_id
        assert log.request_id == request_id

        details = json.loads(log.details_json)

        assert details["draft_id"] == draft.draft_id
        assert details["request_id"] == request_id
        assert details["draft_status"] == "draft"
        assert details["review_action"] == "review_optional"
        assert details["review_required"] is False
        assert details["review_priority"] == "medium"
        assert details["review_decision_source"] == "deterministic"

    finally:
        db.close()


def test_update_draft_writes_draft_updated_audit_event():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Original draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        updated = service.update_draft_body(
            draft_id=draft.draft_id,
            body="Updated draft body.",
        )

        assert updated is not None
        assert updated.body == "Updated draft body."

        audit_logs, _ = service.audit_service.get_logs(
            user_id="employee@example.com",
            limit=20,
        )

        assert any(
            log.event_type == "draft_updated"
            and log.resource_id == draft.draft_id
            for log in audit_logs
        )

    finally:
        db.close()


def test_approve_draft_writes_draft_approved_audit_event():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        approved = service.approve_draft(draft.draft_id)

        assert approved is not None
        assert approved.status == "approved"

        audit_logs, _ = service.audit_service.get_logs(
            user_id="employee@example.com",
            limit=20,
        )

        approved_logs = [
            log for log in audit_logs
            if log.event_type == "draft_approved"
            and log.resource_id == draft.draft_id
        ]

        assert len(approved_logs) == 1

        details = json.loads(approved_logs[0].details_json)

        assert details["draft_status"] == "approved"

    finally:
        db.close()


def test_reject_draft_writes_draft_rejected_audit_event():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        rejected = service.reject_draft(draft.draft_id)

        assert rejected is not None
        assert rejected.status == "rejected"

        audit_logs, _ = service.audit_service.get_logs(
            user_id="employee@example.com",
            limit=20,
        )

        rejected_logs = [
            log for log in audit_logs
            if log.event_type == "draft_rejected"
            and log.resource_id == draft.draft_id
        ]

        assert len(rejected_logs) == 1

        details = json.loads(rejected_logs[0].details_json)

        assert details["draft_status"] == "rejected"

    finally:
        db.close()


def test_approved_draft_cannot_be_updated():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        service.approve_draft(draft.draft_id)

        from app.core.exceptions import InvalidStateTransitionError

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.update_draft_body(
                draft_id=draft.draft_id,
                body="Should not update.",
            )

        error = exc_info.value

        assert error.resource_type == "draft_response"
        assert error.resource_id == draft.draft_id
        assert error.current_status == "approved"
        assert error.attempted_action == "update"

    finally:
        db.close()

def test_send_approved_draft_marks_as_sent_and_writes_audit_event():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        approved = service.approve_draft(draft.draft_id)

        assert approved is not None
        assert approved.status == "approved"

        sent = service.send_draft(draft.draft_id)

        assert sent is not None
        assert sent.status == "sent"

        audit_logs, _ = service.audit_service.get_logs(
            user_id="employee@example.com",
            limit=30,
        )

        sent_logs = [
            log for log in audit_logs
            if log.event_type == "draft_sent"
            and log.resource_id == draft.draft_id
        ]

        assert len(sent_logs) == 1

        details = json.loads(sent_logs[0].details_json)

        assert details["draft_status"] == "sent"
        assert details["draft_id"] == draft.draft_id

    finally:
        db.close()

def test_unapproved_draft_cannot_be_sent():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        from app.core.exceptions import InvalidStateTransitionError

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.send_draft(draft.draft_id)

        error = exc_info.value

        assert error.resource_type == "draft_response"
        assert error.resource_id == draft.draft_id
        assert error.current_status == "draft"
        assert error.attempted_action == "send"

    finally:
        db.close()

def test_send_draft_endpoint_sends_approved_draft():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        approve_response = client.post(
            f"/drafts/{draft.draft_id}/approve",
            headers=REVIEWER_HEADERS,
        )

        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        send_response = client.post(
            f"/drafts/{draft.draft_id}/send",
            headers=REVIEWER_HEADERS,
        )

        assert send_response.status_code == 200
        data = send_response.json()

        assert data["draft_id"] == draft.draft_id
        assert data["status"] == "sent"

    finally:
        db.close()

def test_send_draft_endpoint_rejects_unapproved_draft():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        response = client.post(
            f"/drafts/{draft.draft_id}/send",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 409

        detail = response.json()["detail"]

        assert detail["resource_type"] == "draft_response"
        assert detail["resource_id"] == draft.draft_id
        assert detail["current_status"] == "draft"
        assert detail["attempted_action"] == "send"
        assert "Cannot perform 'send'" in detail["message"]

    finally:
        db.close()

def test_approved_draft_cannot_be_rejected():
    from app.core.exceptions import InvalidStateTransitionError
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        service.approve_draft(draft.draft_id)

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.reject_draft(draft.draft_id)

        error = exc_info.value

        assert error.current_status == "approved"
        assert error.attempted_action == "reject"

    finally:
        db.close()

def test_rejected_draft_cannot_be_approved():
    from app.core.exceptions import InvalidStateTransitionError
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        service.reject_draft(draft.draft_id)

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.approve_draft(draft.draft_id)

        error = exc_info.value

        assert error.current_status == "rejected"
        assert error.attempted_action == "approve"

    finally:
        db.close()

def test_sent_draft_cannot_be_updated():
    from app.core.exceptions import InvalidStateTransitionError
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        service.approve_draft(draft.draft_id)
        service.send_draft(draft.draft_id)

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.update_draft_body(
                draft_id=draft.draft_id,
                body="Should not update sent draft.",
            )

        error = exc_info.value

        assert error.current_status == "sent"
        assert error.attempted_action == "update"

    finally:
        db.close()

def test_get_drafts_filters_by_status():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="employee@example.com",
            subject="Re: Annual leave request",
        )

        service.approve_draft(draft.draft_id)

        response = client.get(
            "/drafts?status=approved",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert any(
            item["draft_id"] == draft.draft_id
            and item["status"] == "approved"
            for item in items
        )

    finally:
        db.close()

def test_get_drafts_filters_by_review_priority():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService
    from app.services.review_decision_service import ReviewDecision

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        high_priority_decision = ReviewDecision(
            action="review_required",
            review_required=True,
            priority="high",
            reason="Sensitive HR topic detected.",
            decision_source="deterministic",
        )

        draft = service.create_draft(
            request_id=request_id,
            body="High priority draft body.",
            review_decision=high_priority_decision,
            recipient_email="employee@example.com",
            subject="Re: Sensitive HR request",
        )

        response = client.get(
            "/drafts?review_priority=high",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert any(
            item["draft_id"] == draft.draft_id
            and item["review_priority"] == "high"
            for item in items
        )

    finally:
        db.close()

def test_get_drafts_filters_by_review_action():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService
    from app.services.review_decision_service import ReviewDecision

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        review_required_decision = ReviewDecision(
            action="review_required",
            review_required=True,
            priority="high",
            reason="Sensitive workplace concern detected.",
            decision_source="deterministic",
        )

        draft = service.create_draft(
            request_id=request_id,
            body="Review required draft body.",
            review_decision=review_required_decision,
            recipient_email="employee@example.com",
            subject="Re: HR concern",
        )

        response = client.get(
            "/drafts?review_action=review_required",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert any(
            item["draft_id"] == draft.draft_id
            and item["review_action"] == "review_required"
            for item in items
        )

    finally:
        db.close()

def test_get_drafts_filters_by_recipient_email():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        draft = service.create_draft(
            request_id=request_id,
            body="Draft body for recipient filter.",
            review_decision=_test_review_decision_for_draft_audit(),
            recipient_email="specific.employee@example.com",
            subject="Re: Annual leave request",
        )

        response = client.get(
            "/drafts?recipient_email=specific.employee@example.com",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert any(
            item["draft_id"] == draft.draft_id
            and item["recipient_email"] == "specific.employee@example.com"
            for item in items
        )

    finally:
        db.close()

def test_get_drafts_supports_combined_filters():
    from app.database import SessionLocal
    from app.services.draft_response_service import DraftResponseService
    from app.services.review_decision_service import ReviewDecision

    db = SessionLocal()

    try:
        request_id = _create_test_hr_request_for_draft_audit(db)
        service = DraftResponseService(db)

        review_required_decision = ReviewDecision(
            action="review_required",
            review_required=True,
            priority="high",
            reason="Sensitive HR topic detected.",
            decision_source="deterministic",
        )

        draft = service.create_draft(
            request_id=request_id,
            body="Combined filter draft body.",
            review_decision=review_required_decision,
            recipient_email="combined.employee@example.com",
            subject="Re: HR concern",
        )

        response = client.get(
            "/drafts"
            "?status=draft"
            "&review_required=true"
            "&review_priority=high"
            "&review_action=review_required"
            "&recipient_email=combined.employee@example.com",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        assert any(
            item["draft_id"] == draft.draft_id
            and item["status"] == "draft"
            and item["review_required"] is True
            and item["review_priority"] == "high"
            and item["review_action"] == "review_required"
            and item["recipient_email"] == "combined.employee@example.com"
            for item in items
        )

    finally:
        db.close()

def test_audit_logs_filter_by_event_type():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        matching = service.create_event(
            event_type="draft_sent",
            resource_type="draft_response",
            resource_id="draft-filter-event-type",
            request_id="request-filter-event-type",
            user_id="audit-filter@example.com",
            details={"test": "event_type"},
        )

        service.create_event(
            event_type="draft_created",
            resource_type="draft_response",
            resource_id="draft-other-event-type",
            request_id="request-other-event-type",
            user_id="audit-filter@example.com",
            details={"test": "other"},
        )

        response = client.get(
            "/audit?event_type=draft_sent",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["id"] == matching.id for item in items)
        assert all(item["event_type"] == "draft_sent" for item in items)

    finally:
        db.close()

def test_audit_logs_filter_by_resource_type():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        matching = service.create_event(
            event_type="draft_approved",
            resource_type="draft_response",
            resource_id="draft-filter-resource-type",
            request_id="request-filter-resource-type",
            user_id="audit-resource@example.com",
            details={"test": "resource_type"},
        )

        service.create_event(
            event_type="request_processed",
            resource_type="hr_request",
            resource_id="request-other-resource-type",
            request_id="request-other-resource-type",
            user_id="audit-resource@example.com",
            details={"test": "other"},
        )

        response = client.get(
            "/audit?resource_type=draft_response",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["id"] == matching.id for item in items)
        assert all(item["resource_type"] == "draft_response" for item in items)

    finally:
        db.close()

def test_audit_logs_filter_by_resource_id():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        matching = service.create_event(
            event_type="draft_sent",
            resource_type="draft_response",
            resource_id="specific-draft-resource-id",
            request_id="request-specific-resource-id",
            user_id="audit-resource-id@example.com",
            details={"test": "resource_id"},
        )

        service.create_event(
            event_type="draft_sent",
            resource_type="draft_response",
            resource_id="different-draft-resource-id",
            request_id="request-different-resource-id",
            user_id="audit-resource-id@example.com",
            details={"test": "other"},
        )

        response = client.get(
            "/audit?resource_id=specific-draft-resource-id",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert len(items) >= 1
        assert any(item["id"] == matching.id for item in items)
        assert all(item["resource_id"] == "specific-draft-resource-id" for item in items)

    finally:
        db.close()

def test_audit_logs_support_combined_filters():
    from app.database import SessionLocal
    from app.services.audit_service import AuditService

    db = SessionLocal()

    try:
        service = AuditService(db)

        matching = service.create_event(
            event_type="draft_approved",
            resource_type="draft_response",
            resource_id="combined-draft-id",
            request_id="combined-request-id",
            user_id="combined-audit@example.com",
            details={"test": "combined"},
            status="success",
        )

        service.create_event(
            event_type="draft_approved",
            resource_type="draft_response",
            resource_id="other-combined-draft-id",
            request_id="other-combined-request-id",
            user_id="combined-audit@example.com",
            details={"test": "other"},
            status="success",
        )

        response = client.get(
            "/audit"
            "?event_type=draft_approved"
            "&resource_type=draft_response"
            "&resource_id=combined-draft-id"
            "&request_id=combined-request-id"
            "&user_id=combined-audit@example.com"
            "&status=success",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert len(items) >= 1
        assert any(item["id"] == matching.id for item in items)

        for item in items:
            assert item["event_type"] == "draft_approved"
            assert item["resource_type"] == "draft_response"
            assert item["resource_id"] == "combined-draft-id"
            assert item["request_id"] == "combined-request-id"
            assert item["user_id"] == "combined-audit@example.com"
            assert item["status"] == "success"

    finally:
        db.close()

def test_email_events_filter_by_status():
    from app.database import SessionLocal
    from app.services.email_event_service import EmailEventService

    db = SessionLocal()

    try:
        service = EmailEventService(db)

        processed_event = service.create_event(
            sender_email="status-filter@example.com",
            sender_name="Status Filter",
            subject="Processed event",
            body="Processed body",
            received_at=None,
            source="webhook",
        )
        service.mark_processed(
            event_id=processed_event.event_id,
            linked_request_id="request-status-filter",
        )

        service.create_event(
            sender_email="status-filter@example.com",
            sender_name="Status Filter",
            subject="Received event",
            body="Received body",
            received_at=None,
            source="webhook",
        )

        response = client.get(
            "/email-events?status=processed",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["event_id"] == processed_event.event_id for item in items)
        assert all(item["status"] == "processed" for item in items)

    finally:
        db.close()

def test_email_events_filter_by_sender_email():
    from app.database import SessionLocal
    from app.services.email_event_service import EmailEventService

    db = SessionLocal()

    try:
        service = EmailEventService(db)

        matching_event = service.create_event(
            sender_email="sender-filter@example.com",
            sender_name="Sender Filter",
            subject="Sender filter event",
            body="Sender filter body",
            received_at=None,
            source="webhook",
        )

        service.create_event(
            sender_email="other-sender@example.com",
            sender_name="Other Sender",
            subject="Other event",
            body="Other body",
            received_at=None,
            source="webhook",
        )

        response = client.get(
            "/email-events?sender_email=sender-filter@example.com",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["event_id"] == matching_event.event_id for item in items)
        assert all(
            item["sender_email"] == "sender-filter@example.com"
            for item in items
        )

    finally:
        db.close()

def test_email_events_filter_by_source():
    from app.database import SessionLocal
    from app.services.email_event_service import EmailEventService

    db = SessionLocal()

    try:
        service = EmailEventService(db)

        matching_event = service.create_event(
            sender_email="source-filter@example.com",
            sender_name="Source Filter",
            subject="Webhook source event",
            body="Webhook source body",
            received_at=None,
            source="webhook",
        )

        service.create_event(
            sender_email="source-filter@example.com",
            sender_name="Source Filter",
            subject="Manual source event",
            body="Manual source body",
            received_at=None,
            source="manual",
        )

        response = client.get(
            "/email-events?source=webhook",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["event_id"] == matching_event.event_id for item in items)
        assert all(item["source"] == "webhook" for item in items)

    finally:
        db.close()

def test_email_events_filter_by_linked_request_id():
    from app.database import SessionLocal
    from app.services.email_event_service import EmailEventService

    db = SessionLocal()

    try:
        service = EmailEventService(db)

        matching_event = service.create_event(
            sender_email="linked-request@example.com",
            sender_name="Linked Request",
            subject="Linked request event",
            body="Linked request body",
            received_at=None,
            source="webhook",
        )

        service.mark_processed(
            event_id=matching_event.event_id,
            linked_request_id="request-linked-filter",
        )

        other_event = service.create_event(
            sender_email="linked-request@example.com",
            sender_name="Linked Request",
            subject="Other linked request event",
            body="Other linked body",
            received_at=None,
            source="webhook",
        )

        service.mark_processed(
            event_id=other_event.event_id,
            linked_request_id="request-other-linked-filter",
        )

        response = client.get(
            "/email-events?linked_request_id=request-linked-filter",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["event_id"] == matching_event.event_id for item in items)
        assert all(
            item["linked_request_id"] == "request-linked-filter"
            for item in items
        )

    finally:
        db.close()

def test_email_events_support_combined_filters():
    from app.database import SessionLocal
    from app.services.email_event_service import EmailEventService

    db = SessionLocal()

    try:
        service = EmailEventService(db)

        matching_event = service.create_event(
            sender_email="combined-email-filter@example.com",
            sender_name="Combined Filter",
            subject="Combined filter event",
            body="Combined body",
            received_at=None,
            source="webhook",
        )

        service.mark_processed(
            event_id=matching_event.event_id,
            linked_request_id="request-combined-email-filter",
        )

        service.create_event(
            sender_email="combined-email-filter@example.com",
            sender_name="Combined Filter",
            subject="Non-processed event",
            body="Other body",
            received_at=None,
            source="manual",
        )

        response = client.get(
            "/email-events"
            "?status=processed"
            "&sender_email=combined-email-filter@example.com"
            "&source=webhook"
            "&linked_request_id=request-combined-email-filter",
            headers=REVIEWER_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()

        items = data["items"]

        assert any(item["event_id"] == matching_event.event_id for item in items)

        for item in items:
            assert item["status"] == "processed"
            assert item["sender_email"] == "combined-email-filter@example.com"
            assert item["source"] == "webhook"
            assert item["linked_request_id"] == "request-combined-email-filter"

    finally:
        db.close()


def test_drafts_endpoint_returns_pagination_metadata():
    response = client.get(
        "/drafts?limit=5&offset=0",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_audit_endpoint_returns_pagination_metadata():
    response = client.get(
        "/audit?limit=5&offset=0",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_email_events_endpoint_returns_pagination_metadata():
    response = client.get(
        "/email-events?limit=5&offset=0",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_hr_requests_endpoint_returns_pagination_metadata():
    response = client.get("/hr-requests?limit=5&offset=0")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0

def test_pii_redaction_redacts_email_addresses():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "Please contact kasun.perera@example.com about this request."
    )

    assert result.redacted_text == "Please contact [EMAIL] about this request."
    assert result.redaction_counts["EMAIL"] == 1
    assert service.has_redactions(result) is True

def test_pii_redaction_redacts_phone_numbers():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "My phone number is 0771234567 and my office number is +94 77 123 4567."
    )

    assert "[PHONE]" in result.redacted_text
    assert "0771234567" not in result.redacted_text
    assert "+94 77 123 4567" not in result.redacted_text
    assert result.redaction_counts["PHONE"] == 2

def test_pii_redaction_redacts_phone_numbers():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "My phone number is 0771234567 and my office number is +94 77 123 4567."
    )

    assert "[PHONE]" in result.redacted_text
    assert "0771234567" not in result.redacted_text
    assert "+94 77 123 4567" not in result.redacted_text
    assert result.redaction_counts["PHONE"] == 2

def test_pii_redaction_redacts_national_ids():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "My NIC is 991234567V and my new NIC is 199912345678."
    )

    assert result.redaction_counts["NATIONAL_ID"] == 2
    assert "991234567V" not in result.redacted_text
    assert "199912345678" not in result.redacted_text
    assert result.redacted_text.count("[NATIONAL_ID]") == 2

def test_pii_redaction_redacts_employee_ids():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "My employee id: 12345 and backup code EMP-009 should be checked."
    )

    assert result.redaction_counts["EMPLOYEE_ID"] == 2
    assert "12345" not in result.redacted_text
    assert "EMP-009" not in result.redacted_text
    assert result.redacted_text.count("[EMPLOYEE_ID]") == 2

def test_pii_redaction_redacts_urls_and_salary_amounts():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    result = service.redact(
        "See https://example.com/hr and my salary is LKR 250,000."
    )

    assert result.redaction_counts["URL"] == 1
    assert result.redaction_counts["SALARY"] == 1
    assert "https://example.com/hr" not in result.redacted_text
    assert "LKR 250,000" not in result.redacted_text
    assert "[URL]" in result.redacted_text
    assert "[SALARY]" in result.redacted_text

def test_pii_redaction_preserves_non_sensitive_text():
    from app.services.pii_redaction_service import PIIRedactionService

    service = PIIRedactionService()

    text = "I want to apply for annual leave next Monday."
    result = service.redact(text)

    assert result.redacted_text == text
    assert service.has_redactions(result) is False
    assert all(count == 0 for count in result.redaction_counts.values())

def test_llm_service_redacts_user_prompt_before_provider_call(monkeypatch):
    from app.services.llm_service import LLMService

    captured_messages = {}

    class MockMessage:
        content = "Mock response."

    class MockChoice:
        message = MockMessage()

    class MockResponse:
        choices = [MockChoice()]

    class MockCompletions:
        def create(self, model, messages, temperature):
            captured_messages["messages"] = messages
            captured_messages["temperature"] = temperature
            return MockResponse()

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        chat = MockChat()

    def mock_openai_client(*args, **kwargs):
        return MockClient()

    monkeypatch.setattr(
        "app.services.llm_service.OpenAI",
        mock_openai_client,
    )

    service = LLMService()

    response = service.chat_completion(
        system_prompt="You are an HR assistant.",
        user_prompt="Contact me at kasun@example.com or 0771234567.",
        temperature=0.1,
    )

    assert response == "Mock response."

    sent_user_prompt = captured_messages["messages"][1]["content"]

    assert "kasun@example.com" not in sent_user_prompt
    assert "0771234567" not in sent_user_prompt
    assert "[EMAIL]" in sent_user_prompt
    assert "[PHONE]" in sent_user_prompt
    assert service.last_redaction_counts["EMAIL"] == 1
    assert service.last_redaction_counts["PHONE"] == 1

def test_llm_service_does_not_redact_system_prompt(monkeypatch):
    from app.services.llm_service import LLMService

    captured_messages = {}

    class MockMessage:
        content = "Mock response."

    class MockChoice:
        message = MockMessage()

    class MockResponse:
        choices = [MockChoice()]

    class MockCompletions:
        def create(self, model, messages, temperature):
            captured_messages["messages"] = messages
            return MockResponse()

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        chat = MockChat()

    monkeypatch.setattr(
        "app.services.llm_service.OpenAI",
        lambda *args, **kwargs: MockClient(),
    )

    service = LLMService()

    service.chat_completion(
        system_prompt="System prompt with admin@example.com should remain unchanged.",
        user_prompt="Normal HR question without PII.",
    )

    sent_system_prompt = captured_messages["messages"][0]["content"]
    sent_user_prompt = captured_messages["messages"][1]["content"]

    assert sent_system_prompt == "System prompt with admin@example.com should remain unchanged."
    assert sent_user_prompt == "Normal HR question without PII."
    assert service.last_redaction_counts["EMAIL"] == 0

