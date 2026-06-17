"""
Unit tests for Risk Fusion Engine (Dempster-Shafer theory & contagion propagation)
"""

import unittest
import pandas as pd
import numpy as np
from src.graph_engine import ContinuousTimeGraphEngine
from src.risk_fusion import RiskFusionEngine

class TestRiskFusion(unittest.TestCase):
    def setUp(self):
        # Create mock accounts & transactions to construct graph structure
        self.accounts_df = pd.DataFrame({
            'account_id': [101, 102],
            'acct_type': ['SAVINGS', 'CURRENT']
        })
        self.tx_df = pd.DataFrame({
            'Sender_account': [101],
            'Receiver_account': [102],
            'amount_local_npr': [200000.0],
            'cross_border_flag': [0],
            'Date': ['2023-01-01'],
            'Time': ['10:00:00']
        })
        self.ge = ContinuousTimeGraphEngine()
        self.ge.build_multigraph(self.tx_df, self.accounts_df)
        self.ge.compute_centrality_features()
        
    def test_dempster_combination(self):
        engine = RiskFusionEngine(self.ge)
        
        # High belief source
        m1 = {'S': 0.8, 'NS': 0.1, 'Theta': 0.1}
        # Medium belief source
        m2 = {'S': 0.6, 'NS': 0.2, 'Theta': 0.2}
        
        m_combined = engine.dempster_combination(m1, m2)
        
        # Combined belief in suspicious 'S' should be higher than either individually
        self.assertGreater(m_combined['S'], 0.8)
        self.assertLess(m_combined['NS'], 0.15)
        self.assertAlmostEqual(sum(m_combined.values()), 1.0, places=4)

    def test_fuse_risk_signals_and_propagation(self):
        engine = RiskFusionEngine(self.ge)
        
        # Mock inputs
        xgb_scores = pd.DataFrame({
            'account_id': ['101', '102'],
            'risk_score': [0.1, 0.9] # 102 is highly suspicious
        })
        typology_alerts = pd.DataFrame({
            'account_id': ['102'],
            'confidence': [0.85]
        })
        str_verification = pd.DataFrame({
            'account_id': ['102'],
            'claim_type': ['high_volume'],
            'verification_status': ['CONFIRMED']
        })
        
        fused = engine.fuse_risk_signals(xgb_scores, typology_alerts, str_verification)
        self.assertEqual(len(fused), 2)
        
        # 102 should have much higher fused score than 101
        fused_101 = fused[fused['account_id'] == '101'].iloc[0]['risk_score_fused']
        fused_102 = fused[fused['account_id'] == '102'].iloc[0]['risk_score_fused']
        self.assertGreater(fused_102, fused_101)
        
        # Test propagation
        # Node 101 sends to Node 102. Under downstream propagation with decay, risk of 102
        # propagates back/forward. In our formulation:
        # R_prop(v) = R_fused(v) + sum_{u in N_in(v)} R_prop(u) * flow_weight * decay
        # Since 101 sends to 102, 102's risk prop should increase based on 101's risk.
        propagated = engine.propagate_risk_contagion(fused)
        
        self.assertEqual(len(propagated), 2)
        self.assertIn('risk_score', propagated.columns)
        self.assertIn('risk_band', propagated.columns)

if __name__ == '__main__':
    unittest.main()
