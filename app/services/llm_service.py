import json
from typing import Any

from openai import OpenAI, OpenAIError

from app.config import get_settings


class LLMServiceError(Exception):
    """Raised when the LLM service fails safely."""


class LLMService:
    """Centralized service for OpenAI-compatible LLM API calls."""

    def __init__(self) -> None:
        self.settings = get_settings()

        if not self.settings.llm_api_key:
            raise LLMServiceError("LLM API key is not configured.")

        self.client = OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request to the configured LLM provider."""
        try:
            response = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )

            content = response.choices[0].message.content

            if not content:
                raise LLMServiceError("LLM returned an empty response.")

            return content.strip()

        except OpenAIError as exc:
            raise LLMServiceError("LLM provider request failed.") from exc
        except Exception as exc:
            raise LLMServiceError("Unexpected LLM service failure.") from exc

    @staticmethod
    def parse_json_response(content: str) -> dict[str, Any]:
        """Parse an LLM JSON response safely."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMServiceError("LLM returned invalid JSON.") from exc