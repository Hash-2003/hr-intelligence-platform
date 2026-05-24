import re
from dataclasses import dataclass
from datetime import date, timedelta


WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@dataclass
class LeaveDateFacts:
    """Resolved leave dates and notice-period status."""

    found_leave_dates: bool
    reference_date: date
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    submission_deadline: date | None
    notice_status: str
    original_phrase: str | None


class LeaveDateService:
    """Deterministic resolver for common leave-date phrases."""

    NOTICE_DAYS = 7

    def resolve(
        self,
        message: str,
        reference_date: date,
    ) -> LeaveDateFacts:
        """Resolve common leave-date phrases from a user request."""
        text = message.lower()

        start_date, original_phrase = self._resolve_start_date(
            text=text,
            reference_date=reference_date,
        )

        duration_days = self._extract_duration_days(text)

        if start_date is None:
            return LeaveDateFacts(
                found_leave_dates=False,
                reference_date=reference_date,
                start_date=None,
                end_date=None,
                duration_days=duration_days,
                submission_deadline=None,
                notice_status="unknown",
                original_phrase=None,
            )

        if duration_days is None:
            duration_days = 1

        end_date = start_date + timedelta(days=duration_days - 1)
        submission_deadline = start_date - timedelta(days=self.NOTICE_DAYS)

        if submission_deadline < reference_date:
            notice_status = "missed"
        elif submission_deadline == reference_date:
            notice_status = "deadline_today"
        else:
            notice_status = "not_missed"

        return LeaveDateFacts(
            found_leave_dates=True,
            reference_date=reference_date,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            submission_deadline=submission_deadline,
            notice_status=notice_status,
            original_phrase=original_phrase,
        )

    def build_context(self, facts: LeaveDateFacts) -> str:
        """Build a stable text context block for the Leave Agent."""
        if not facts.found_leave_dates:
            return (
                "No deterministic leave dates were resolved from the request. "
                "Ask for clarification if dates are required."
            )

        lines = [
            "Resolved leave date facts:",
            f"- reference date: {self._format_date(facts.reference_date)}",
            f"- original date phrase: {facts.original_phrase}",
            f"- requested start date: {self._format_date(facts.start_date)}",
            f"- requested duration: {facts.duration_days} day(s)",
            f"- requested end date: {self._format_date(facts.end_date)}",
            f"- standard annual leave notice period: {self.NOTICE_DAYS} days",
            f"- latest standard submission date: {self._format_date(facts.submission_deadline)}",
            f"- notice status: {facts.notice_status}",
        ]

        return "\n".join(lines)

    def _resolve_start_date(
        self,
        text: str,
        reference_date: date,
    ) -> tuple[date | None, str | None]:
        """Resolve supported start-date phrases."""
        for weekday in WEEKDAY_NAMES:
            if f"a week after next {weekday}" in text:
                next_weekday = self._next_weekday(reference_date, weekday)
                return (
                    next_weekday + timedelta(days=7),
                    f"a week after next {weekday}",
                )

            if f"one week after next {weekday}" in text:
                next_weekday = self._next_weekday(reference_date, weekday)
                return (
                    next_weekday + timedelta(days=7),
                    f"one week after next {weekday}",
                )

            if f"week after next {weekday}" in text:
                next_weekday = self._next_weekday(reference_date, weekday)
                return (
                    next_weekday + timedelta(days=7),
                    f"week after next {weekday}",
                )

        for weekday in WEEKDAY_NAMES:
            if f"next {weekday}" in text:
                return (
                    self._next_weekday(reference_date, weekday),
                    f"next {weekday}",
                )

        if "tomorrow" in text:
            return reference_date + timedelta(days=1), "tomorrow"

        if "today" in text:
            return reference_date, "today"

        return None, None

    @staticmethod
    def _extract_duration_days(text: str) -> int | None:
        """Extract duration such as 'for 2 days'."""
        match = re.search(r"\bfor\s+(\d+)\s+days?\b", text)

        if not match:
            return None

        duration = int(match.group(1))

        if duration <= 0:
            return None

        return duration

    @staticmethod
    def _next_weekday(reference_date: date, weekday_name: str) -> date:
        """Return the next occurrence of a weekday after the reference date."""
        weekday_index = WEEKDAY_NAMES.index(weekday_name)
        days_ahead = (weekday_index - reference_date.weekday()) % 7

        if days_ahead == 0:
            days_ahead = 7

        return reference_date + timedelta(days=days_ahead)

    @staticmethod
    def _format_date(value: date | None) -> str:
        """Format dates consistently for agent context."""
        if value is None:
            return "unknown"

        return f"{value.isoformat()} {value.strftime('%A')}"