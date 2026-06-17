"""
Unit tests for src/ml_models.py

Tests:
- Transaction-level ML features aggregate into account-level training rows
- Label normalization supports the hackathon dataset's is_suspicious_tx column
- Feature selection excludes labels and account identifiers
"""

import pandas as pd

from src.ml_models import AMLRiskClassifier


class _StubModel:
    def predict_proba(self, data):
        return [[0.90, 0.10], [0.20, 0.80], [0.55, 0.45]]


def test_transaction_features_aggregate_to_account_level():
    df = pd.DataFrame(
        {
            "Sender_account": [101, 101, 202],
            "Receiver_account": [202, 303, 101],
            "amount_local_npr": [900_000.0, 1_200_000.0, 50_000.0],
            "cross_border_flag": [0, 1, 0],
            "tx_count_10": [1.0, 2.0, 1.0],
            "is_suspicious_tx": [0, 1, 0],
        }
    )

    features = AMLRiskClassifier()._aggregate_transaction_features(df)

    assert set(features["account_id"]) == {101, 202, 303}
    assert features.loc[features["account_id"] == 101, "is_suspicious"].item() == 1
    assert features.loc[features["account_id"] == 303, "is_suspicious"].item() == 1
    assert "sent_amount_local_npr_sum" in features.columns
    assert "received_amount_local_npr_sum" in features.columns


def test_feature_selection_excludes_ids_and_labels():
    df = pd.DataFrame(
        {
            "account_id": [101, 202, 303],
            "is_suspicious_tx": [0, 1, 0],
            "pagerank": [0.1, 0.8, 0.2],
            "community_id": ["A", "B", "A"],
            "constant_feature": [1, 1, 1],
        }
    )
    classifier = AMLRiskClassifier()
    normalized = classifier._normalize_target(df)

    feature_columns = classifier._select_feature_columns(normalized, "is_suspicious")

    assert "account_id" not in feature_columns
    assert "is_suspicious" not in feature_columns
    assert "is_suspicious_tx" not in feature_columns
    assert "constant_feature" not in feature_columns
    assert feature_columns == ["pagerank", "community_id"]


def test_predict_risk_scores_ranks_accounts_with_percentile_bands():
    classifier = AMLRiskClassifier()
    classifier.model_ = _StubModel()
    classifier.feature_columns_ = ["pagerank"]
    classifier.account_id_col_ = "account_id"
    classifier.label_col_ = "is_suspicious"

    scores = classifier.predict_risk_scores(
        pd.DataFrame(
            {
                "account_id": [101, 202, 303],
                "pagerank": [0.1, 0.8, 0.4],
                "is_suspicious": [0, 1, 0],
            }
        )
    )

    assert scores["account_id"].tolist() == ["202", "303", "101"]
    assert scores["risk_score"].tolist() == [0.80, 0.45, 0.10]
    assert scores.loc[0, "rank"] == 1
    assert scores.loc[0, "risk_band"] == "SEVERE"
