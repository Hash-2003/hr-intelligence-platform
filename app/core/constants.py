from enum import StrEnum


class DraftStatus(StrEnum):
    """Allowed draft response statuses."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class ReviewAction(StrEnum):
    """Allowed review decision actions."""

    AUTO_RESPONSE = "auto_response"
    REVIEW_OPTIONAL = "review_optional"
    REVIEW_REQUIRED = "review_required"
    ESCALATED = "escalated"


class ReviewPriority(StrEnum):
    """Allowed review priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailEventStatus(StrEnum):
    """Allowed email event statuses."""

    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class AuditEventType(StrEnum):
    """Known audit event types."""

    REQUEST_PROCESSED = "request_processed"
    DRAFT_CREATED = "draft_created"
    DRAFT_UPDATED = "draft_updated"
    DRAFT_APPROVED = "draft_approved"
    DRAFT_REJECTED = "draft_rejected"
    DRAFT_SENT = "draft_sent"


class ResourceType(StrEnum):
    """Known audit resource types."""

    HR_REQUEST = "hr_request"
    DRAFT_RESPONSE = "draft_response"
    EMAIL_EVENT = "email_event"