"""
AMLIOS-X STR Validator Component

Renders side-by-side views comparing STR narrative claims against
actual transaction graph evidence, showing verification status.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def render_verification_view(report_id: str | int | None = None) -> pd.DataFrame:
    """Render STR narrative verification evidence for an analyst."""

    try:
        import streamlit as st
    except ImportError as exc:
        raise ImportError("STR validation view requires streamlit from requirements.txt.") from exc

    verification = load_verification_matrix()
    if verification.empty:
        st.info("STR verification output is not available yet. Run the narrative verifier when DevA Phase 6 lands.")
        return verification

    report_col = _first_existing(verification, ["report_id", "xml_file", "str_id"])
    if report_id is not None and report_col:
        filtered = verification[verification[report_col].astype(str) == str(report_id)]
    else:
        filtered = verification

    if filtered.empty:
        st.warning("No verification rows match the selected report.")
        return filtered

    status_col = _first_existing(filtered, ["status", "verification_status"])
    if status_col:
        status_counts = filtered[status_col].value_counts().rename_axis("status").reset_index(name="count")
        st.dataframe(status_counts, width="stretch", hide_index=True)

    st.dataframe(filtered.head(100), width="stretch", hide_index=True)
    return filtered


def load_verification_matrix() -> pd.DataFrame:
    """Load STR verification output if present."""

    candidates = [
        PROCESSED_DIR / "str_verification.csv",
        PROCESSED_DIR / "verification_matrix.csv",
        PROCESSED_DIR / "extracted_entities.csv",
    ]
    for path in candidates:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def _first_existing(df: pd.DataFrame, columns: list[str]) -> str | None:
    return next((col for col in columns if col in df.columns), None)
