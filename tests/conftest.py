import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Force tests to use a separate SQLite database before app/database imports.
TEST_DATABASE_PATH = Path("test_hr_intelligence_platform.db")
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DATABASE_PATH}"

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

print("TEST DATABASE URL:", engine.url)
def override_get_db():
    """Provide test database sessions to FastAPI routes."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_test_database():
    """Reset all database tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield


@pytest.fixture
def client():
    """FastAPI test client using the isolated test database."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Direct database session for service-level tests."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

assert "test_hr_intelligence_platform.db" in str(engine.url), (
    f"Tests are not using the isolated test database. Current DB: {engine.url}"
)