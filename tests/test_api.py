import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

from pathlib import Path
from datetime import date

from app.services.leave_date_service import LeaveDateService
from app.services.review_decision_service import ReviewDecisionService, ReviewDecision


client = TestClient(app)


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
    response = client.get("/audit")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)

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

    assert isinstance(data, list)


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

        audit_logs = service.audit_service.get_logs(
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

        audit_logs = service.audit_service.get_logs(
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

        audit_logs = service.audit_service.get_logs(
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

        audit_logs = service.audit_service.get_logs(
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

        updated = service.update_draft_body(
            draft_id=draft.draft_id,
            body="Should not update.",
        )

        assert updated is None

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

        audit_logs = service.audit_service.get_logs(
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

        sent = service.send_draft(draft.draft_id)

        assert sent is None

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

        approve_response = client.post(f"/drafts/{draft.draft_id}/approve")

        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        send_response = client.post(f"/drafts/{draft.draft_id}/send")

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

        response = client.post(f"/drafts/{draft.draft_id}/send")

        assert response.status_code == 404
        assert response.json()["detail"] == "Draft response not found or cannot be sent."

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

        response = client.get("/drafts?status=approved")

        assert response.status_code == 200
        data = response.json()

        assert any(
            item["draft_id"] == draft.draft_id
            and item["status"] == "approved"
            for item in data
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

        response = client.get("/drafts?review_priority=high")

        assert response.status_code == 200
        data = response.json()

        assert any(
            item["draft_id"] == draft.draft_id
            and item["review_priority"] == "high"
            for item in data
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

        response = client.get("/drafts?review_action=review_required")

        assert response.status_code == 200
        data = response.json()

        assert any(
            item["draft_id"] == draft.draft_id
            and item["review_action"] == "review_required"
            for item in data
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
            "/drafts?recipient_email=specific.employee@example.com"
        )

        assert response.status_code == 200
        data = response.json()

        assert any(
            item["draft_id"] == draft.draft_id
            and item["recipient_email"] == "specific.employee@example.com"
            for item in data
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
            "&recipient_email=combined.employee@example.com"
        )

        assert response.status_code == 200
        data = response.json()

        assert any(
            item["draft_id"] == draft.draft_id
            and item["status"] == "draft"
            and item["review_required"] is True
            and item["review_priority"] == "high"
            and item["review_action"] == "review_required"
            and item["recipient_email"] == "combined.employee@example.com"
            for item in data
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

        response = client.get("/audit?event_type=draft_sent")

        assert response.status_code == 200
        data = response.json()

        assert any(item["id"] == matching.id for item in data)
        assert all(item["event_type"] == "draft_sent" for item in data)

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

        response = client.get("/audit?resource_type=draft_response")

        assert response.status_code == 200
        data = response.json()

        assert any(item["id"] == matching.id for item in data)
        assert all(item["resource_type"] == "draft_response" for item in data)

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

        response = client.get("/audit?resource_id=specific-draft-resource-id")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        assert any(item["id"] == matching.id for item in data)
        assert all(item["resource_id"] == "specific-draft-resource-id" for item in data)

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
            "&status=success"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        assert any(item["id"] == matching.id for item in data)

        for item in data:
            assert item["event_type"] == "draft_approved"
            assert item["resource_type"] == "draft_response"
            assert item["resource_id"] == "combined-draft-id"
            assert item["request_id"] == "combined-request-id"
            assert item["user_id"] == "combined-audit@example.com"
            assert item["status"] == "success"

    finally:
        db.close()
