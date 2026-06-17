"""
Unit tests for src/graph_engine.py
"""

import unittest
import pandas as pd
import numpy as np
import networkx as nx
from src.graph_engine import ContinuousTimeGraphEngine

class TestGraphEngine(unittest.TestCase):
    def setUp(self):
        # Create mock accounts
        self.accounts_df = pd.DataFrame({
            'account_id': [101, 102, 103, 104],
            'account_number': ['NP101', 'NP102', 'NP103', 'NP104'],
            'acct_type': ['SAVINGS', 'SAVINGS', 'CURRENT', 'CURRENT'],
            'risk_grade': ['RISK-LOW', 'RISK-MED', 'RISK-HIGH', 'RISK-LOW'],
            'pep_flag': [0, 0, 1, 0],
            'sanctions_hit': [0, 0, 0, 0]
        })
        
        # Create mock transactions
        # 101 sends to 102, 102 to 103, 103 to 104
        self.tx_df = pd.DataFrame({
            'Sender_account': [101, 101, 102, 103],
            'Receiver_account': [102, 102, 103, 104],
            'amount_local_npr': [950000.0, 50000.0, 1000000.0, 2000000.0],
            'cross_border_flag': [0, 0, 1, 0],
            'Date': ['2023-01-01', '2023-01-01', '2023-01-02', '2023-01-03'],
            'Time': ['10:00:00', '10:05:00', '11:00:00', '12:00:00']
        })
        
        self.engine = ContinuousTimeGraphEngine()
        
    def test_full_pipeline(self):
        # Build multigraph
        self.engine.build_multigraph(self.tx_df, self.accounts_df)
        self.assertEqual(self.engine.G.number_of_nodes(), 4)
        self.assertEqual(self.engine.G.number_of_edges(), 4)
        
        # Compute centralities
        self.engine.compute_centrality_features()
        # Check volume metrics
        self.assertIn(101, self.engine.node_features)
        self.assertEqual(self.engine.node_features[101]['out_volume'], 1000000.0)
        self.assertEqual(self.engine.node_features[102]['in_volume'], 1000000.0)
        self.assertEqual(self.engine.node_features[102]['out_volume'], 1000000.0)
        self.assertAlmostEqual(self.engine.node_features[102]['flow_ratio'], 1.0, places=2)
        
        # Compute asymmetry
        self.engine.compute_asymmetry_index()
        self.assertIn('dfa_score', self.engine.node_features[101])
        # Node 101 has only outgoing volume, DFA should be close to 1
        self.assertAlmostEqual(self.engine.node_features[101]['dfa_score'], 1.0, places=4)
        # Node 102 has equal incoming and outgoing volume, DFA should be close to 0
        self.assertAlmostEqual(self.engine.node_features[102]['dfa_score'], 0.0, places=4)
        
        # Compute Hawkes
        self.engine.compute_hawkes_intensity()
        self.assertIn('hawkes_intensity', self.engine.node_features[101])
        # Node 101 has two transactions separated by 5 minutes (1/12 hour)
        self.assertGreater(self.engine.node_features[101]['hawkes_intensity'], 0.01)
        
        # Compute Threshold Proximity
        # 101 sends 950000 which is within 10% tolerance below 1,000,000
        self.engine.compute_threshold_proximity(threshold=1000000, tolerance=0.10)
        self.assertIn('tps_score', self.engine.node_features[101])
        # Out of 2 transactions, 1 is structuring (950000), so TPS should be 0.5
        self.assertEqual(self.engine.node_features[101]['tps_score'], 0.5)
        
        # Leiden Community Detection
        self.engine.detect_communities_leiden()
        self.assertIn('community_id', self.engine.node_features[101])
        
        # Community Risk Indices
        self.engine.compute_community_risk_indices()
        self.assertIn('comm_cb_ratio', self.engine.node_features[101])
        
        # Structural Holes
        self.engine.compute_structural_holes()
        self.assertIn('structural_constraint', self.engine.node_features[101])
        
        # Feature Matrix Compilation
        df = self.engine.build_node_feature_matrix()
        self.assertEqual(len(df), 4)
        self.assertIn('account_id', df.columns)
        self.assertIn('pagerank', df.columns)
        self.assertIn('hawkes_intensity', df.columns)
        self.assertIn('tps_score', df.columns)

if __name__ == '__main__':
    unittest.main()
