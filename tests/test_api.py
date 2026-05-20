from fastapi.testclient import TestClient

from app.database import create_db_tables
from app.main import app


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