"""
Unit tests for src/explainability.py

Tests:
- Risk driver grouping is stable for dashboard decomposition
- Counterfactual edge analysis ranks incident flow by estimated impact
"""

import pandas as pd

from src.explainability import ExplainabilityEngine


class _FakeGraph:
    def __contains__(self, node):
        return str(node) == "101"

    def out_edges(self, account_id, keys=True, data=True):
        return [("101", "202", 0, {"amount_local_npr": 1_000_000})]

    def in_edges(self, account_id, keys=True, data=True):
        return [("303", "101", 0, {"amount_local_npr": 250_000})]


def test_decompose_risk_drivers_returns_normalized_groups():
    explanations = pd.DataFrame(
        {
            "account_id": ["101", "101", "101", "101"],
            "feature": ["sent_amount_sum", "received_amount_sum", "community_risk", "pep_flag"],
            "abs_shap_value": [4.0, 3.0, 2.0, 1.0],
            "driver_group": ["self_behavior", "counterparty", "community", "external"],
        }
    )

    result = ExplainabilityEngine().decompose_risk_drivers("101", explanations)

    assert result["self_behavior"] == 0.4
    assert result["counterparty"] == 0.3
    assert result["community"] == 0.2
    assert result["external"] == 0.1


def test_counterfactual_edge_analysis_orders_highest_flow_first():
    result = ExplainabilityEngine().counterfactual_edge_analysis("101", _FakeGraph())

    assert result.loc[0, "target"] == "202"
    assert result.loc[0, "risk_drop_estimate"] > result.loc[1, "risk_drop_estimate"]
