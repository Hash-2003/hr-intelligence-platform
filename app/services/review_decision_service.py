import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ReviewDecision:
    """Decision describing whether a generated HR response needs human review."""

    action: str
    review_required: bool
    priority: str
    reason: str
    decision_source: str


class ReviewDecisionService:
    """Hybrid review decision layer for risk-based human-in-the-loop handling.

    Deterministic rules are used as the final authority for obvious cases.
    An optional LLM classifier can be used only for ambiguous cases.
    """

    SAFETY_TERMS = {
        "unsafe",
        "danger",
        "emergency",
        "threat",
        "threatened",
        "weapon",
        "police",
        "ambulance",
        "hospital",
    }

    HIGH_RISK_TERMS = {
        "harassment",
        "harassed",
        "harassing",
        "discrimination",
        "discriminated",
        "discriminating",
        "retaliation",
        "retaliated",
        "misconduct",
        "bullying",
        "bullied",
        "hostile",
        "stalking",
        "assault",
        "abuse",
    }

    SENSITIVE_HR_TERMS = {
        "salary",
        "payroll",
        "wage",
        "wages",
        "paycheck",
        "compensation",
        "bonus",
        "contract",
        "termination",
        "terminated",
        "fired",
        "dismissed",
        "demotion",
        "demoted",
        "resign",
        "resigning",
        "quitting",
        "disciplinary",
        "grievance",
        "complaint",
        "medical",
        "diagnosis",
        "sick leave",
        "maternity",
        "paternity",
        "pregnancy",
        "disability",
        "accommodation",
    }

    LEGAL_COMPLIANCE_TERMS = {
        "lawyer",
        "attorney",
        "lawsuit",
        "sue",
        "sued",
        "legal action",
        "whistleblower",
        "labor board",
    }

    SECURITY_DATA_TERMS = {
        "hacked",
        "stolen laptop",
        "data breach",
        "leaked",
        "phishing",
        "unauthorized access",
    }

    SOFT_RISK_TERMS = {
        "uncomfortable",
        "inappropriate",
        "toxic",
        "unfair",
        "concern",
        "issue with my manager",
        "treated badly",
    }

    LOW_RISK_POLICY_QUESTION_PATTERNS = {
        "how many annual leave",
        "how do i apply",
        "what is the policy",
        "what is the overtime policy",
        "how should i submit",
        "where can i report",
    }

    def __init__(self, llm_service: Any | None = None):
        self.llm_service = llm_service

    def decide(
        self,
        message: str,
        intent: str | None,
        confidence: float | None,
        selected_agent: str | None,
        policy_sources_used: list[dict] | None = None,
        status: str = "success",
    ) -> ReviewDecision:
        """Return a review decision for an HR request."""
        normalized_text = self._normalize_text(message)
        sources = policy_sources_used or []

        deterministic_decision = self._deterministic_decision(
            text=normalized_text,
            intent=intent,
            confidence=confidence,
            selected_agent=selected_agent,
            policy_sources_used=sources,
            status=status,
        )

        if deterministic_decision.action != "needs_llm_review_classification":
            return deterministic_decision

        llm_decision = self._llm_assisted_decision(
            message=message,
            intent=intent,
            confidence=confidence,
            selected_agent=selected_agent,
        )

        if llm_decision is not None:
            return llm_decision

        return ReviewDecision(
            action="review_required",
            review_required=True,
            priority="medium",
            reason="Ambiguous HR request could not be safely classified automatically.",
            decision_source="deterministic_fallback",
        )

    def _deterministic_decision(
        self,
        text: str,
        intent: str | None,
        confidence: float | None,
        selected_agent: str | None,
        policy_sources_used: list[dict],
        status: str,
    ) -> ReviewDecision:
        """Apply deterministic review rules."""
        if status != "success":
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="high",
                reason="Workflow did not complete successfully.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.SAFETY_TERMS):
            return ReviewDecision(
                action="escalated",
                review_required=True,
                priority="critical",
                reason="Safety-sensitive or emergency-related message detected.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.LEGAL_COMPLIANCE_TERMS):
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="high",
                reason="Legal, whistleblowing, or external complaint-related term detected.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.SECURITY_DATA_TERMS):
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="high",
                reason="Security or data-protection concern detected.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.HIGH_RISK_TERMS):
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="high",
                reason="Sensitive workplace misconduct concern detected.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.SENSITIVE_HR_TERMS):
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="high",
                reason="Sensitive HR topic detected.",
                decision_source="deterministic",
            )

        if confidence is not None and confidence < 0.75:
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="medium",
                reason="Intent confidence is below review threshold.",
                decision_source="deterministic",
            )

        if intent in {"leave", "compliance"} and not policy_sources_used:
            return ReviewDecision(
                action="review_required",
                review_required=True,
                priority="medium",
                reason="No policy source was used for a policy-sensitive request.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.SOFT_RISK_TERMS):
            return ReviewDecision(
                action="needs_llm_review_classification",
                review_required=True,
                priority="medium",
                reason="Ambiguous soft-risk workplace concern detected.",
                decision_source="deterministic",
            )

        if self._contains_any(text, self.LOW_RISK_POLICY_QUESTION_PATTERNS):
            return ReviewDecision(
                action="auto_response",
                review_required=False,
                priority="low",
                reason="Low-risk policy question detected.",
                decision_source="deterministic",
            )

        if intent == "leave":
            return ReviewDecision(
                action="review_optional",
                review_required=False,
                priority="medium",
                reason="Leave request detected; draft may be reviewed before action.",
                decision_source="deterministic",
            )

        if intent == "scheduling":
            return ReviewDecision(
                action="review_optional",
                review_required=False,
                priority="low",
                reason="Scheduling request detected.",
                decision_source="deterministic",
            )

        if intent == "compliance":
            return ReviewDecision(
                action="auto_response",
                review_required=False,
                priority="low",
                reason="Low-risk compliance policy question with policy context.",
                decision_source="deterministic",
            )

        return ReviewDecision(
            action="needs_llm_review_classification",
            review_required=True,
            priority="medium",
            reason="Request is ambiguous and needs risk classification.",
            decision_source="deterministic",
        )

    def _llm_assisted_decision(
        self,
        message: str,
        intent: str | None,
        confidence: float | None,
        selected_agent: str | None,
    ) -> ReviewDecision | None:
        """Use an optional LLM classifier for ambiguous review decisions."""
        if self.llm_service is None:
            return None

        system_prompt = """
You are a strict HR review-risk classifier.

Classify whether an employee HR message requires human HR review.

Return ONLY valid JSON with these keys:
{
  "action": "auto_response" | "review_optional" | "review_required" | "escalated",
  "priority": "low" | "medium" | "high" | "critical",
  "reason": "short reason"
}

Rules:
- If the message may involve workplace misconduct, legal concerns, compensation disputes, medical sensitivity, safety concerns, or employee relations risk, choose review_required or escalated.
- If the message is a simple low-risk policy question, choose auto_response.
- If the message is a normal action request but not highly sensitive, choose review_optional.
- Do not include markdown.
- Do not include explanations outside JSON.
""".strip()

        user_prompt = f"""
Message:
{message}

Intent:
{intent}

Intent confidence:
{confidence}

Selected agent:
{selected_agent}
""".strip()

        try:
            raw_response = self.llm_service.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
            )

            parsed = json.loads(raw_response)

            action = parsed.get("action")
            priority = parsed.get("priority")
            reason = parsed.get("reason")

            if action not in {
                "auto_response",
                "review_optional",
                "review_required",
                "escalated",
            }:
                return None

            if priority not in {"low", "medium", "high", "critical"}:
                return None

            return ReviewDecision(
                action=action,
                review_required=action in {"review_required", "escalated"},
                priority=priority,
                reason=reason or "LLM-assisted review classification.",
                decision_source="llm_assisted",
            )

        except Exception:
            return None

    @staticmethod
    def _contains_any(text: str, terms: set[str]) -> bool:
        """Return True if any term appears in normalized text."""
        return any(term in text for term in terms)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for simple rule-based matching."""
        normalized = text.lower()

        replacements = {
            "harassing": "harassment",
            "harassed": "harassment",
            "discriminating": "discrimination",
            "discriminated": "discrimination",
            "retaliated": "retaliation",
            "bullied": "bullying",
            "resigning": "resign",
            "quitting": "resign",
            "terminated": "termination",
            "demoted": "demotion",
            "complaints": "complaint",
            "grievances": "grievance",
        }

        for source, target in replacements.items():
            normalized = normalized.replace(source, target)

        return normalized