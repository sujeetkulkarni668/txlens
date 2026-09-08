"""Unit tests for AIAnalystService — retry-then-fallback orchestration,
using a hand-written FakeAIProvider (no network, no SDK needed)."""
import json
import unittest

from ai_analyst.provider import AIProvider, AIProviderError
from ai_analyst.schemas import Evidence
from ai_analyst.service import AIAnalystService

VALID_RESPONSE = json.dumps(
    {
        "summary": "Native ETH transfer to a known address.",
        "risk_assessment": "Low risk.",
        "findings": [],
        "potential_impact": ["Recipient receives the transferred ETH."],
        "recommendation": "ALLOW",
        "confidence": 90,
    }
)


def make_evidence() -> Evidence:
    return Evidence(transaction={"value": "0"}, parsed={"tx_type": "native_transfer"})


class ScriptedProvider(AIProvider):
    """Returns a pre-scripted sequence of responses/exceptions, one per call."""

    def __init__(self, script: list):
        self._script = list(script)
        self.call_count = 0
        self.calls: list[str] = []

    async def complete(self, *, system: str, user: str) -> str:
        self.call_count += 1
        self.calls.append(user)
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TestAIAnalystServiceHappyPath(unittest.IsolatedAsyncioTestCase):
    async def test_valid_first_response_used_directly_no_retry(self):
        provider = ScriptedProvider([VALID_RESPONSE])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertEqual(provider.call_count, 1)
        self.assertFalse(result.is_fallback)
        self.assertEqual(result.recommendation, "ALLOW")
        self.assertEqual(result.confidence, 90)


class TestAIAnalystServiceRetry(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_then_valid_response_recovers_via_retry(self):
        provider = ScriptedProvider(["not valid json {{{", VALID_RESPONSE])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertEqual(provider.call_count, 2)
        self.assertFalse(result.is_fallback)
        self.assertEqual(result.recommendation, "ALLOW")
        # the retry prompt should include a correction reminder referencing the error
        self.assertIn("could not be parsed", provider.calls[1])

    async def test_invalid_twice_falls_back_safely(self):
        provider = ScriptedProvider(["not json", "still not json"])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertEqual(provider.call_count, 2)
        self.assertTrue(result.is_fallback)
        self.assertEqual(result.recommendation, "REVIEW")  # never ALLOW on failure
        self.assertEqual(result.confidence, 0)


class TestAIAnalystServiceProviderFailure(unittest.IsolatedAsyncioTestCase):
    async def test_provider_unreachable_on_first_call_falls_back(self):
        provider = ScriptedProvider([AIProviderError("connection refused")])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertTrue(result.is_fallback)
        self.assertEqual(result.recommendation, "REVIEW")
        self.assertTrue(any("unreachable" in n for n in result.notes))

    async def test_provider_unreachable_on_retry_falls_back(self):
        provider = ScriptedProvider(["bad json", AIProviderError("timeout")])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertTrue(result.is_fallback)
        self.assertTrue(any("retry" in n for n in result.notes))

    async def test_fallback_is_never_allow_or_block(self):
        """A security product must never silently 'pass' a transaction it
        couldn't actually assess."""
        provider = ScriptedProvider([AIProviderError("down"), AIProviderError("still down")])
        service = AIAnalystService(provider)
        result = await service.analyze(make_evidence())
        self.assertEqual(result.recommendation, "REVIEW")


if __name__ == "__main__":
    unittest.main()
