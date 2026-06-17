"""
Unit tests for src/typologies.py
"""

import unittest
import networkx as nx
import pandas as pd
from src.typologies import TypologyDetector

class MockGraphEngine:
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self.node_features = {}
        self.community_map = {}

class TestTypologies(unittest.TestCase):
    def setUp(self):
        self.ge = MockGraphEngine()
        
        # Populate self.ge.G with nodes of type Account
        for i in range(1, 100):
            node_id = str(i)
            self.ge.G.add_node(node_id, type='Account')
            self.ge.node_features[node_id] = {
                'account_id': node_id,
                'flow_ratio': 0.0,
                'out_volume': 0.0,
                'in_volume': 0.0,
                'tps_score': 0.0,
                'hawkes_intensity': 0.0,
                'pagerank': 0.0,
                'structural_constraint': 1.0,
                'acct_type': 'SAVINGS',
                'comm_cb_ratio': 0.0,
                'dfa_score': 0.0
            }
            self.ge.community_map[node_id] = 1
            
        # 1. Setup for Layering Chains (Node 1 -> 2 -> 3 -> 4)
        t_base = pd.Timestamp('2023-01-01 10:00:00')
        self.ge.G.add_edge('1', '2', relation='SENDS', amount=250000.0, timestamp=t_base)
        self.ge.G.add_edge('2', '3', relation='SENDS', amount=250000.0, timestamp=t_base + pd.Timedelta(hours=2))
        self.ge.G.add_edge('3', '4', relation='SENDS', amount=250000.0, timestamp=t_base + pd.Timedelta(hours=4))
        self.ge.node_features['1']['flow_ratio'] = 1.0
        self.ge.node_features['1']['out_volume'] = 250000.0
        
        # 2. Setup for Structuring Stars (Node 2)
        # Node 2 sends just below 1,000,000 to multiple recipients
        self.ge.G.add_edge('2', '21', relation='SENDS', amount=950000.0)
        self.ge.G.add_edge('2', '22', relation='SENDS', amount=950000.0)
        self.ge.G.add_edge('2', '23', relation='SENDS', amount=950000.0)
        self.ge.node_features['2']['tps_score'] = 0.50
        
        # 3. Setup for Carousel Cycles (Node 3 -> 31 -> 32 -> 3)
        self.ge.G.add_edge('3', '31', relation='SENDS', amount=500000.0, timestamp=t_base)
        self.ge.G.add_edge('31', '32', relation='SENDS', amount=500000.0, timestamp=t_base + pd.Timedelta(hours=1))
        self.ge.G.add_edge('32', '3', relation='SENDS', amount=500000.0, timestamp=t_base + pd.Timedelta(hours=2))
        self.ge.node_features['3']['structural_constraint'] = 0.90
        self.ge.node_features['3']['flow_ratio'] = 1.0
        
        # 4. Setup for Mule Accounts (Node 4)
        self.ge.node_features['4']['hawkes_intensity'] = 0.90
        self.ge.node_features['4']['flow_ratio'] = 1.0
        self.ge.node_features['4']['out_volume'] = 150000.0
        
        # 5. Setup for Accumulation-Spike-Disperse (Node 5)
        # 5 incoming edges, 5 outgoing edges
        for idx in range(5):
            u_id = f"5_in_{idx}"
            v_id = f"5_out_{idx}"
            self.ge.G.add_node(u_id, type='Account')
            self.ge.G.add_node(v_id, type='Account')
            self.ge.node_features[u_id] = {'account_id': u_id}
            self.ge.node_features[v_id] = {'account_id': v_id}
            self.ge.G.add_edge(u_id, '5', relation='SENDS', amount=150000.0, timestamp=t_base)
            self.ge.G.add_edge('5', v_id, relation='SENDS', amount=150000.0, timestamp=t_base + pd.Timedelta(hours=5))
            
        self.ge.node_features['5']['flow_ratio'] = 1.0
        self.ge.node_features['5']['in_volume'] = 750000.0
        self.ge.node_features['5']['out_volume'] = 750000.0
        
        # 6. Setup for Hawala Ghost Flows (Node 6)
        # Synchronized cross-border offset pairs
        self.ge.G.add_node('6_cb_s', type='Account')
        self.ge.G.add_node('6_cb_r', type='Account')
        self.ge.G.add_node('6_dom_s', type='Account')
        self.ge.node_features['6_cb_s'] = {'account_id': '6_cb_s'}
        self.ge.node_features['6_cb_r'] = {'account_id': '6_cb_r'}
        self.ge.node_features['6_dom_s'] = {'account_id': '6_dom_s'}
        
        self.ge.G.add_edge('6_cb_s', '6_cb_r', relation='SENDS', amount=350000.0, timestamp=t_base, cross_border=1)
        self.ge.G.add_edge('6_dom_s', '6', relation='SENDS', amount=350000.0, timestamp=t_base + pd.Timedelta(minutes=5), cross_border=0)
        
        # 7. Setup for Loan-Back Cycles (Node 7)
        self.ge.node_features['7']['pagerank'] = 0.006
        self.ge.node_features['7']['flow_ratio'] = 0.98
        self.ge.G.add_edge('7', '71', relation='SENDS', amount=600000.0)
        self.ge.G.add_edge('71', '7', relation='SENDS', amount=600000.0)
        
        # 8. Setup for Ghost Payroll (Node 8)
        # Corporate fan-out of 10 nodes forwarding to consolidator '801'
        self.ge.G.add_node('801', type='Account')
        self.ge.node_features['801'] = {'account_id': '801'}
        for idx in range(10):
            emp_id = f"emp_{idx}"
            self.ge.G.add_node(emp_id, type='Account')
            self.ge.node_features[emp_id] = {'account_id': emp_id, 'flow_ratio': 1.0}
            self.ge.G.add_edge('8', emp_id, relation='SENDS', amount=80000.0, timestamp=t_base)
            self.ge.G.add_edge(emp_id, '801', relation='SENDS', amount=80000.0, timestamp=t_base + pd.Timedelta(hours=2))
            
        # 9. Setup for Shell Company Layering (Node 9)
        self.ge.node_features['9']['acct_type'] = 'CURRENT'
        self.ge.node_features['9']['flow_ratio'] = 0.98
        self.ge.node_features['9']['comm_cb_ratio'] = 0.05
        self.ge.community_map['9'] = 2
        # Add internal transaction from community member
        self.ge.G.add_node('9_memb', type='Account')
        self.ge.node_features['9_memb'] = {'account_id': '9_memb'}
        self.ge.community_map['9_memb'] = 2
        self.ge.G.add_edge('9_memb', '9', relation='SENDS', amount=800000.0)
        
        self.detector = TypologyDetector(self.ge)
        
    def test_detect_layering_chains(self):
        self.detector.detect_layering_chains()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Layering Chain']
        self.assertGreaterEqual(len(alerts), 1)
        flagged_ids = [a['account_id'] for a in alerts]
        self.assertIn('4', flagged_ids)
        
    def test_detect_structuring_stars(self):
        self.detector.detect_structuring_stars()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Structuring Star']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], '2')

    def test_detect_rapid_cycles(self):
        self.detector.detect_rapid_cycles()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Carousel Cycle']
        self.assertGreater(len(alerts), 0)
        flagged_ids = [a['account_id'] for a in alerts]
        self.assertIn('3', flagged_ids)

    def test_detect_mule_accounts(self):
        self.detector.detect_mule_accounts()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Mule Account']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], '4')

    def test_detect_accumulation_spike_disperse(self):
        self.detector.detect_accumulation_spike_disperse()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Accumulation-Spike-Disperse']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], '5')

    def test_detect_hawala_ghost_flows(self):
        self.detector.detect_hawala_ghost_flows()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Hawala Ghost Flow']
        self.assertEqual(len(alerts), 2)
        # Should flag nodes 6_cb_s and 6 (which is target of domestic offset)
        flagged_ids = [a['account_id'] for a in alerts]
        self.assertIn('6_cb_s', flagged_ids)
        self.assertIn('6', flagged_ids)

    def test_detect_loan_back_cycles(self):
        self.detector.detect_loan_back_cycles()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Loan-Back Cycle']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], '7')

    def test_detect_ghost_payroll(self):
        self.detector.detect_ghost_payroll()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Ghost Payroll']
        self.assertEqual(len(alerts), 2)
        flagged_ids = [a['account_id'] for a in alerts]
        self.assertIn('8', flagged_ids)
        self.assertIn('801', flagged_ids)

    def test_detect_shell_company_layering(self):
        self.detector.detect_shell_company_layering()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Shell Company Layering']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], '9')

    def test_run_all_typologies(self):
        df = self.detector.run_all_typologies()
        self.assertGreater(len(df), 0)

if __name__ == '__main__':
    unittest.main()
