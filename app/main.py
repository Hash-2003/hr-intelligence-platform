from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_audit import router as audit_router
from app.api.routes_health import router as health_router
from app.api.routes_memory import router as memory_router
from app.api.routes_requests import router as requests_router
from app.api.routes_hr_requests import router as hr_requests_router
from app.api.routes_documents import router as documents_router
from app.config import get_settings
from app.database import create_db_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan hook used to initialize local database tables."""
    create_db_tables()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="LLM-powered HR intelligence platform for request routing, memory, audit logging, and document-aware automation.",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(memory_router)
app.include_router(audit_router)
app.include_router(requests_router)
app.include_router(hr_requests_router)
app.include_router(documents_router)


@app.get("/")
def root() -> dict:
    """Return basic API information."""
    return {
        "message": "HR Intelligence Platform API",
        "docs": "/docs",
        "health": "/health",
        "requests": "/requests",
        "memory": "/memory/{user_id}",
        "audit": "/audit",
        "hr_requests": "/hr-requests",
        "documents": "/documents",
    }