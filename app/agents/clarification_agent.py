from app.services.llm_service import LLMService


class ClarificationAgent:
    """Specialist agent for ambiguous or low-confidence requests."""

    name = "clarification_agent"

    def __init__(self) -> None:
        self.llm_service = LLMService()

    def run(self, user_message: str, memory_context: str) -> str:
        """Generate a clarification response."""
        system_prompt = """
You are the Clarification Agent in an HR automation platform.

Your responsibilities:
- Handle unclear, incomplete, unrelated, or low-confidence requests.
- Ask one or two specific follow-up questions.
- Do not guess the user's intention when the request is ambiguous.
- Mention the supported areas if useful: scheduling, leave, and HR compliance.
- Keep the response polite and concise.
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
            temperature=0.3,
        )