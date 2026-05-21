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
        - Answer leave policy questions using the provided HR policy context.
        - Read the full HR policy context carefully before answering.
        - Give a direct policy-based answer first when the policy context contains a clear rule.
        - For leave application requests, ask for missing details such as leave type, start date, end date, and reason when needed.
        - Do not claim that leave has been officially submitted unless this is only described as a mock/demo action.
        - Do not say the policy is unclear if the provided context contains a relevant rule.
        - If the policy context does not contain enough information, say exactly what information is missing.
        - Keep the response polite, concise, and practical.
        """.strip()

        user_prompt = f"""
Memory context:
{memory_context}

HR policy context:
{policy_context}

Instruction:
Answer using the HR policy context first.
If the policy context contains a direct rule, state that rule clearly.
For yes/no or factual policy questions, answer directly before asking follow-up questions.
Do not invent uncertainty when the policy context provides a clear answer.

User request:
{user_message}
""".strip()

        return self.llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )