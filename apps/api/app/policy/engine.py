"""Deterministic policy engine (product spec section 18).

Every rule either produces a decision (ALLOW is implicit — a rule that
doesn't match simply contributes nothing) or is explicitly marked
"could not be evaluated" when the context lacks the data the rule needs
(e.g. block_unknown_contracts with no contract intelligence available).
An unevaluatable rule is never silently treated as passing — it's
surfaced separately so the caller (and eventually the AI analyst) knows
policy coverage was incomplete, not clean.

Multiple matched rules combine by taking the most severe outcome:
BLOCK > REVIEW > ALLOW.
"""
from __future__ import annotations

from app.policy.schemas import (
    _SEVERITY,
    PolicyDecision,
    PolicyEvaluationContext,
    PolicyEvaluationResult,
    PolicyRule,
    RuleOutcome,
    RuleType,
)


class PolicyEngine:
    def evaluate(
        self, policies: list[PolicyRule], context: PolicyEvaluationContext
    ) -> PolicyEvaluationResult:
        matched: list[RuleOutcome] = []
        unevaluated: list[RuleOutcome] = []

        for policy in policies:
            if not policy.is_active:
                continue
            outcome = self._evaluate_one(policy, context)
            if outcome.decision is None:
                unevaluated.append(outcome)
            elif outcome.decision != PolicyDecision.ALLOW:
                matched.append(outcome)

        overall = PolicyDecision.ALLOW
        for outcome in matched:
            if _SEVERITY[outcome.decision] > _SEVERITY[overall]:
                overall = outcome.decision

        return PolicyEvaluationResult(
            decision=overall, matched_rules=matched, unevaluated_rules=unevaluated
        )

    def _evaluate_one(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        try:
            handler = self._HANDLERS[policy.rule_type]
        except KeyError:
            return RuleOutcome(
                rule_name=policy.name,
                rule_type=policy.rule_type,
                decision=None,
                reason=f"unknown rule_type '{policy.rule_type}'",
            )
        return handler(self, policy, ctx)

    def _require_param(self, policy: PolicyRule, key: str) -> float | None:
        value = policy.parameters.get(key)
        if value is None:
            return None
        try:
            val = float(value)
            return val if val >= 0 else None
        except (TypeError, ValueError):
            return None

    def _maximum_transaction_value(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        max_value = self._require_param(policy, "max_value")
        if max_value is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "misconfigured: missing/invalid 'max_value' parameter",
            )
        if ctx.transaction_value_native > max_value:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.BLOCK,
                f"transaction value {ctx.transaction_value_native} exceeds maximum {max_value}",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "within limit")

    def _maximum_daily_spend(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        max_spend = self._require_param(policy, "max_daily_spend")
        if max_spend is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "misconfigured: missing/invalid 'max_daily_spend' parameter",
            )
        if ctx.daily_spend_so_far_native is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "daily spend history not available — cannot evaluate",
            )
        projected = ctx.daily_spend_so_far_native + ctx.transaction_value_native
        if projected > max_spend:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.BLOCK,
                f"projected daily spend {projected} exceeds maximum {max_spend}",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "within daily limit")

    def _require_review_above(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        threshold = self._require_param(policy, "threshold")
        if threshold is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "misconfigured: missing/invalid 'threshold' parameter",
            )
        if ctx.transaction_value_native > threshold:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.REVIEW,
                f"transaction value {ctx.transaction_value_native} exceeds review threshold {threshold}",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "below review threshold")

    def _block_unlimited_approvals(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        if ctx.is_unlimited_approval:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.BLOCK,
                "transaction requests an unlimited token approval",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "not an unlimited approval")

    def _block_unknown_contracts(self, policy: PolicyRule, ctx: PolicyEvaluationContext) -> RuleOutcome:
        if ctx.contract_known is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "contract verification status not available — cannot evaluate",
            )
        if ctx.contract_known is False:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.BLOCK,
                "counterparty contract is unverified/unknown",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "contract is known/verified")

    def _require_review_for_new_contracts(
        self, policy: PolicyRule, ctx: PolicyEvaluationContext
    ) -> RuleOutcome:
        max_age = self._require_param(policy, "max_age_days")
        if max_age is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "misconfigured: missing/invalid 'max_age_days' parameter",
            )
        if ctx.contract_age_days is None:
            return RuleOutcome(
                policy.name, policy.rule_type, None,
                "contract age not available — cannot evaluate",
            )
        if ctx.contract_age_days < max_age:
            return RuleOutcome(
                policy.name, policy.rule_type, PolicyDecision.REVIEW,
                f"contract age {ctx.contract_age_days}d is under the {max_age}d review threshold",
            )
        return RuleOutcome(policy.name, policy.rule_type, PolicyDecision.ALLOW, "contract is established")

    _HANDLERS = {
        RuleType.MAXIMUM_TRANSACTION_VALUE: _maximum_transaction_value,
        RuleType.MAXIMUM_DAILY_SPEND: _maximum_daily_spend,
        RuleType.REQUIRE_REVIEW_ABOVE: _require_review_above,
        RuleType.BLOCK_UNLIMITED_APPROVALS: _block_unlimited_approvals,
        RuleType.BLOCK_UNKNOWN_CONTRACTS: _block_unknown_contracts,
        RuleType.REQUIRE_REVIEW_FOR_NEW_CONTRACTS: _require_review_for_new_contracts,
    }
