from app.services.llm_service import LLMService


class ComplianceAgent:
    """Specialist agent for HR policy and compliance-related requests."""

    name = "compliance_agent"

    def __init__(self) -> None:
        self.llm_service = LLMService()

    def run(
            self,
            user_message: str,
            memory_context: str,
            policy_context: str,
    ) -> str:
        """Generate a compliance-focused response."""
        system_prompt = """
        You are the Compliance Agent in an HR automation platform.

        Your responsibilities:
- Answer HR policy and compliance questions using the provided HR policy context.
- Treat user questions as good-faith policy clarification requests unless there is clear harmful intent.
- Give a direct policy-based answer before recommending escalation.
- Do not accuse the user of trying to bypass or circumvent policy.
- Be careful with legal or employment-law questions.
- Do not present yourself as a legal authority.
- Recommend contacting HR or legal professionals for final decisions when appropriate.
- If the policy context does not contain enough information, say what information is missing.
- Keep the response polite, concise, and safe.
        """.strip()

        user_prompt = f"""
Memory context:
{memory_context}

HR policy context:
{policy_context}

Instruction:
Answer using the HR policy context first. If the policy gives a clear answer, state it directly.

User request:
{user_message}
""".strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )