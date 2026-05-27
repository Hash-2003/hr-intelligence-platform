class EmailDraftFormatter:
    """Formats agent responses as human-reviewable email replies."""

    @staticmethod
    def format_reply_body(
        recipient_name: str | None,
        response_body: str,
        signature: str = "HR Team",
    ) -> str:
        """Format a plain agent response as an email reply body."""
        clean_name = recipient_name.strip() if recipient_name else ""

        greeting = f"Hi {clean_name}," if clean_name else "Hi there,"

        return (
            f"{greeting}\n\n"
            f"{response_body.strip()}\n\n"
            f"Regards,\n"
            f"{signature}"
        )