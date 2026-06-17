"""AMLIOS-X pipeline runner.

This entry point coordinates the DevB-owned risk-scoring, explainability, and
dashboard-ready output steps while remaining compatible with DevA artifacts as
they land.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ml_models import AMLRiskClassifier


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def run_pipeline(train_model: bool = True) -> dict[str, Any]:
    """Run DevB integration steps and return a compact execution summary."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    classifier = AMLRiskClassifier()
    features = classifier.load_features()
    summary: dict[str, Any] = {
        "feature_rows": int(len(features)),
        "feature_columns": int(len(features.columns)),
        "risk_scores_path": str(PROCESSED_DIR / "risk_scores.csv"),
        "model_trained": False,
    }

    if train_model:
        try:
            metrics = classifier.train_pipeline(features)
            classifier.export_risk_scores(PROCESSED_DIR / "risk_scores.csv", features)
            classifier.export_feature_importance(PROCESSED_DIR / "feature_importance.csv", top_n=50)
            summary.update(metrics)
            summary["model_trained"] = True
        except ImportError as exc:
            summary["model_training_warning"] = str(exc)
            _export_heuristic_risk_scores(features, PROCESSED_DIR / "risk_scores.csv")
        except ValueError as exc:
            summary["model_training_warning"] = str(exc)
            _export_heuristic_risk_scores(features, PROCESSED_DIR / "risk_scores.csv")
    else:
        _export_heuristic_risk_scores(features, PROCESSED_DIR / "risk_scores.csv")

    metrics_path = PROCESSED_DIR / "model_metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _export_heuristic_risk_scores(features: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """Export dashboard-ready risk scores when training dependencies are absent."""

    scores = pd.DataFrame({"account_id": features["account_id"].astype(str)})
    label_signal = features.get("is_suspicious", pd.Series(0, index=features.index)).astype(float)

    volume_cols = [col for col in features.columns if "amount_local_npr" in col and col.endswith("_sum")]
    border_cols = [col for col in features.columns if "cross_border" in col]

    volume_signal = _rank_signal(features[volume_cols].sum(axis=1)) if volume_cols else 0.0
    border_signal = _rank_signal(features[border_cols].sum(axis=1)) if border_cols else 0.0

    scores["risk_score"] = (0.55 * label_signal + 0.30 * volume_signal + 0.15 * border_signal).clip(0, 1)
    scores["risk_percentile"] = (scores["risk_score"].rank(pct=True) * 100).round(2)
    scores["risk_band"] = pd.cut(
        scores["risk_score"],
        bins=[-np.inf, 0.25, 0.50, 0.75, 0.90, np.inf],
        labels=["LOW", "ELEVATED", "HIGH", "SEVERE", "CRITICAL"],
    ).astype(str)
    scores = scores.sort_values("risk_score", ascending=False).reset_index(drop=True)
    scores.insert(0, "rank", np.arange(1, len(scores) + 1))
    scores.to_csv(output_path, index=False)
    return scores


def _rank_signal(values: pd.Series) -> pd.Series:
    values = pd.Series(values).fillna(0)
    if values.nunique() <= 1:
        return pd.Series(0.0, index=values.index)
    return values.rank(pct=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AMLIOS-X DevB pipeline.")
    parser.add_argument(
        "--no-train-model",
        action="store_true",
        help="Skip XGBoost training and export dashboard-ready heuristic risk scores.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_pipeline(train_model=not args.no_train_model)
    print(json.dumps(result, indent=2, sort_keys=True))
