from fastapi.testclient import TestClient

from app.database import create_db_tables
from app.main import app

from pathlib import Path
from datetime import date

from app.services.leave_date_service import LeaveDateService


create_db_tables()
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