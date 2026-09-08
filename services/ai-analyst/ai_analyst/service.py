"""AIAnalystService — orchestrates prompt building, the provider call,
and strict output validation (product spec section 15).

On invalid output, retries once with an explicit correction reminder
appended; if that also fails, or the provider itself is unreachable,
returns a safe fallback assessment (recommendation REVIEW, confidence 0,
is_fallback=True) rather than propagating a raw exception up to the
transaction-analysis endpoint or fabricating a plausible-looking result.
REVIEW — not ALLOW — is the fallback because in a security product,
"couldn't assess this" must never be silently equivalent to "looks fine".
"""
from __future__ import annotations

from ai_analyst.output import AIOutputError, parse_and_validate
from ai_analyst.prompt import SYSTEM_PROMPT, build_user_prompt
from ai_analyst.provider import AIProvider, AIProviderError
from ai_analyst.schemas import AIAssessment, Evidence

_RETRY_REMINDER = (
    "\n\nYour previous response could not be parsed: {error}. Respond again with "
    "ONLY the JSON object described above — no markdown code fences, no other text."
)


def _fallback(reason: str) -> AIAssessment:
    return AIAssessment(
        summary="AI analysis could not be completed.",
        risk_assessment="insufficient evidence: the AI analyst's output could not be validated",
        findings=[],
        potential_impact=[],
        recommendation="REVIEW",
        confidence=0,
        is_fallback=True,
        notes=[reason],
    )


class AIAnalystService:
    def __init__(self, provider: AIProvider):
        self._provider = provider

    async def analyze(self, evidence: Evidence) -> AIAssessment:
        user_prompt = build_user_prompt(evidence)

        try:
            raw = await self._provider.complete(system=SYSTEM_PROMPT, user=user_prompt)
        except AIProviderError as exc:
            return _fallback(f"AI provider unreachable: {exc}")

        try:
            return parse_and_validate(raw)
        except AIOutputError as first_error:
            retry_prompt = user_prompt + _RETRY_REMINDER.format(error=first_error)
            try:
                raw_retry = await self._provider.complete(system=SYSTEM_PROMPT, user=retry_prompt)
            except AIProviderError as exc:
                return _fallback(f"AI provider unreachable on retry: {exc}")

            try:
                return parse_and_validate(raw_retry)
            except AIOutputError as second_error:
                return _fallback(
                    f"AI output failed validation twice: first={first_error}; retry={second_error}"
                )
