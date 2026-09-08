"""Unit tests for output.py — strict validation of raw model text."""
import json
import unittest

from ai_analyst.output import AIOutputError, parse_and_validate

VALID = {
    "summary": "Approves a token spend to a known DEX router.",
    "risk_assessment": "Low risk, standard approval pattern.",
    "findings": ["Approval amount matches the swap amount."],
    "potential_impact": ["Router could spend up to the approved amount."],
    "recommendation": "ALLOW",
    "confidence": 85,
}


class TestParseAndValidate(unittest.TestCase):
    def test_accepts_valid_json(self):
        result = parse_and_validate(json.dumps(VALID))
        self.assertEqual(result.recommendation, "ALLOW")
        self.assertEqual(result.confidence, 85)
        self.assertFalse(result.is_fallback)

    def test_strips_markdown_code_fence(self):
        fenced = "```json\n" + json.dumps(VALID) + "\n```"
        result = parse_and_validate(fenced)
        self.assertEqual(result.recommendation, "ALLOW")

    def test_rejects_invalid_json(self):
        with self.assertRaises(AIOutputError):
            parse_and_validate("not json at all {{{")

    def test_rejects_non_object_json(self):
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(["a", "list", "not", "an", "object"]))

    def test_rejects_missing_required_key(self):
        data = dict(VALID)
        del data["recommendation"]
        with self.assertRaises(AIOutputError) as ctx:
            parse_and_validate(json.dumps(data))
        self.assertIn("recommendation", str(ctx.exception))

    def test_rejects_invalid_recommendation_value(self):
        data = dict(VALID, recommendation="MAYBE")
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_confidence_out_of_range(self):
        data = dict(VALID, confidence=150)
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_confidence_below_zero(self):
        data = dict(VALID, confidence=-1)
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_non_integer_confidence(self):
        data = dict(VALID, confidence="high")
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_boolean_confidence(self):
        # bool is a subclass of int in Python — must be explicitly rejected.
        data = dict(VALID, confidence=True)
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_findings_not_a_list_of_strings(self):
        data = dict(VALID, findings=["ok", 42])
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))

    def test_rejects_empty_summary(self):
        data = dict(VALID, summary="   ")
        with self.assertRaises(AIOutputError):
            parse_and_validate(json.dumps(data))


if __name__ == "__main__":
    unittest.main()
