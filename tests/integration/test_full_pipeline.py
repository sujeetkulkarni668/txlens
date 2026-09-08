"""End-to-end pipeline integration tests (product spec section 27):
Parser -> Simulation -> ML risk -> Policy -> AI, composed exactly the way
apps/api/app/api/v1/endpoints/transactions.py wires them, but without the
HTTP/DB layer around them (those remain syntax-checked only — see
README limitations). This is a genuine integration test: it proves the
seams between independently-tested components actually compose correctly,
using a FakeBlockchainProvider and FakeAIProvider so it runs with zero
network access and zero installed dependencies beyond scikit-learn/numpy
(already present for the real trained risk model).

Run from the repo root with:
  PYTHONPATH=apps/api:services/risk-engine:services/ai-analyst:. \
    python3 -m unittest discover -s tests/integration -v
"""
from __future__ import annotations

import unittest

from app.blockchain.exceptions import UnsupportedCapabilityError
from app.blockchain.provider import BlockchainProvider
from app.blockchain.schemas import CallResult, TraceCall, TraceCallResult
from app.parser.parser import TransactionParser
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyEvaluationContext, PolicyRule, RuleType
from app.simulation.service import SimulationService
from ml.features.schema import RiskFeatures
from risk_engine.model import RiskModel
from ai_analyst.provider import AIProvider
from ai_analyst.schemas import Evidence
from ai_analyst.service import AIAnalystService

MAX_UINT256 = 2**256 - 1
WEI_PER_ETHER = 10**18

ATTACKER_CONTRACT = "0x9999999999999999999999999999999999999999"
SPENDER = "0x2222222222222222222222222222222222222222"
FROM_ADDR = "0x1111111111111111111111111111111111111111"
RECIPIENT = "0x3333333333333333333333333333333333333333"


def word_address(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def word_uint(n: int) -> str:
    return format(n, "064x")


class FakeProvider(BlockchainProvider):
    """Minimal configurable stand-in for the real JSON-RPC provider —
    same pattern used in unit tests, reused here to drive the full
    pipeline rather than SimulationService alone."""

    def __init__(self, *, call_success=True, call_error=None, gas=45000, trace_result=None, trace_exc=None):
        self._call_success = call_success
        self._call_error = call_error
        self._gas = gas
        self._trace_result = trace_result
        self._trace_exc = trace_exc

    async def get_balance(self, address, block="latest"): raise NotImplementedError
    async def get_transaction(self, tx_hash): raise NotImplementedError
    async def get_transaction_receipt(self, tx_hash): raise NotImplementedError
    async def get_transaction_count(self, address, block="latest"): raise NotImplementedError
    async def get_code(self, address, block="latest"): raise NotImplementedError
    async def get_logs(self, **kwargs): raise NotImplementedError
    async def get_block(self, block="latest"): raise NotImplementedError

    async def call(self, *, to, data, block="latest"):
        return CallResult(success=self._call_success, return_data="0x", error=self._call_error)

    async def estimate_gas(self, **kwargs):
        return self._gas

    async def trace_call(self, **kwargs):
        if self._trace_exc:
            raise self._trace_exc
        return self._trace_result


class ScriptedAIProvider(AIProvider):
    def __init__(self, response: str):
        self._response = response
        self.call_count = 0

    async def complete(self, *, system: str, user: str) -> str:
        self.call_count += 1
        return self._response


def build_pipeline(*, provider: BlockchainProvider, ai_provider: AIProvider):
    return {
        "parser": TransactionParser(),
        "simulation": SimulationService(provider),
        "risk": RiskModel.load(model_version="integration-test"),
        "policy": PolicyEngine(),
        "ai": AIAnalystService(ai_provider),
    }


class TestFullPipelineBoringTransaction(unittest.IsolatedAsyncioTestCase):
    """A plain, low-value native transfer with no policies configured —
    every stage should agree this is unremarkable."""

    async def test_end_to_end_low_risk_allow(self):
        provider = FakeProvider(call_success=True, trace_exc=UnsupportedCapabilityError("no debug ns"))
        ai_provider = ScriptedAIProvider(
            '{"summary": "Simple ETH transfer.", "risk_assessment": "Low risk.", '
            '"findings": [], "potential_impact": ["Recipient receives the ETH."], '
            '"recommendation": "ALLOW", "confidence": 92}'
        )
        pipeline = build_pipeline(provider=provider, ai_provider=ai_provider)

        parsed = pipeline["parser"].parse(to=RECIPIENT, value=str(10**16), data=None)
        simulation = await pipeline["simulation"].simulate(
            chain="base-sepolia", from_address=FROM_ADDR, to=RECIPIENT, value=str(10**16), data=None
        )
        risk = pipeline["risk"].predict(
            RiskFeatures(
                transaction_value=10**16 / WEI_PER_ETHER,
                transaction_type=parsed.tx_type.value,
                simulation_warning_count=len(simulation.warnings),
                wallet_age=400, contract_age=None,
            )
        )
        policy_result = pipeline["policy"].evaluate(
            [], PolicyEvaluationContext(transaction_value_native=10**16 / WEI_PER_ETHER)
        )
        ai_result = await pipeline["ai"].analyze(
            Evidence(
                transaction={"value": str(10**16)},
                parsed=parsed.__dict__,
                simulation=simulation.__dict__,
                risk=risk.__dict__,
                policy=policy_result.__dict__,
            )
        )

        self.assertEqual(parsed.tx_type.value, "native_transfer")
        self.assertTrue(simulation.success)
        self.assertIn(risk.risk_level, ("LOW", "MEDIUM"))  # no red flags present
        self.assertEqual(policy_result.decision.value, "ALLOW")  # no policies configured
        self.assertFalse(ai_result.is_fallback)
        self.assertEqual(ai_result.recommendation, "ALLOW")


class TestFullPipelineRiskyTransaction(unittest.IsolatedAsyncioTestCase):
    """Unlimited approval to a brand-new, unknown contract, with
    simulation warnings and a matching policy — every stage should
    escalate, and the escalations should be internally consistent."""

    async def test_end_to_end_high_risk_blocked(self):
        # Simulate a trace that surfaces the approval as an on-chain effect.
        approval_log = {
            "address": ATTACKER_CONTRACT,
            "topics": [
                "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
                "0x" + word_address(FROM_ADDR),
                "0x" + word_address(SPENDER),
            ],
            "data": "0x" + word_uint(MAX_UINT256),
        }
        root_call = TraceCall(
            call_type="CALL", from_address=FROM_ADDR, to_address=ATTACKER_CONTRACT, value="0",
            input_data="0x095ea7b3", logs=[approval_log],
        )
        provider = FakeProvider(
            call_success=True, trace_result=TraceCallResult(success=True, root_call=root_call)
        )
        ai_provider = ScriptedAIProvider(
            '{"summary": "Unlimited approval to an unverified, brand-new contract.", '
            '"risk_assessment": "High risk: unlimited allowance with no established history.", '
            '"findings": ["Unlimited token approval", "Contract has no established history"], '
            '"potential_impact": ["Spender could drain the full token balance at any time."], '
            '"recommendation": "BLOCK", "confidence": 88}'
        )
        pipeline = build_pipeline(provider=provider, ai_provider=ai_provider)

        calldata = "0x095ea7b3" + word_address(SPENDER) + word_uint(MAX_UINT256)
        parsed = pipeline["parser"].parse(to=ATTACKER_CONTRACT, value="0", data=calldata)
        simulation = await pipeline["simulation"].simulate(
            chain="base-sepolia", from_address=FROM_ADDR, to=ATTACKER_CONTRACT, value="0", data=calldata
        )
        risk = pipeline["risk"].predict(
            RiskFeatures(
                transaction_value=0.0,
                transaction_type=parsed.tx_type.value,
                approval_ratio_to_max=1.0,
                is_unlimited_approval=parsed.is_unlimited_approval,
                simulation_warning_count=len(simulation.warnings),
                wallet_age=2, contract_age=1,
            )
        )
        policies = [
            PolicyRule(
                name="no-unlimited-approvals",
                rule_type=RuleType.BLOCK_UNLIMITED_APPROVALS,
                parameters={},
            )
        ]
        policy_result = pipeline["policy"].evaluate(
            policies,
            PolicyEvaluationContext(
                transaction_value_native=0.0, is_unlimited_approval=parsed.is_unlimited_approval
            ),
        )
        ai_result = await pipeline["ai"].analyze(
            Evidence(
                transaction={"to": ATTACKER_CONTRACT, "value": "0"},
                parsed=parsed.__dict__,
                simulation=simulation.__dict__,
                risk=risk.__dict__,
                policy=policy_result.__dict__,
            )
        )

        # Every stage should independently recognize this as dangerous —
        # that agreement, not any single stage, is what this test proves.
        self.assertEqual(parsed.tx_type.value, "erc20_approval")
        self.assertTrue(parsed.is_unlimited_approval)
        self.assertTrue(simulation.trace_supported)
        self.assertEqual(len(simulation.approvals), 1)
        self.assertIn(risk.risk_level, ("HIGH", "CRITICAL"))
        self.assertEqual(policy_result.decision.value, "BLOCK")
        self.assertEqual(ai_result.recommendation, "BLOCK")
        self.assertFalse(ai_result.is_fallback)


class TestFullPipelineDegradedConditions(unittest.IsolatedAsyncioTestCase):
    """Worst case for the surrounding infrastructure: no trace support AND
    the AI provider producing unparseable output twice. The pipeline must
    still complete without raising, and must never quietly present that
    failure as a clean ALLOW."""

    async def test_end_to_end_survives_infra_failures_without_raising(self):
        provider = FakeProvider(
            call_success=True, trace_exc=UnsupportedCapabilityError("debug namespace disabled")
        )
        ai_provider = ScriptedAIProvider("this is not json at all")
        pipeline = build_pipeline(provider=provider, ai_provider=ai_provider)

        calldata = "0x095ea7b3" + word_address(SPENDER) + word_uint(MAX_UINT256)
        parsed = pipeline["parser"].parse(to=ATTACKER_CONTRACT, value="0", data=calldata)
        simulation = await pipeline["simulation"].simulate(
            chain="base-sepolia", from_address=FROM_ADDR, to=ATTACKER_CONTRACT, value="0", data=calldata
        )
        risk = pipeline["risk"].predict(
            RiskFeatures(
                transaction_value=0.0, transaction_type=parsed.tx_type.value,
                approval_ratio_to_max=1.0, is_unlimited_approval=True,
                simulation_warning_count=len(simulation.warnings),
            )
        )
        policy_result = pipeline["policy"].evaluate(
            [], PolicyEvaluationContext(transaction_value_native=0.0, is_unlimited_approval=True)
        )
        # No exception should escape this call despite the AI provider
        # never returning valid output.
        ai_result = await pipeline["ai"].analyze(
            Evidence(
                transaction={"to": ATTACKER_CONTRACT, "value": "0"},
                parsed=parsed.__dict__, simulation=simulation.__dict__,
                risk=risk.__dict__, policy=policy_result.__dict__,
            )
        )

        self.assertFalse(simulation.trace_supported)
        self.assertTrue(any("calldata_decode" in a.get("source", "") for a in simulation.approvals))
        self.assertTrue(ai_result.is_fallback)
        # A degraded AI stage must never look like a clean pass.
        self.assertEqual(ai_result.recommendation, "REVIEW")
        self.assertEqual(ai_provider.call_count, 2)  # confirms the retry actually happened


if __name__ == "__main__":
    unittest.main()
