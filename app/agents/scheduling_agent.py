from app.services.llm_service import LLMService


class SchedulingAgent:
    """Specialist agent for meeting, interview, and scheduling requests."""

    name = "scheduling_agent"

    def __init__(self) -> None:
        self.llm_service = LLMService()

    def run(
            self,
            user_message: str,
            memory_context: str,
            datetime_context: str,
            policy_context: str = "No relevant HR policy context required.",

    ) -> str:
        """Generate a scheduling-focused response."""
        system_prompt = """
        You are the Scheduling Agent in an HR automation platform.

        Your responsibilities:
        - Help with meetings, interviews, calendar coordination, and rescheduling.
        - Use the provided memory context when relevant.
        - Ask for missing details such as date, time, attendee names, or meeting purpose.
        - Do not claim that a real calendar event has been created.
        - Keep the response polite, concise, and operational.
        """.strip()

        user_prompt = f"""
        Memory context:
        {memory_context}

        Datetime context:
        {datetime_context}

        HR policy context:
        {policy_context}

        Instruction:
        Use the resolved date values in the datetime context exactly.
        Do not manually recalculate weekday dates.
        If the user provides a relative date, use the resolved date from the datetime context.
        Ask for confirmation only if the date or time remains genuinely ambiguous.

        User request:
        {user_message}
        """.strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )