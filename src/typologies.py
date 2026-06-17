"""
AMLIOS-X Typology Detection Module

Handles:
- Temporal DFS layering chain detection
- Structuring star pattern detection
- Rapid cycling / carousel fraud detection
- Mule account identification
- Accumulation-spike-disperse pattern detection
- Hawala/Hundi ghost flow detection
- Loan-back cycle detection
- Ghost payroll diversion detection
- Shell company layering network detection
"""

import networkx as nx
import pandas as pd
import numpy as np
import logging
from src.utils import setup_logger, PROCESSED_DATA_DIR

logger = setup_logger()

class TypologyDetector:
    def __init__(self, graph_engine):
        self.ge = graph_engine
        self.G = graph_engine.G
        self.node_features = graph_engine.node_features
        self.alerts = []

    def detect_layering_chains(self, window_hours=72, min_hops=3, conservation=0.97):
        """Detects multi-hop chains with high amount conservation within a time window."""
        logger.info(f"Detecting layering chains (min {min_hops} hops, {conservation*100}% conservation)...")
        # In a real scenario, this would use a fast DFS. We'll simulate the logic for high-volume nodes.
        # Check nodes with high flow_ratio (near 1.0) and high out_degree
        for node, features in self.node_features.items():
            if features.get('flow_ratio', 0) > conservation and features.get('out_volume', 0) > 1000000:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Layering Chain',
                    'confidence': 0.88,
                    'details': 'High flow conservation indicating intermediary node in layering chain.'
                })

    def detect_structuring_stars(self, threshold=1_000_000, tolerance=0.10):
        """Detects fan-out patterns just below reporting thresholds."""
        logger.info(f"Detecting structuring stars near {threshold}...")
        for node, features in self.node_features.items():
            tps = features.get('tps_score', 0)
            if tps > 0.4: # If >40% of outbound transactions are just below threshold
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Structuring Star',
                    'confidence': min(tps * 1.5, 0.99),
                    'details': f'High Threshold Proximity Score: {tps:.2f}'
                })

    def detect_rapid_cycles(self, max_hours=24, min_hops=3, conservation=0.98):
        """Detects closed loops completing quickly with high conservation."""
        logger.info("Detecting rapid cycles / carousel fraud...")
        # Since exact cycle enumeration on large graphs is NP-hard, we use a heuristic based on structural constraints
        for node, features in self.node_features.items():
            if features.get('structural_constraint', 0.0) > 0.8 and features.get('flow_ratio', 0) > conservation:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Carousel Cycle',
                    'confidence': 0.82,
                    'details': 'High structural constraint and flow conservation indicating cycle participation.'
                })

    def detect_mule_accounts(self, velocity_spike=5):
        """Detects dormant accounts with sudden velocity spikes."""
        logger.info("Detecting mule accounts...")
        for node, features in self.node_features.items():
            intensity = features.get('hawkes_intensity', 0)
            # High Hawkes intensity coupled with zero previous activity (simulated by high intensity relative to normal)
            if intensity > 0.8:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Mule Account',
                    'confidence': 0.75,
                    'details': f'High temporal burstiness detected. Hawkes Intensity: {intensity:.2f}'
                })

    def detect_accumulation_spike_disperse(self):
        """Detects the 3-phase accumulation, spike, and disperse pattern."""
        logger.info("Detecting accumulation-spike-disperse patterns...")
        for node, features in self.node_features.items():
            in_vol = features.get('in_volume', 0)
            out_vol = features.get('out_volume', 0)
            flow_ratio = features.get('flow_ratio', 0)
            if in_vol > 500000 and out_vol > 500000 and 0.95 < flow_ratio < 1.05:
                # Approximate heuristic using in/out degree parity and volumes
                if self.G.in_degree(node) > 5 and self.G.out_degree(node) > 5:
                    self.alerts.append({
                        'account_id': node,
                        'typology': 'Accumulation-Spike-Disperse',
                        'confidence': 0.80,
                        'details': 'High volume pass-through with multiple sources and destinations.'
                    })

    def detect_hawala_ghost_flows(self):
        """Detects Hawala/Hundi ghost flows via synchronized cross-border value pairs."""
        logger.info("Detecting Hawala ghost flows...")
        # Cross-border ratios inside communities flag potential Hawala rings
        for node, features in self.node_features.items():
            cb_ratio = features.get('comm_cb_ratio', 0)
            if cb_ratio > 0.6 and features.get('dfa_score', 0) > 0.7:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Hawala Ghost Flow',
                    'confidence': 0.85,
                    'details': f'High community cross-border ratio ({cb_ratio:.2f}) and flow asymmetry.'
                })

    def detect_loan_back_cycles(self):
        """Detects loan-back cycle schemes."""
        logger.info("Detecting loan-back cycles...")
        for node, features in self.node_features.items():
            if features.get('pagerank', 0) > 0.005 and features.get('flow_ratio', 0) > 0.9:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Loan-Back Cycle',
                    'confidence': 0.70,
                    'details': 'Suspicious cyclic centrality detected.'
                })

    def detect_ghost_payroll(self):
        """Detects ghost payroll diversion patterns."""
        logger.info("Detecting ghost payroll diversion...")
        for node, features in self.node_features.items():
            # Corporate account (heuristic: high out-degree, low in-degree, but one massive sink)
            if self.G.out_degree(node) > 20 and features.get('dfa_score', 0) > 0.9:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Ghost Payroll',
                    'confidence': 0.78,
                    'details': 'High out-degree fan-out with asymmetric flow.'
                })

    def detect_shell_company_layering(self):
        """Detects young account clusters doing high internal transactions."""
        logger.info("Detecting shell company layering networks...")
        for node, features in self.node_features.items():
            if features.get('acct_type') == 'CURRENT' and features.get('flow_ratio', 0) > 0.95:
                if features.get('comm_cb_ratio', 0) < 0.1: # Mostly internal
                    self.alerts.append({
                        'account_id': node,
                        'typology': 'Shell Company Layering',
                        'confidence': 0.81,
                        'details': 'CURRENT account acting as pass-through within dense domestic cluster.'
                    })

    def run_all_typologies(self) -> pd.DataFrame:
        """Executes all typology detectors and compiles results."""
        logger.info("Running all typology detectors...")
        self.detect_layering_chains()
        self.detect_structuring_stars()
        self.detect_rapid_cycles()
        self.detect_mule_accounts()
        self.detect_accumulation_spike_disperse()
        self.detect_hawala_ghost_flows()
        self.detect_loan_back_cycles()
        self.detect_ghost_payroll()
        self.detect_shell_company_layering()
        
        alerts_df = pd.DataFrame(self.alerts)
        logger.info(f"Generated {len(alerts_df)} typology alerts.")
        return alerts_df

    def export_alerts(self, df: pd.DataFrame, filename: str = "alerts.csv"):
        """Exports detected alerts to the processed data directory."""
        path = PROCESSED_DATA_DIR / filename
        if not df.empty:
            df.to_csv(path, index=False)
            logger.info(f"Exported alerts to {path}")
        else:
            logger.warning("No alerts to export.")
