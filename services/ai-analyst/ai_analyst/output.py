"""Strict validation of the AI provider's raw text into an AIAssessment.

Never trusts the model's output at face value — every field is checked
for presence, type, and (for recommendation/confidence) value range
before being accepted. Anything that fails validation raises
AIOutputError; the caller (service.py) decides whether to retry or fall
back, but this module itself never guesses at a missing/malformed field.
"""
from __future__ import annotations

import json

from ai_analyst.schemas import VALID_RECOMMENDATIONS, AIAssessment

REQUIRED_KEYS = ("summary", "risk_assessment", "findings", "potential_impact", "recommendation", "confidence")


class AIOutputError(ValueError):
    pass


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def parse_and_validate(raw_text: str) -> AIAssessment:
    cleaned = _strip_code_fence(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIOutputError(f"model output is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise AIOutputError(f"model output must be a JSON object, got {type(data).__name__}")

    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise AIOutputError(f"model output missing required key(s): {', '.join(missing)}")

    if not isinstance(data["summary"], str) or not data["summary"].strip():
        raise AIOutputError("'summary' must be a non-empty string")
    if not isinstance(data["risk_assessment"], str) or not data["risk_assessment"].strip():
        raise AIOutputError("'risk_assessment' must be a non-empty string")

    for key in ("findings", "potential_impact"):
        value = data[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise AIOutputError(f"'{key}' must be a list of strings")

    if data["recommendation"] not in VALID_RECOMMENDATIONS:
        raise AIOutputError(
            f"'recommendation' must be one of {VALID_RECOMMENDATIONS}, got {data['recommendation']!r}"
        )

    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, int):
        raise AIOutputError(f"'confidence' must be an integer, got {type(confidence).__name__}")
    if not (0 <= confidence <= 100):
        raise AIOutputError(f"'confidence' must be between 0 and 100, got {confidence}")

    return AIAssessment(
        summary=data["summary"],
        risk_assessment=data["risk_assessment"],
        findings=list(data["findings"]),
        potential_impact=list(data["potential_impact"]),
        recommendation=data["recommendation"],
        confidence=confidence,
        is_fallback=False,
    )
