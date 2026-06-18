"""
ALEPH Streamlit Dashboard — Main Entry Point

Launch with: streamlit run app/app.py

Features:
- Risk score filtering and high-risk entity action queue
- Account deep-dive with diagnostic metrics
- Interactive money-flow ego network visualization
- Topological Data Analysis (TDA) Persistence Homology indicators
- SCAN density community labels (Hub/Outlier/Cluster)
- STR narrative vs graph evidence validation
- SHAP attribution charts
- Analyst Copilot: Auto-generated Suspicious Activity Reports (SAR) with download support
- Typology alerts table
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
current_dir = Path(__file__).resolve().parent

# Remove script directory from sys.path to avoid name collision with app.py
sys.path = [p for p in sys.path if p != str(current_dir)]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "STUDENT_DATASET"

from app.components.flow_visualizer import load_account_transactions, render_ego_graph
from app.components.str_validator import render_verification_view, load_verification_matrix
from src.ml_models import AMLRiskClassifier
from src.copilot import AnalystCopilot
from src.explainability import ExplainabilityEngine


def main() -> None:
    import plotly.express as px
    import streamlit as st

    st.set_page_config(
        page_title="ALEPH - Anti-Money Laundering Intelligence Operating System",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css(st)

    st.title("ALEPH - Anti-Money Laundering Intelligence Operating System")
    st.markdown("---")

    risk_scores = load_risk_scores()
    if risk_scores.empty:
        st.error("No risk score data could be loaded. Make sure to run `python main.py` first.")
        return

    # Load node features and alerts
    node_features = load_node_features()
    alerts = load_alerts()

    # Sidebar Filter Controls
    st.sidebar.title("Filter Panel")
    min_score = st.sidebar.slider("Minimum risk score", 0.0, 1.0, 0.50, 0.01)
    selected_band = st.sidebar.multiselect(
        "Risk bands",
        ["CRITICAL", "SEVERE", "HIGH", "ELEVATED", "LOW"],
        default=["CRITICAL", "SEVERE", "HIGH"],
    )

    queue = risk_scores[risk_scores["risk_score"] >= min_score].copy()
    if selected_band and "risk_band" in queue.columns:
        queue = queue[queue["risk_band"].isin(selected_band)]

    # Top-Level Dashboard Metrics
    metric_cols = st.columns(4)
    metric_cols[0].metric("Entities Scored", f"{len(risk_scores):,}")
    metric_cols[1].metric("Queue Size", f"{len(queue):,}")
    metric_cols[2].metric("Max Risk Score", f"{risk_scores['risk_score'].max():.3f}")
    metric_cols[3].metric("Critical Alert Queue", f"{(risk_scores['risk_band'] == 'CRITICAL').sum():,}")

    left, right = st.columns([1.35, 1.0], gap="large")
    with left:
        st.subheader("High-Risk Analyst Action Queue")
        st.dataframe(
            queue.head(250),
            width="stretch",
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
        st.subheader("Entity Deep-Dive Selector")
        selected_account = st.selectbox(
            "Select Account for Deep-Dive Analysis",
            queue["account_id"].astype(str).head(500).tolist()
            if not queue.empty
            else risk_scores["account_id"].astype(str).head(500).tolist(),
        )
        
        # Render full diagnostic profile
        render_account_summary(st, selected_account, risk_scores, node_features)

    tabs = st.tabs(["Graph Flow View", "Explainability & Copilot", "STR Claims Validator", "Typology Alerts", "Topological & Community Analytics"])

    # TAB 1: Money Flow Ego Network
    with tabs[0]:
        st.subheader(f"Ego Money Flow Network for Account {selected_account}")
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
                width="stretch",
                hide_index=True,
            )

    # TAB 2: SHAP explanations + Copilot Report Generator
    with tabs[1]:
        col1, col2 = st.columns([1.0, 1.2])
        
        with col1:
            st.subheader("SHAP Feature Attributions")
            explanations = load_explanations()
            if explanations.empty:
                st.info("SHAP explanations are not available yet. Run the pipeline first.")
            else:
                account_explanations = explanations[
                    explanations["account_id"].astype(str) == str(selected_account)
                ].head(20)
                if account_explanations.empty:
                    st.warning("No SHAP attributions are available for this account.")
                else:
                    fig = px.bar(
                        account_explanations.sort_values("abs_shap_value"),
                        x="shap_value",
                        y="feature",
                        color="driver_group",
                        orientation="h",
                        height=520,
                        title=f"Feature Contribution (Account {selected_account})"
                    )
                    st.plotly_chart(fig, width="stretch")
                    
        with col2:
            st.subheader("Analyst Copilot — Automatic SAR Narrative Generator")
            
            # Compile Case details for Copilot template
            acc_feat = node_features[node_features['account_id'].astype(str) == str(selected_account)]
            acc_score_row = risk_scores[risk_scores['account_id'].astype(str) == str(selected_account)]
            
            if not acc_feat.empty and not acc_score_row.empty:
                feat_rec = acc_feat.iloc[0]
                score_rec = acc_score_row.iloc[0]
                
                # Fetch risk drivers from explanations
                drivers = {}
                if not explanations.empty:
                    ee = ExplainabilityEngine()
                    drivers = ee.decompose_risk_drivers(selected_account, explanations)
                
                # Fetch flagged typologies for this node
                node_alerts = []
                if not alerts.empty and 'account_id' in alerts.columns:
                    node_alerts = alerts[alerts['account_id'].astype(str) == str(selected_account)]['typology'].tolist()
                    
                # Fetch claims verification
                claims_map = {}
                v_matrix = load_verification_matrix()
                if not v_matrix.empty and 'account_id' in v_matrix.columns:
                    node_v = v_matrix[v_matrix['account_id'].astype(str) == str(selected_account)]
                    for _, v_row in node_v.iterrows():
                        claims_map[v_row['claim_type']] = v_row['verification_status']
                
                case_details = {
                    'account_id': selected_account,
                    'risk_score': score_rec['risk_score'],
                    'risk_band': score_rec.get('risk_band', 'UNKNOWN'),
                    'rank': score_rec.get('rank', 'N/A'),
                    'in_volume': feat_rec.get('in_volume', 0.0),
                    'out_volume': feat_rec.get('out_volume', 0.0),
                    'risk_drivers': drivers,
                    'typologies': node_alerts,
                    'verification_claims': claims_map
                }
                
                copilot = AnalystCopilot()
                report_txt = copilot.generate_case_summary(case_details)
                
                st.text_area("Suspicious Activity Report (SAR) Filing Draft", value=report_txt, height=440)
                st.download_button(
                    label="📥 Download SAR Report TXT",
                    data=report_txt,
                    file_name=f"SAR_Report_Account_{selected_account}.txt",
                    mime="text/plain"
                )
            else:
                st.warning("Ensure the pipeline executes successfully to compile copilot report details.")

    # TAB 3: STR Claims Validator
    with tabs[2]:
        st.subheader("STR Claims Narrative Verification Dashboard")
        render_verification_view()

    # TAB 4: Typology Alerts
    with tabs[3]:
        st.subheader("Flagged Typology Alerts Table")
        if alerts.empty:
            st.info("No typology alerts are available yet.")
        else:
            st.dataframe(alerts.head(500), width="stretch", hide_index=True)

    # TAB 5: Topological & Community Analytics
    with tabs[4]:
        st.subheader("Advanced Topological Data Analysis (TDA) & Community Metrics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Persistence Homology (Betti-0 Barcode)")
            st.markdown(
                "ALEPH filters transactions by amount threshold to compute Betti-0 components. "
                "Robust laundering pipelines persist across multiple thresholds, indicating continuous flow."
            )
            
            acc_feat = node_features[node_features['account_id'].astype(str) == str(selected_account)]
            if not acc_feat.empty:
                rec = acc_feat.iloc[0]
                st.metric("TDA Birth Threshold", f"{rec.get('betti_birth', 0.0):,.0f} NPR")
                st.metric("TDA Death Threshold", f"{rec.get('betti_death', 0.0):,.0f} NPR")
                st.metric("TDA Persistence Length", f"{rec.get('betti_persistence', 0.0):,.0f} NPR")
            else:
                st.warning("TDA features are not populated.")
                
        with col2:
            st.markdown("#### SCAN Density Clustering & Motif Mining")
            st.markdown(
                "SCAN (Structural Clustering Algorithm for Networks) classifies nodes as Core cluster members, "
                "Hubs (bridges between communities), or Outliers."
            )
            
            if not acc_feat.empty:
                rec = acc_feat.iloc[0]
                scan_val = int(rec.get('scan_cluster', -1))
                if scan_val == -1:
                    scan_type = "OUTLIER (Sparse Connection)"
                elif scan_val == -2:
                    scan_type = "HUB (Community Bridge)"
                else:
                    scan_type = f"Cluster {scan_val}"
                    
                st.metric("SCAN Community Type", scan_type)
                
                # Motif counts
                st.metric("Temporal Triangles Detected", f"{int(rec.get('motif_triangle', 0))}")
                st.metric("Temporal Cycle (Carousel) loops", f"{int(rec.get('motif_cycle', 0))}")
            else:
                st.warning("SCAN/Motif features are not populated.")


def load_risk_scores() -> pd.DataFrame:
    risk_path = PROCESSED_DIR / "risk_scores.csv"
    if risk_path.exists():
        return _normalize_risk_scores(pd.read_csv(risk_path))
    return pd.DataFrame()


def load_node_features() -> pd.DataFrame:
    path = PROCESSED_DIR / "node_features.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def render_account_summary(st, account_id: str, risk_scores: pd.DataFrame, node_features: pd.DataFrame) -> None:
    row = risk_scores[risk_scores["account_id"].astype(str) == str(account_id)].head(1)
    if row.empty:
        st.info("Select an account from the queue.")
        return

    record = row.iloc[0]
    
    # Grid of details
    m_cols = st.columns(3)
    m_cols[0].metric("Risk Score (Fused)", f"{record['risk_score']:.3f}")
    m_cols[1].metric("Risk Band", record.get("risk_band", "UNCLASSIFIED"))
    m_cols[2].metric("Risk Percentile", f"{record.get('risk_percentile', 0.0):.2f}")
    
    # Load advanced KYC & topological attributes
    feat_row = node_features[node_features['account_id'].astype(str) == str(account_id)].head(1)
    if not feat_row.empty:
        feat_rec = feat_row.iloc[0]
        st.markdown("##### Account KYC & Network Details")
        st.markdown(
            f"- **PageRank Importance**: `{feat_rec.get('pagerank', 0.0):.6f}`\n"
            f"- **Hawkes Process Intensity**: `{feat_rec.get('hawkes_intensity', 0.0):.4f}`\n"
            f"- **Directed Flow Asymmetry (DFA)**: `{feat_rec.get('dfa_score', 0.0):.2f}`\n"
            f"- **Threshold Proximity (TPS)**: `{feat_rec.get('tps_score', 0.0):.2%}`\n"
            f"- **Burt's Constraint (Structural Hole)**: `{feat_rec.get('structural_constraint', 1.0):.4f}`"
        )


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


def _inject_css(st) -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetric"] {
            border: 1px solid var(--secondary-background-color);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            background-color: transparent;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
