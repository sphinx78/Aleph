"""
AMLIOS-X Streamlit Dashboard — Main Entry Point

Launch with: streamlit run app/app.py

Features:
- Risk score filtering and high-risk entity action queue
- Account deep-dive with diagnostic metrics
- Money-flow visualization
- STR narrative vs graph evidence validation
- SHAP attribution charts
- Typology alerts table
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "STUDENT_DATASET"

from app.components.flow_visualizer import load_account_transactions, render_ego_graph
from app.components.str_validator import render_verification_view
from src.ml_models import AMLRiskClassifier


def main() -> None:
    import plotly.express as px
    import streamlit as st

    st.set_page_config(
        page_title="AMLIOS-X Analyst Dashboard",
        page_icon="AMLIOS-X",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css(st)

    st.title("AMLIOS-X Analyst Dashboard")

    risk_scores = load_risk_scores()
    if risk_scores.empty:
        st.error("No risk score data could be loaded.")
        return

    min_score = st.sidebar.slider("Minimum risk score", 0.0, 1.0, 0.50, 0.01)
    selected_band = st.sidebar.multiselect(
        "Risk bands",
        ["CRITICAL", "SEVERE", "HIGH", "ELEVATED", "LOW"],
        default=["CRITICAL", "SEVERE", "HIGH"],
    )

    queue = risk_scores[risk_scores["risk_score"] >= min_score].copy()
    if selected_band and "risk_band" in queue.columns:
        queue = queue[queue["risk_band"].isin(selected_band)]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Entities Scored", f"{len(risk_scores):,}")
    metric_cols[1].metric("Queue Size", f"{len(queue):,}")
    metric_cols[2].metric("Max Risk", f"{risk_scores['risk_score'].max():.3f}")
    metric_cols[3].metric("Critical Entities", f"{(risk_scores['risk_band'] == 'CRITICAL').sum():,}")

    left, right = st.columns([1.35, 1.0], gap="large")
    with left:
        st.subheader("High-Risk Entity Queue")
        st.dataframe(
            queue.head(250),
            use_container_width=True,
            hide_index=True,
            column_config={
                "risk_score": st.column_config.ProgressColumn(
                    "Risk Score",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.3f",
                )
            },
        )

    with right:
        selected_account = st.selectbox(
            "Account deep-dive",
            queue["account_id"].astype(str).head(500).tolist()
            if not queue.empty
            else risk_scores["account_id"].astype(str).head(500).tolist(),
        )
        render_account_summary(st, selected_account, risk_scores)

    tabs = st.tabs(["Flow", "Explainability", "STR Evidence", "Typology Alerts", "Model Health"])

    with tabs[0]:
        transactions = load_account_transactions(selected_account)
        render_ego_graph(selected_account, transactions_df=transactions)
        if not transactions.empty:
            st.dataframe(
                transactions[
                    [
                        col
                        for col in [
                            "Date",
                            "Time",
                            "Sender_account",
                            "Receiver_account",
                            "amount_local_npr",
                            "Payment_currency",
                            "cross_border_flag",
                        ]
                        if col in transactions.columns
                    ]
                ].head(100),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[1]:
        explanations = load_explanations()
        if explanations.empty:
            st.info("SHAP explanations are not available yet. Run Phase 10 after training the classifier.")
        else:
            account_explanations = explanations[
                explanations["account_id"].astype(str) == str(selected_account)
            ].head(20)
            if account_explanations.empty:
                st.warning("No explanation rows are available for this account.")
            else:
                fig = px.bar(
                    account_explanations.sort_values("abs_shap_value"),
                    x="shap_value",
                    y="feature",
                    color="driver_group",
                    orientation="h",
                    height=560,
                )
                st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        render_verification_view()

    with tabs[3]:
        alerts = load_alerts()
        if alerts.empty:
            st.info("Typology alerts are not available yet. Run DevA typology phases when ready.")
        else:
            st.dataframe(alerts.head(500), use_container_width=True, hide_index=True)

    with tabs[4]:
        metrics = load_model_metrics()
        if metrics:
            st.json(metrics)
        else:
            st.info("Model metrics will appear here after `main.py --train-model` runs successfully.")


def load_risk_scores() -> pd.DataFrame:
    risk_path = PROCESSED_DIR / "risk_scores.csv"
    if risk_path.exists():
        return _normalize_risk_scores(pd.read_csv(risk_path))

    classifier = AMLRiskClassifier()
    try:
        features = classifier.load_features()
    except Exception:
        return pd.DataFrame()

    scores = pd.DataFrame({"account_id": features["account_id"].astype(str)})
    volume_cols = [col for col in features.columns if "amount_local_npr" in col and col.endswith("_sum")]
    cross_border_cols = [col for col in features.columns if "cross_border" in col]

    volume_signal = _rank_signal(features[volume_cols].sum(axis=1)) if volume_cols else 0.0
    border_signal = _rank_signal(features[cross_border_cols].sum(axis=1)) if cross_border_cols else 0.0
    label_signal = features.get("is_suspicious", pd.Series(0, index=features.index)).astype(float)
    scores["risk_score"] = (0.55 * label_signal + 0.30 * volume_signal + 0.15 * border_signal).clip(0, 1)
    return _normalize_risk_scores(scores)


def render_account_summary(st, account_id: str, risk_scores: pd.DataFrame) -> None:
    row = risk_scores[risk_scores["account_id"].astype(str) == str(account_id)].head(1)
    if row.empty:
        st.info("Select an account from the queue.")
        return

    record = row.iloc[0]
    st.metric("Risk Score", f"{record['risk_score']:.3f}")
    st.metric("Risk Band", record.get("risk_band", "UNCLASSIFIED"))
    if "risk_percentile" in record:
        st.metric("Risk Percentile", f"{record['risk_percentile']:.2f}")


def load_explanations() -> pd.DataFrame:
    path = PROCESSED_DIR / "shap_explanations.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_alerts() -> pd.DataFrame:
    path = PROCESSED_DIR / "alerts.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_model_metrics() -> dict[str, object]:
    path = PROCESSED_DIR / "model_metrics.json"
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text())


def _normalize_risk_scores(scores: pd.DataFrame) -> pd.DataFrame:
    normalized = scores.copy()
    if "account_id" not in normalized.columns:
        normalized.insert(0, "account_id", normalized.index.astype(str))
    if "risk_score" not in normalized.columns:
        raise ValueError("Risk score data must include a risk_score column.")
    normalized["risk_score"] = normalized["risk_score"].astype(float).clip(0, 1)
    if "risk_percentile" not in normalized.columns:
        normalized["risk_percentile"] = (normalized["risk_score"].rank(pct=True) * 100).round(2)
    if "risk_band" not in normalized.columns:
        normalized["risk_band"] = pd.cut(
            normalized["risk_score"],
            bins=[-np.inf, 0.25, 0.50, 0.75, 0.90, np.inf],
            labels=["LOW", "ELEVATED", "HIGH", "SEVERE", "CRITICAL"],
        ).astype(str)
    if "rank" not in normalized.columns:
        normalized = normalized.sort_values("risk_score", ascending=False).reset_index(drop=True)
        normalized.insert(0, "rank", np.arange(1, len(normalized) + 1))
    return normalized.sort_values("risk_score", ascending=False).reset_index(drop=True)


def _rank_signal(values: pd.Series) -> pd.Series:
    values = pd.Series(values).fillna(0)
    if values.nunique() <= 1:
        return pd.Series(0.0, index=values.index)
    return values.rank(pct=True)


def _inject_css(st) -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetric"] {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            background: #FFFFFF;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
