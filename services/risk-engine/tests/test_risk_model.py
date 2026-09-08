"""Tests for RiskModel / RiskEngineService against the real trained
artifact in ml/models/risk_model.joblib (not mocked — this actually loads
and runs the model that ml/training/train.py produced).

Run from repo root with:
  PYTHONPATH=.:services/risk-engine python3 -m unittest \
    discover -s services/risk-engine/tests -v
"""
import unittest

from ml.features.schema import RiskFeatures
from risk_engine.model import RiskModel
from risk_engine.service import RiskEngineService


class TestRiskModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel.load(model_version="test")

    def test_risk_score_in_valid_range(self):
        result = self.model.predict(RiskFeatures())
        self.assertGreaterEqual(result.risk_score, 0)
        self.assertLessEqual(result.risk_score, 100)
        self.assertIn(result.risk_level, ("LOW", "MEDIUM", "HIGH", "CRITICAL"))

    def test_unlimited_approval_scores_higher_than_limited(self):
        base = dict(
            transaction_value=0.1, wallet_age=100, contract_age=100,
            transaction_type="erc20_approval", simulation_warning_count=0,
        )
        limited = self.model.predict(
            RiskFeatures(**base, approval_ratio_to_max=0.1, is_unlimited_approval=False)
        )
        unlimited = self.model.predict(
            RiskFeatures(**base, approval_ratio_to_max=1.0, is_unlimited_approval=True)
        )
        self.assertGreater(unlimited.risk_score, limited.risk_score)

    def test_new_wallet_and_contract_scores_higher_than_established(self):
        new = self.model.predict(
            RiskFeatures(
                wallet_age=1, contract_age=1, transaction_value=0.1,
                transaction_type="contract_interaction", simulation_warning_count=1,
            )
        )
        established = self.model.predict(
            RiskFeatures(
                wallet_age=800, contract_age=800, transaction_value=0.1,
                unique_contract_count=50, unique_token_count=20, recent_activity=20,
                transaction_frequency=5, contract_interaction_frequency=0.7,
                transaction_type="contract_interaction", simulation_warning_count=0,
            )
        )
        self.assertGreater(new.risk_score, established.risk_score)

    def test_more_simulation_warnings_increase_score(self):
        base = dict(transaction_value=0.1, wallet_age=100, transaction_type="contract_interaction")
        low_warn = self.model.predict(RiskFeatures(**base, simulation_warning_count=0))
        high_warn = self.model.predict(RiskFeatures(**base, simulation_warning_count=3))
        self.assertGreater(high_warn.risk_score, low_warn.risk_score)

    def test_imputed_fields_reduce_confidence_and_are_reported(self):
        sparse = self.model.predict(RiskFeatures(transaction_value=0.1))
        rich = self.model.predict(
            RiskFeatures(
                transaction_value=0.1, wallet_age=100, transaction_frequency=2,
                value_deviation=0.1, contract_age=100, unique_contract_count=10,
                unique_token_count=5, recent_activity=10, contract_interaction_frequency=0.5,
            )
        )
        self.assertLess(sparse.model_confidence, rich.model_confidence)
        self.assertTrue(any("imputed" in n for n in sparse.notes))
        self.assertEqual(rich.notes, [])

    def test_signals_are_sorted_by_magnitude_and_nonzero(self):
        result = self.model.predict(
            RiskFeatures(
                transaction_value=5, approval_ratio_to_max=1.0, is_unlimited_approval=True,
                contract_age=2, wallet_age=1, transaction_type="erc20_approval",
                simulation_warning_count=3,
            )
        )
        impacts = [abs(s.impact) for s in result.signals]
        self.assertEqual(impacts, sorted(impacts, reverse=True))
        self.assertTrue(all(i != 0 for i in impacts))

    def test_reports_demo_data_flag(self):
        result = self.model.predict(RiskFeatures())
        self.assertTrue(result.model_is_demo_data)

    def test_rejects_model_with_mismatched_feature_schema(self):
        with self.assertRaises(ValueError):
            RiskModel(model=None, scaler=None, feature_names=["wrong", "schema"])


class TestRiskEngineService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = RiskEngineService(RiskModel.load(model_version="test"))

    def test_assess_from_pipeline_wires_fields_through(self):
        result = self.service.assess_from_pipeline(
            transaction_type="erc20_approval",
            transaction_value_native=0.0,
            simulation_warning_count=1,
            approval_ratio_to_max=1.0,
            is_unlimited_approval=True,
        )
        self.assertIn(result.risk_level, ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
        # unsupplied wallet/contract stats should show up as imputed, not silently zero
        self.assertTrue(any("imputed" in n for n in result.notes))


if __name__ == "__main__":
    unittest.main()
