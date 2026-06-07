from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.hr_request_schema import (
    AgentRunResponse,
    HRRequestListResponse,
    HRRequestResponse,
    RequestPolicySourceResponse,
)
from app.services.hr_request_service import HRRequestService

router = APIRouter(prefix="/hr-requests", tags=["HR Requests"])


@router.get("", response_model=HRRequestListResponse)
def get_hr_requests(
    user_id: str | None = None,
    status: str | None = None,
    intent: str | None = None,
    source_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> HRRequestListResponse:
    """Retrieve HR requests with optional filters and pagination metadata."""
    service = HRRequestService(db)
    requests, total = service.get_requests(
        user_id=user_id,
        status=status,
        intent=intent,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )

    return HRRequestListResponse(
        items=[
            HRRequestResponse.model_validate(request)
            for request in requests
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{request_id}", response_model=HRRequestResponse)
def get_hr_request(
    request_id: str,
    db: Session = Depends(get_db),
) -> HRRequestResponse:
    """Retrieve one HR request by request ID."""
    service = HRRequestService(db)
    request = service.get_request_by_id(request_id)

    if request is None:
        raise HTTPException(status_code=404, detail="HR request not found.")

    return HRRequestResponse.model_validate(request)


@router.get("/{request_id}/agent-runs", response_model=list[AgentRunResponse])
def get_hr_request_agent_runs(
    request_id: str,
    db: Session = Depends(get_db),
) -> list[AgentRunResponse]:
    """Retrieve agent runs for one HR request."""
    service = HRRequestService(db)

    request = service.get_request_by_id(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="HR request not found.")

    runs = service.get_agent_runs(request_id)

    return [
        AgentRunResponse.model_validate(run)
        for run in runs
    ]


@router.get("/{request_id}/policy-sources", response_model=list[RequestPolicySourceResponse])
def get_hr_request_policy_sources(
    request_id: str,
    db: Session = Depends(get_db),
) -> list[RequestPolicySourceResponse]:
    """Retrieve policy document chunks used by one HR request."""
    service = HRRequestService(db)

    request = service.get_request_by_id(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="HR request not found.")

    sources = service.get_policy_sources(request_id)

    return [
        RequestPolicySourceResponse.model_validate(source)
        for source in sources
    ]