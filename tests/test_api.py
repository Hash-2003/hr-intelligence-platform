from fastapi.testclient import TestClient

from app.database import create_db_tables
from app.main import app

from pathlib import Path


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