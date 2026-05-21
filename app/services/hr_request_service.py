from datetime import datetime, timezone
from typing import cast

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import AgentRun, HRRequest, RequestPolicySource


class HRRequestService:
    """Service layer for HR request and agent run persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        request_id: str,
        user_id: str,
        message: str,
        source_type: str = "api",
        subject: str | None = None,
    ) -> HRRequest:
        """Create a new HR request record."""
        request = HRRequest(
            request_id=request_id,
            user_id=user_id,
            source_type=source_type,
            subject=subject,
            message=message,
            status="new",
        )

        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)

        return request

    def update_request_result(
        self,
        request_id: str,
        intent: str | None,
        confidence: float | None,
        selected_agent: str | None,
        response: str | None,
        status: str,
        error_message: str | None = None,
    ) -> HRRequest | None:
        """Update an HR request with classification and response results."""
        request = cast(
            HRRequest | None,
            self.db.query(HRRequest)
            .filter(HRRequest.request_id == request_id)
            .first(),
        )

        if request is None:
            return None

        request.intent = intent
        request.confidence = confidence
        request.selected_agent = selected_agent
        request.response = response
        request.status = status
        request.error_message = error_message
        request.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(request)

        return request

    def create_agent_run(
        self,
        request_id: str,
        agent_name: str,
        input_summary: str | None,
        output_summary: str | None,
        status: str,
        error_message: str | None = None,
    ) -> AgentRun:
        """Create an agent execution record."""
        agent_run = AgentRun(
            request_id=request_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=output_summary,
            status=status,
            error_message=error_message,
            completed_at=datetime.now(timezone.utc),
        )

        self.db.add(agent_run)
        self.db.commit()
        self.db.refresh(agent_run)

        return agent_run

    def get_requests(self, user_id: str | None = None, limit: int = 50) -> list[HRRequest]:
        """Retrieve HR requests, optionally filtered by user."""
        query = self.db.query(HRRequest)

        if user_id:
            query = query.filter(HRRequest.user_id == user_id)

        return cast(
            list[HRRequest],
            query.order_by(desc(HRRequest.created_at)).limit(limit).all(),
        )

    def get_request_by_id(self, request_id: str) -> HRRequest | None:
        """Retrieve one HR request by request ID."""
        return (
            self.db.query(HRRequest)
            .filter(HRRequest.request_id == request_id)
            .first()
        )

    def get_agent_runs(self, request_id: str) -> list[AgentRun]:
        """Retrieve agent runs for a specific HR request."""
        return cast(
            list[AgentRun],
            self.db.query(AgentRun)
            .filter(AgentRun.request_id == request_id)
            .order_by(desc(AgentRun.started_at))
            .all(),
        )

    def create_policy_sources(
            self,
            request_id: str,
            policy_sources: list[dict],
    ) -> list[RequestPolicySource]:
        """Persist policy document chunks used by a request."""
        records: list[RequestPolicySource] = []

        for source in policy_sources:
            record = RequestPolicySource(
                request_id=request_id,
                document_id=source["document_id"],
                document_title=source["document_title"],
                filename=source["filename"],
                chunk_id=source["chunk_id"],
                chunk_index=source["chunk_index"],
                score=source["score"],
            )

            self.db.add(record)
            records.append(record)

        self.db.commit()

        for record in records:
            self.db.refresh(record)

        return records

    def get_policy_sources(self, request_id: str) -> list[RequestPolicySource]:
        """Retrieve policy sources used by one HR request."""
        return cast(
            list[RequestPolicySource],
            self.db.query(RequestPolicySource)
            .filter(RequestPolicySource.request_id == request_id)
            .order_by(RequestPolicySource.score.desc())
            .all(),
        )