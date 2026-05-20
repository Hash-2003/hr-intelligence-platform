from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import LongTermMemory, ShortTermMemory


class MemoryService:
    """Service layer for short-term and long-term memory operations."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def add_short_term_memory(
        self,
        user_id: str,
        content: str,
        intent: str | None = None,
        metadata_json: str | None = None,
    ) -> ShortTermMemory:
        """Add a short-term memory record with a default 24-hour expiry."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        memory = ShortTermMemory(
            user_id=user_id,
            content=content,
            intent=intent,
            expires_at=expires_at,
            metadata_json=metadata_json,
        )

        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        self._enforce_stm_limit(user_id=user_id)

        return memory

    def add_long_term_memory(
        self,
        user_id: str,
        content: str,
        significance_score: float,
        metadata_json: str | None = None,
    ) -> LongTermMemory:
        """Add a long-term memory record."""
        memory = LongTermMemory(
            user_id=user_id,
            content=content,
            significance_score=significance_score,
            metadata_json=metadata_json,
        )

        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        return memory

    def get_short_term_memory(self, user_id: str) -> list[ShortTermMemory]:
        """Return non-expired short-term memory records for a user."""
        now = datetime.now(timezone.utc)

        return (
            self.db.query(ShortTermMemory)
            .filter(ShortTermMemory.user_id == user_id)
            .filter(
                (ShortTermMemory.expires_at.is_(None))
                | (ShortTermMemory.expires_at > now)
            )
            .order_by(desc(ShortTermMemory.created_at))
            .limit(self.settings.stm_limit_per_user)
            .all()
        )

    def get_long_term_memory(self, user_id: str) -> list[LongTermMemory]:
        """Return long-term memory records for a user."""
        memories = (
            self.db.query(LongTermMemory)
            .filter(LongTermMemory.user_id == user_id)
            .order_by(desc(LongTermMemory.significance_score), desc(LongTermMemory.created_at))
            .limit(10)
            .all()
        )

        for memory in memories:
            memory.last_accessed_at = datetime.now(timezone.utc)

        self.db.commit()

        return memories

    def build_memory_context(self, user_id: str) -> tuple[str, bool]:
        """Build a text memory context block for LLM prompt injection."""
        stm_records = self.get_short_term_memory(user_id)
        ltm_records = self.get_long_term_memory(user_id)

        context_lines: list[str] = []

        if stm_records:
            context_lines.append("Short-term memory:")
            for item in stm_records:
                context_lines.append(f"- {item.content}")

        if ltm_records:
            context_lines.append("Long-term memory:")
            for item in ltm_records:
                context_lines.append(
                    f"- {item.content} "
                    f"(significance={item.significance_score:.2f})"
                )

        if not context_lines:
            return "No relevant memory found.", False

        return "\n".join(context_lines), True

    def score_significance(self, message: str, intent: str | None = None) -> float:
        """
        Score whether a message should be promoted to long-term memory.

        This deterministic scoring is intentionally transparent:
        - preferences and explicit memory instructions receive high scores
        - HR-related facts receive medium scores
        - generic messages receive low scores
        """
        text = message.lower()
        score = 0.1

        preference_markers = [
            "prefer",
            "usually",
            "always",
            "remember",
            "important",
            "my manager",
            "my team",
            "my department",
        ]

        time_markers = [
            "today",
            "tomorrow",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "next week",
            "morning",
            "evening",
        ]

        hr_markers = [
            "leave",
            "sick",
            "annual",
            "meeting",
            "interview",
            "salary",
            "policy",
            "contract",
            "overtime",
        ]

        if any(marker in text for marker in preference_markers):
            score += 0.4

        if any(marker in text for marker in time_markers):
            score += 0.2

        if any(marker in text for marker in hr_markers):
            score += 0.2

        if intent in {"leave", "scheduling", "compliance"}:
            score += 0.1

        return min(score, 1.0)

    def _enforce_stm_limit(self, user_id: str) -> None:
        """Keep only the latest configured number of STM records per user."""
        limit = self.settings.stm_limit_per_user

        records = (
            self.db.query(ShortTermMemory)
            .filter(ShortTermMemory.user_id == user_id)
            .order_by(desc(ShortTermMemory.created_at))
            .all()
        )

        records_to_delete = records[limit:]

        for record in records_to_delete:
            self.db.delete(record)

        self.db.commit()