from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.services.llm_service import LLMService, LLMServiceError

ALLOWED_INTENTS = {"scheduling", "leave", "compliance", "clarification"}


class IntentClassificationResult(BaseModel):
    """Validated result of intent classification."""

    intent: str = Field(..., description="One of the allowed HR routing intents.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str = Field(..., min_length=1, max_length=500)


class IntentClassifier:
    """LLM-powered intent classifier for HR automation requests."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm_service = LLMService()

    def classify(
        self,
        message: str,
        memory_context: str,
    ) -> IntentClassificationResult:
        """Classify a user message into an HR intent using an LLM."""
        system_prompt = """
You are an intent classification engine for an HR automation platform.

Classify the user's request into exactly one of these intents:
- scheduling
- leave
- compliance
- clarification

Intent definitions:
- scheduling: meetings, interviews, calendar events, rescheduling, appointment coordination
- leave: annual leave, sick leave, vacation, absence, leave balance, time off
- compliance: HR policy, workplace rules, contracts, overtime, salary, legal/policy questions
- clarification: unclear, unrelated, missing critical information, or not enough confidence

Return only valid JSON. Do not include markdown. Do not include explanations outside JSON.

Required JSON schema:
{
  "intent": "scheduling | leave | compliance | clarification",
  "confidence": 0.0,
  "reasoning_summary": "short explanation"
}
""".strip()

        user_prompt = f"""
Memory context:
{memory_context}

User request:
{message}
""".strip()

        try:
            raw_response = self.llm_service.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )

            parsed = self.llm_service.parse_json_response(raw_response)
            result = IntentClassificationResult.model_validate(parsed)

            if result.intent not in ALLOWED_INTENTS:
                return self._clarification_result(
                    "LLM returned an unsupported intent."
                )

            if result.confidence < self.settings.intent_confidence_threshold:
                return IntentClassificationResult(
                    intent="clarification",
                    confidence=result.confidence,
                    reasoning_summary=(
                        f"Confidence below threshold. Original reason: "
                        f"{result.reasoning_summary}"
                    ),
                )

            return result

        except (LLMServiceError, ValidationError) as exc:
            return self._clarification_result(
                f"Intent classification failed safely: {exc}"
            )

    @staticmethod
    def _clarification_result(reason: str) -> IntentClassificationResult:
        """Return a safe clarification result."""
        return IntentClassificationResult(
            intent="clarification",
            confidence=0.0,
            reasoning_summary=reason,
        )