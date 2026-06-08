import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    """Result returned after redacting sensitive text."""

    redacted_text: str
    redaction_counts: dict[str, int]


class PIIRedactionService:
    """Deterministic PII redaction service for prompt-safety preparation."""

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    URL_PATTERN = re.compile(
        r"\b(?:https?://|www\.)[^\s<>\"]+",
        re.IGNORECASE,
    )

    # Sri Lankan mobile/landline-ish formats and common international format.
    # Examples:
    # 0771234567, 071-123-4567, +94771234567, +94 77 123 4567
    PHONE_PATTERN = re.compile(
        r"(?<!\w)(?:\+94[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}|0\d{2}[\s-]?\d{3}[\s-]?\d{4})(?!\w)"
    )

    # Sri Lankan NIC examples:
    # 991234567V, 991234567X, 199912345678
    NATIONAL_ID_PATTERN = re.compile(
        r"(?<!\w)(?:\d{9}[VvXx]|\d{12})(?!\w)"
    )

    # Employee ID examples:
    # EMP001, EMP-001, EMP_001, employee id: 12345, employee number 12345
    EMPLOYEE_ID_PATTERN = re.compile(
        r"(?<!\w)(?:EMP[-_]?\d{3,10}|employee\s+(?:id|number)\s*[:#-]?\s*\d{3,10})(?!\w)",
        re.IGNORECASE,
    )

    SALARY_PATTERN = re.compile(
        r"(?<!\w)(?:LKR|Rs\.?|රු\.?)\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?!\w)",
        re.IGNORECASE,
    )

    REDACTION_RULES = [
        ("EMAIL", EMAIL_PATTERN, "[EMAIL]"),
        ("URL", URL_PATTERN, "[URL]"),
        ("PHONE", PHONE_PATTERN, "[PHONE]"),
        ("NATIONAL_ID", NATIONAL_ID_PATTERN, "[NATIONAL_ID]"),
        ("EMPLOYEE_ID", EMPLOYEE_ID_PATTERN, "[EMPLOYEE_ID]"),
        ("SALARY", SALARY_PATTERN, "[SALARY]"),
    ]

    def redact(self, text: str) -> RedactionResult:
        """Redact known sensitive patterns from text."""
        redacted_text = text
        redaction_counts: dict[str, int] = {}

        for label, pattern, replacement in self.REDACTION_RULES:
            redacted_text, count = pattern.subn(replacement, redacted_text)
            redaction_counts[label] = count

        return RedactionResult(
            redacted_text=redacted_text,
            redaction_counts=redaction_counts,
        )

    def has_redactions(self, result: RedactionResult) -> bool:
        """Return whether any redaction occurred."""
        return any(count > 0 for count in result.redaction_counts.values())