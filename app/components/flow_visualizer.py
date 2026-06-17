"""
AMLIOS-X Flow Visualizer Component

Renders interactive money-flow graph visualizations for selected accounts,
including ego network views and transaction timeline animations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_TRANSACTIONS_PATH = PROJECT_ROOT / "data" / "STUDENT_DATASET" / "transactions.csv"


def render_ego_graph(
    account_id: str | int,
    graph_engine: Any | None = None,
    transactions_df: pd.DataFrame | None = None,
    max_edges: int = 80,
) -> Any:
    """Render an interactive ego money-flow graph for a selected account."""

    try:
        import networkx as nx
        import plotly.graph_objects as go
        import streamlit as st
    except ImportError as exc:
        raise ImportError(
            "Flow visualization requires streamlit, plotly, and networkx from requirements.txt."
        ) from exc

    graph = _graph_from_engine(graph_engine)
    if graph is None:
        graph = _graph_from_transactions(account_id, transactions_df, max_edges=max_edges)

    if graph is None or graph.number_of_nodes() == 0:
        st.info("No money-flow edges are available for this account yet.")
        return None

    plot_graph = graph.to_undirected() if graph.is_directed() else graph
    positions = nx.spring_layout(plot_graph, seed=42, k=0.75)

    edge_x, edge_y, hover_text = [], [], []
    for source, target, data in _edge_iter(graph):
        if source not in positions or target not in positions:
            continue
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        amount = _edge_amount(data)
        hover_text.append(f"{source} -> {target}<br>NPR {amount:,.0f}")

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": 1.2, "color": "#9CA3AF"},
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    selected = str(account_id)
    for node in graph.nodes():
        x, y = positions[node]
        degree = graph.degree(node)
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"Account {node}<br>Degree {degree}")
        node_color.append("#DC2626" if str(node) == selected else "#2563EB")
        node_size.append(26 if str(node) == selected else min(10 + degree * 2, 24))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_text,
        marker={
            "size": node_size,
            "color": node_color,
            "line": {"width": 1, "color": "#111827"},
        },
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        height=520,
        margin={"l": 0, "r": 0, "t": 20, "b": 0},
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"showgrid": False, "zeroline": False, "visible": False},
        yaxis={"showgrid": False, "zeroline": False, "visible": False},
    )
    st.plotly_chart(fig, use_container_width=True)
    return fig


def load_account_transactions(account_id: str | int, limit: int = 2500) -> pd.DataFrame:
    """Load a bounded set of transactions touching ``account_id``."""

    if not RAW_TRANSACTIONS_PATH.exists():
        return pd.DataFrame()

    account = str(account_id)
    chunks = []
    for chunk in pd.read_csv(RAW_TRANSACTIONS_PATH, chunksize=50_000):
        mask = (chunk["Sender_account"].astype(str) == account) | (
            chunk["Receiver_account"].astype(str) == account
        )
        if mask.any():
            chunks.append(chunk.loc[mask])
        if sum(len(part) for part in chunks) >= limit:
            break

    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True).head(limit)


def _graph_from_engine(graph_engine: Any | None) -> Any | None:
    if graph_engine is None:
        return None
    return getattr(graph_engine, "G", graph_engine)


def _graph_from_transactions(
    account_id: str | int,
    transactions_df: pd.DataFrame | None,
    max_edges: int,
) -> Any | None:
    try:
        import networkx as nx
    except ImportError:
        return None

    tx = transactions_df if transactions_df is not None else load_account_transactions(account_id)
    if tx.empty:
        return None

    graph = nx.MultiDiGraph()
    for _, row in tx.head(max_edges).iterrows():
        source = str(row.get("Sender_account", "unknown_sender"))
        target = str(row.get("Receiver_account", "unknown_receiver"))
        graph.add_edge(
            source,
            target,
            amount_local_npr=float(row.get("amount_local_npr", row.get("Amount", 0)) or 0),
            timestamp=f"{row.get('Date', '')} {row.get('Time', '')}".strip(),
        )
    return graph


def _edge_iter(graph: Any):
    if getattr(graph, "is_multigraph", lambda: False)():
        for source, target, _, data in graph.edges(keys=True, data=True):
            yield source, target, data
    else:
        for source, target, data in graph.edges(data=True):
            yield source, target, data


def _edge_amount(data: dict[str, Any]) -> float:
    for key in ("amount_local_npr", "Amount", "amount", "weight"):
        if key in data and pd.notna(data[key]):
            return float(data[key])
    return 0.0
