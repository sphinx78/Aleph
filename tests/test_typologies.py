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

class TestTypologies(unittest.TestCase):
    def setUp(self):
        self.ge = MockGraphEngine()
        
        # Populate self.ge.G with nodes and edges to support degree queries
        self.ge.G.add_nodes_from(range(1, 10))
        
        # Add edges for Node 5 (Accumulation-Spike-Disperse needs >5 in-degree and >5 out-degree)
        for i in range(10, 16):
            self.ge.G.add_edge(i, 5) # 6 incoming
            self.ge.G.add_edge(5, i + 10) # 6 outgoing
            
        # Add edges for Node 8 (Ghost Payroll needs >20 out-degree)
        for i in range(100, 125):
            self.ge.G.add_edge(8, i)
            
        # Setup mock node features
        self.ge.node_features = {
            1: {'out_volume': 2000000, 'flow_ratio': 0.98},
            2: {'tps_score': 0.5},
            3: {'structural_constraint': 0.9, 'flow_ratio': 0.99},
            4: {'hawkes_intensity': 0.9},
            5: {'in_volume': 600000, 'out_volume': 600000, 'flow_ratio': 1.0},
            6: {'comm_cb_ratio': 0.7, 'dfa_score': 0.8},
            7: {'pagerank': 0.006, 'flow_ratio': 0.95},
            8: {'dfa_score': 0.95},
            9: {'acct_type': 'CURRENT', 'flow_ratio': 0.98, 'comm_cb_ratio': 0.05}
        }
        self.detector = TypologyDetector(self.ge)
        
    def test_detect_layering_chains(self):
        self.detector.detect_layering_chains()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Layering Chain']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 1)
        
    def test_detect_structuring_stars(self):
        self.detector.detect_structuring_stars()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Structuring Star']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 2)

    def test_detect_rapid_cycles(self):
        self.detector.detect_rapid_cycles()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Carousel Cycle']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 3)

    def test_detect_mule_accounts(self):
        self.detector.detect_mule_accounts()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Mule Account']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 4)

    def test_detect_accumulation_spike_disperse(self):
        self.detector.detect_accumulation_spike_disperse()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Accumulation-Spike-Disperse']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 5)

    def test_detect_hawala_ghost_flows(self):
        self.detector.detect_hawala_ghost_flows()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Hawala Ghost Flow']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 6)

    def test_detect_loan_back_cycles(self):
        self.detector.detect_loan_back_cycles()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Loan-Back Cycle']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 7)

    def test_detect_ghost_payroll(self):
        self.detector.detect_ghost_payroll()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Ghost Payroll']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 8)

    def test_detect_shell_company_layering(self):
        self.detector.detect_shell_company_layering()
        alerts = [a for a in self.detector.alerts if a['typology'] == 'Shell Company Layering']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['account_id'], 9)

    def test_run_all_typologies(self):
        df = self.detector.run_all_typologies()
        self.assertEqual(len(df), 9)
        self.assertEqual(len(df['typology'].unique()), 9)

if __name__ == '__main__':
    unittest.main()
