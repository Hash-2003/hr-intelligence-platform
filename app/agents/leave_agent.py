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
            policy_context: str,
    ) -> str:
        """Generate a leave-focused response."""
        system_prompt = """
You are the Leave Agent in an HR automation platform.

Your responsibilities:
- Help users understand or prepare leave requests.
- Use the provided HR policy context when it is relevant.
- Ask for missing details such as leave type, start date, end date, and reason when needed.
- Do not claim that leave has been officially submitted unless this is only described as a mock/demo action.
- If the policy context does not contain enough information, say what information is missing.
- Keep the response polite, concise, and practical.
""".strip()

        user_prompt = f"""
Memory context:
{memory_context}

HR policy context:
{policy_context}

User request:
{user_message}
""".strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )