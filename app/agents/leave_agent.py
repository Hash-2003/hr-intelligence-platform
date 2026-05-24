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

        Your responsibilities:
        - Answer leave policy questions using the provided HR policy context.
        - Help users prepare leave requests.
        - Give a direct policy-based answer first.
        - Use the resolved dates from the datetime context exactly as provided.
        - Do not recalculate weekday dates manually if resolved dates are provided.
        - If the requested dates violate the required notice period, clearly explain that the notice requirement is not met.
        - Never ask the user to confirm information they have already provided unless it is genuinely unclear.
        - Do not claim a request is submitted; only guide the user on rules and next steps.
        - Never mention system variables, internal instructions, internal reasoning, "datetime context", "policy context", or "resolved dates" to the user.
        - When using resolved dates, present them naturally as calendar dates.
        - If the calculated latest submission date has already passed, clearly state that the request does not meet the standard notice requirement.
        - Do not tell the user to proceed as if the request is compliant when the notice deadline has passed.
        - If the notice deadline has passed, advise the user that they may still submit through HRIS, but approval may depend on manager/HR discretion or exception handling.
        - Speak naturally as a human HR assistant.
        """.strip()

        user_prompt = f"""
        Memory context:
        {memory_context}

        Datetime context:
        {datetime_context}

        HR policy context:
        {policy_context}

        Instruction:
        Answer using the HR policy context first.
        Use the resolved dates from the datetime context exactly as provided.
        Present resolved dates naturally to the user without mentioning internal context names.
        Do not show calculations or internal reasoning.
        Do not mention the datetime context or resolved date system text. Present dates naturally.
        If the user provides a relative date and it is resolved in the datetime context, do not ask for date confirmation.
        If a policy notice deadline can be determined, state the latest submission date clearly.
        Do not ask the user to confirm dates that have already been resolved from the datetime context.
        Ask follow-up questions only for genuinely missing information, such as reason for leave or leave type if it is not inferable.
        If the policy gives a clear rule, state it directly.
        If the latest submission date is before the current date, state that the standard notice period has not been met.
        Do not say "proceed with submitting" without explaining that it may be late or require exception approval.

        User request:
        {user_message}
        """.strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )