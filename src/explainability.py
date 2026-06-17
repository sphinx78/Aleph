"""
AMLIOS-X Explainability Module

Handles:
- SHAP TreeExplainer attributions for XGBoost risk model
- Multi-level SHAP decomposition (self, counterparty, community, external)
- Counterfactual edge perturbation analysis
- Evidence subgraph extraction (2-hop ego networks)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


@dataclass
class ExplainabilityEngine:
    """Explain AML risk scores with SHAP-style attribution and graph evidence.

    The engine is intentionally model-adapter friendly. It supports the
    sklearn Pipeline produced by ``AMLRiskClassifier`` and can still produce
    dashboard-ready decomposition tables from precomputed SHAP exports.
    """

    model: Any | None = None
    feature_columns: list[str] | None = None
    account_id_col: str = "account_id"
    shap_values_: np.ndarray | None = field(default=None, init=False, repr=False)
    shap_feature_names_: list[str] = field(default_factory=list, init=False)
    explanations_: pd.DataFrame | None = field(default=None, init=False, repr=False)

    DRIVER_GROUPS = {
        "self_behavior": (
            "sent_",
            "sender_",
            "tx_count",
            "velocity",
            "amount",
            "threshold",
            "tps",
            "dfa",
            "hawkes",
        ),
        "counterparty": ("received_", "receiver_", "counterparty", "neighbor", "degree"),
        "community": ("community", "leiden", "cluster", "structural_hole", "constraint"),
        "external": ("cross_border", "country_risk", "currency", "sanctions", "pep"),
    }

    def compute_shap_attributions(
        self,
        model: Any | None,
        features_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute per-account SHAP attributions for an XGBoost risk model."""

        self.model = model or self.model
        if self.model is None:
            raise RuntimeError("A trained model or pipeline is required for SHAP attribution.")

        feature_columns = self._resolve_feature_columns(features_df)
        X = features_df[feature_columns].copy()

        transformed_X, feature_names, estimator = self._prepare_model_inputs(X)

        try:
            import shap
        except ImportError as exc:
            raise ImportError(
                "Missing explainability dependency: shap. Install it with `pip install -r requirements.txt`."
            ) from exc

        explainer = shap.TreeExplainer(estimator)
        shap_values = explainer.shap_values(transformed_X)
        if isinstance(shap_values, list):
            shap_values = shap_values[-1]

        shap_values = np.asarray(shap_values)
        self.shap_values_ = shap_values
        self.shap_feature_names_ = feature_names

        account_ids = self._account_ids(features_df)
        long_rows = []
        for row_idx, account_id in enumerate(account_ids):
            values = shap_values[row_idx]
            for feature, value in zip(feature_names, values):
                long_rows.append(
                    {
                        "account_id": account_id,
                        "feature": feature,
                        "shap_value": float(value),
                        "abs_shap_value": float(abs(value)),
                        "driver_group": self._driver_group(feature),
                    }
                )

        self.explanations_ = pd.DataFrame(long_rows).sort_values(
            ["account_id", "abs_shap_value"],
            ascending=[True, False],
            kind="mergesort",
        )
        return self.explanations_.reset_index(drop=True)

    def decompose_risk_drivers(
        self,
        account_id: str | int,
        explanations_df: pd.DataFrame | None = None,
    ) -> dict[str, float]:
        """Aggregate feature attributions into analyst-friendly risk groups."""

        explanations = explanations_df if explanations_df is not None else self.explanations_
        if explanations is None or explanations.empty:
            return {group: 0.0 for group in self.DRIVER_GROUPS}

        account_rows = explanations[explanations["account_id"].astype(str) == str(account_id)]
        if account_rows.empty:
            return {group: 0.0 for group in self.DRIVER_GROUPS}

        grouped = account_rows.groupby("driver_group")["abs_shap_value"].sum()
        total = float(grouped.sum()) or 1.0
        return {
            group: float(grouped.get(group, 0.0) / total)
            for group in ("self_behavior", "counterparty", "community", "external")
        }

    def counterfactual_edge_analysis(
        self,
        account_id: str | int,
        graph_engine: Any,
        max_edges: int = 25,
    ) -> pd.DataFrame:
        """Estimate risk drop from removing incident edges around an account.

        Full graph-feature recomputation belongs to the graph pipeline, so this
        method computes a transparent perturbation proxy from incident edge
        volume. It is deterministic and dashboard-ready until DevA's graph
        feature recomputation hooks are available.
        """

        graph = self._extract_graph(graph_engine)
        if graph is None or account_id not in graph:
            return pd.DataFrame(
                columns=[
                    "account_id",
                    "source",
                    "target",
                    "edge_key",
                    "amount",
                    "direction",
                    "risk_drop_estimate",
                ]
            )

        edges = []
        for source, target, key, data in self._incident_edges(graph, account_id):
            amount = self._edge_amount(data)
            direction = "outbound" if str(source) == str(account_id) else "inbound"
            edges.append(
                {
                    "account_id": str(account_id),
                    "source": str(source),
                    "target": str(target),
                    "edge_key": str(key),
                    "amount": float(amount),
                    "direction": direction,
                }
            )

        if not edges:
            return pd.DataFrame(edges)

        result = pd.DataFrame(edges)
        total_amount = float(result["amount"].sum()) or 1.0
        result["risk_drop_estimate"] = (result["amount"] / total_amount * 0.60).round(6)
        return result.sort_values("risk_drop_estimate", ascending=False).head(max_edges).reset_index(drop=True)

    def extract_evidence_subgraph(
        self,
        account_id: str | int,
        graph_engine: Any,
        hops: int = 2,
    ) -> Any:
        """Return a NetworkX ego subgraph around a high-risk account."""

        graph = self._extract_graph(graph_engine)
        if graph is None or account_id not in graph:
            return None

        try:
            import networkx as nx

            undirected = graph.to_undirected()
            nodes = nx.single_source_shortest_path_length(undirected, account_id, cutoff=hops).keys()
            return graph.subgraph(nodes).copy()
        except ImportError:
            return None

    def export_explanations(
        self,
        output_path: str | Path = PROCESSED_DATA_DIR / "shap_explanations.csv",
        explanations_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Write SHAP explanations to ``data/processed/shap_explanations.csv``."""

        explanations = explanations_df if explanations_df is not None else self.explanations_
        if explanations is None:
            raise RuntimeError("No explanations available. Run compute_shap_attributions() first.")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        explanations.to_csv(output, index=False)
        return explanations

    def _prepare_model_inputs(self, X: pd.DataFrame) -> tuple[Any, list[str], Any]:
        if hasattr(self.model, "named_steps"):
            preprocessor = self.model.named_steps.get("preprocess")
            estimator = self.model.named_steps.get("model")
            if preprocessor is not None and estimator is not None:
                transformed = preprocessor.transform(X)
                feature_names = self._clean_feature_names(preprocessor.get_feature_names_out())
                return transformed, feature_names, estimator

        feature_names = list(X.columns)
        return X, feature_names, self.model

    def _resolve_feature_columns(self, features_df: pd.DataFrame) -> list[str]:
        if self.feature_columns:
            return [col for col in self.feature_columns if col in features_df.columns]

        excluded = {self.account_id_col, "is_suspicious", "is_suspicious_tx", "label", "target"}
        return [col for col in features_df.columns if col not in excluded]

    def _account_ids(self, features_df: pd.DataFrame) -> pd.Series:
        if self.account_id_col in features_df.columns:
            return features_df[self.account_id_col].astype(str)
        return pd.Series(features_df.index.astype(str), index=features_df.index)

    def _driver_group(self, feature: str) -> str:
        lowered = feature.lower()
        for group, prefixes in self.DRIVER_GROUPS.items():
            if any(token in lowered for token in prefixes):
                return group
        return "self_behavior"

    def _extract_graph(self, graph_engine: Any) -> Any:
        if graph_engine is None:
            return None
        return getattr(graph_engine, "G", graph_engine)

    def _incident_edges(self, graph: Any, account_id: str | int) -> list[tuple[Any, Any, Any, dict[str, Any]]]:
        edges = []
        if hasattr(graph, "out_edges"):
            edges.extend(graph.out_edges(account_id, keys=True, data=True))
        if hasattr(graph, "in_edges"):
            edges.extend(graph.in_edges(account_id, keys=True, data=True))
        return edges

    def _edge_amount(self, edge_data: dict[str, Any]) -> float:
        for key in ("amount_local_npr", "Amount", "amount", "weight"):
            if key in edge_data and pd.notna(edge_data[key]):
                return float(edge_data[key])
        return 1.0

    def _clean_feature_names(self, feature_names: Any) -> list[str]:
        cleaned = []
        for name in feature_names:
            text = str(name)
            if "__" in text:
                text = text.split("__", 1)[1]
            cleaned.append(text)
        return cleaned
