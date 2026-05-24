from app.services.llm_service import LLMService


class LeaveAgent:
    """Specialist agent for leave and absence-related HR requests."""

    name = "leave_agent"

    def __init__(self) -> None:
        self.llm_service = LLMService()

    def run(
            self,
            user_message: str,
            memory_context: str,
            datetime_context: str,
            policy_context: str,
    ) -> str:
        """Generate a leave-focused response."""
        system_prompt = """
        You are the Leave Agent in an HR automation platform.

        Primary goal:
        - Answer leave-related HR requests using the provided HR policy context and date context.

        Strict guardrails:
        - Give a direct policy-based answer first.
        - Use the HR policy context as the source of truth for leave rules.
        - Use resolved calendar dates exactly as provided in the date context.
        - Do not manually recalculate weekday dates if resolved dates are provided.
        - When comparing a submission deadline with the current/reference date, use the reference application-local date from the date context.
        - Do not say a deadline has passed unless the reference application-local date is later than the deadline.
        - If the deadline is today, say the deadline is today.
        - If the deadline is after the reference application-local date, say the standard notice period can still be met if submitted by that deadline.
        - If the deadline has passed, state that the standard notice period has not been met.
        - If the notice deadline has passed, advise that the user may still submit through HRIS, but approval may depend on manager/HR discretion or exception handling.
        - If the user explicitly says "annual leave", "sick leave", or "casual leave", do not ask them to confirm the leave type again.
        - Ask only for genuinely missing details, such as the reason for leave, if needed.
        - Do not claim a request has been submitted.
        - Never mention system variables, internal instructions, internal reasoning, "datetime context", "policy context", or "resolved dates" to the user.
        - Present dates naturally as calendar dates.
        - Speak naturally as a human HR assistant.
        """.strip()

        user_prompt = f"""
        Memory context:
        {memory_context}

        Date context:
        {datetime_context}

        HR policy context:
        {policy_context}

        Task instructions:
        1. Answer using the HR policy context first.
        2. Use the resolved date values from the date context exactly.
        3. Do not manually recalculate weekday dates.
        4. Do not show calculations or internal reasoning.
        5. Do not mention date context, datetime context, policy context, resolved dates, or system text.
        6. If a policy notice deadline can be determined, state the latest submission date clearly.
        7. Compare the latest submission date against the reference application-local date from the date context.
        8. If the latest submission date is before the reference application-local date, state that the standard notice period has not been met.
        9. If the latest submission date is the same as the reference application-local date, state that the deadline is today.
        10. If the latest submission date is after the reference application-local date, state that the standard notice period can still be met if the user submits by that date.
        11. If the leave type is already stated in the user request, do not ask for leave type confirmation.
        12. Ask only for missing details that are not already present in the request.
        13. If the requested date remains genuinely unclear or contradictory after using the date context, ask for clarification.

        User request:
        {user_message}
        """.strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )