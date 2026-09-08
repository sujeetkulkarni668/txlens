"""Unit tests for PolicyEngine (product spec section 18).

Pure stdlib unittest — no external dependencies required to run these.
"""
import unittest

from app.policy.engine import PolicyEngine
from app.policy.schemas import (
    PolicyDecision,
    PolicyEvaluationContext,
    PolicyRule,
    RuleType,
)


def ctx(**kwargs) -> PolicyEvaluationContext:
    kwargs.setdefault("transaction_value_native", 0.0)
    return PolicyEvaluationContext(**kwargs)


class TestNoPolicies(unittest.TestCase):
    def test_no_policies_means_allow(self):
        result = PolicyEngine().evaluate([], ctx(transaction_value_native=1000))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.matched_rules, [])


class TestMaximumTransactionValue(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()
        self.policy = PolicyRule(
            name="cap", rule_type=RuleType.MAXIMUM_TRANSACTION_VALUE, parameters={"max_value": 1.0}
        )

    def test_blocks_when_over_limit(self):
        result = self.engine.evaluate([self.policy], ctx(transaction_value_native=1.5))
        self.assertEqual(result.decision, PolicyDecision.BLOCK)
        self.assertEqual(result.matched_rules[0].rule_name, "cap")

    def test_allows_when_under_limit(self):
        result = self.engine.evaluate([self.policy], ctx(transaction_value_native=0.5))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.matched_rules, [])

    def test_boundary_exactly_at_limit_is_allowed(self):
        result = self.engine.evaluate([self.policy], ctx(transaction_value_native=1.0))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_missing_parameter_is_unevaluated_not_crashed(self):
        bad_policy = PolicyRule(name="broken", rule_type=RuleType.MAXIMUM_TRANSACTION_VALUE, parameters={})
        result = self.engine.evaluate([bad_policy], ctx(transaction_value_native=1000))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(len(result.unevaluated_rules), 1)
        self.assertIn("misconfigured", result.unevaluated_rules[0].reason)

    def test_inactive_policy_is_skipped_entirely(self):
        inactive = PolicyRule(
            name="cap", rule_type=RuleType.MAXIMUM_TRANSACTION_VALUE,
            parameters={"max_value": 1.0}, is_active=False,
        )
        result = self.engine.evaluate([inactive], ctx(transaction_value_native=1000))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.matched_rules, [])
        self.assertEqual(result.unevaluated_rules, [])


class TestMaximumDailySpend(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()
        self.policy = PolicyRule(
            name="daily-cap", rule_type=RuleType.MAXIMUM_DAILY_SPEND,
            parameters={"max_daily_spend": 5.0},
        )

    def test_blocks_when_projected_spend_exceeds_cap(self):
        result = self.engine.evaluate(
            [self.policy], ctx(transaction_value_native=2.0, daily_spend_so_far_native=4.0)
        )
        self.assertEqual(result.decision, PolicyDecision.BLOCK)

    def test_allows_when_within_cap(self):
        result = self.engine.evaluate(
            [self.policy], ctx(transaction_value_native=1.0, daily_spend_so_far_native=1.0)
        )
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_unevaluated_when_spend_history_unavailable(self):
        result = self.engine.evaluate(
            [self.policy], ctx(transaction_value_native=1.0, daily_spend_so_far_native=None)
        )
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(len(result.unevaluated_rules), 1)
        self.assertIn("not available", result.unevaluated_rules[0].reason)


class TestRequireReviewAbove(unittest.TestCase):
    def test_review_when_over_threshold(self):
        policy = PolicyRule(
            name="review", rule_type=RuleType.REQUIRE_REVIEW_ABOVE, parameters={"threshold": 1.0}
        )
        result = PolicyEngine().evaluate([policy], ctx(transaction_value_native=2.0))
        self.assertEqual(result.decision, PolicyDecision.REVIEW)


class TestBlockUnlimitedApprovals(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()
        self.policy = PolicyRule(
            name="no-unlimited", rule_type=RuleType.BLOCK_UNLIMITED_APPROVALS, parameters={}
        )

    def test_blocks_unlimited_approval(self):
        result = self.engine.evaluate([self.policy], ctx(is_unlimited_approval=True))
        self.assertEqual(result.decision, PolicyDecision.BLOCK)

    def test_allows_limited_approval(self):
        result = self.engine.evaluate([self.policy], ctx(is_unlimited_approval=False))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)


class TestBlockUnknownContracts(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()
        self.policy = PolicyRule(
            name="known-only", rule_type=RuleType.BLOCK_UNKNOWN_CONTRACTS, parameters={}
        )

    def test_blocks_when_contract_known_false(self):
        result = self.engine.evaluate([self.policy], ctx(contract_known=False))
        self.assertEqual(result.decision, PolicyDecision.BLOCK)

    def test_allows_when_contract_known_true(self):
        result = self.engine.evaluate([self.policy], ctx(contract_known=True))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_unevaluated_when_unknown_status(self):
        result = self.engine.evaluate([self.policy], ctx(contract_known=None))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(len(result.unevaluated_rules), 1)


class TestRequireReviewForNewContracts(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()
        self.policy = PolicyRule(
            name="new-contract-review", rule_type=RuleType.REQUIRE_REVIEW_FOR_NEW_CONTRACTS,
            parameters={"max_age_days": 30},
        )

    def test_review_for_new_contract(self):
        result = self.engine.evaluate([self.policy], ctx(contract_age_days=5))
        self.assertEqual(result.decision, PolicyDecision.REVIEW)

    def test_allow_for_established_contract(self):
        result = self.engine.evaluate([self.policy], ctx(contract_age_days=400))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_unevaluated_when_age_unknown(self):
        result = self.engine.evaluate([self.policy], ctx(contract_age_days=None))
        self.assertEqual(len(result.unevaluated_rules), 1)


class TestSeverityCombination(unittest.TestCase):
    def test_block_wins_over_review(self):
        policies = [
            PolicyRule(name="review", rule_type=RuleType.REQUIRE_REVIEW_ABOVE, parameters={"threshold": 0.1}),
            PolicyRule(name="block", rule_type=RuleType.MAXIMUM_TRANSACTION_VALUE, parameters={"max_value": 0.1}),
        ]
        result = PolicyEngine().evaluate(policies, ctx(transaction_value_native=5.0))
        self.assertEqual(result.decision, PolicyDecision.BLOCK)
        self.assertEqual(len(result.matched_rules), 2)

    def test_unknown_rule_type_is_unevaluated(self):
        # Simulates a policy row with a rule_type no handler recognizes
        # (e.g. added to the DB by a newer version of the app).
        policy = PolicyRule(name="mystery", rule_type="some_future_rule", parameters={})
        result = PolicyEngine().evaluate([policy], ctx(transaction_value_native=1.0))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(len(result.unevaluated_rules), 1)
        self.assertIn("unknown rule_type", result.unevaluated_rules[0].reason)


if __name__ == "__main__":
    unittest.main()
