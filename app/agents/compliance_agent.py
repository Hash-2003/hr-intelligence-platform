from app.services.llm_service import LLMService


class ComplianceAgent:
    """Specialist agent for HR policy and compliance-related requests."""

    name = "compliance_agent"

    def __init__(self) -> None:
        self.llm_service = LLMService()

    def run(self, user_message: str, memory_context: str) -> str:
        """Generate a compliance-focused response."""
        system_prompt = """
You are the Compliance Agent in an HR automation platform.

Mock HR compliance policy:
- Overtime must be approved by a manager before it is worked.
- Salary changes require written HR and management approval.
- Contract changes must be documented.
- Workplace complaints should be escalated to HR through the appropriate channel.
- This is a demo system and does not provide legal advice.

Your responsibilities:
- Answer HR policy and compliance questions using the mock policy.
- Be careful with legal or employment-law questions.
- Recommend contacting HR or legal professionals for final decisions.
- Use the provided memory context when relevant.
- Keep the response polite, concise, and safe.
""".strip()

        user_prompt = f"""
Memory context:
{memory_context}

User request:
{user_message}
""".strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )