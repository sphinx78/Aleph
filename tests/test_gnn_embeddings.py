"""
Unit tests for GNN Embeddings (DeepWalk, TGAT, HAN)
"""

import unittest
import pandas as pd
import numpy as np
import networkx as nx
from src.graph_engine import ContinuousTimeGraphEngine
from src.gnn_embeddings import DynamicGraphEmbeddings

class TestGNNEmbeddings(unittest.TestCase):
    def setUp(self):
        # Create mock accounts & transactions to construct graph structure
        self.accounts_df = pd.DataFrame({
            'account_id': [101, 102, 103],
            'account_number': ['NP101', 'NP102', 'NP103'],
            'acct_type': ['SAVINGS', 'CURRENT', 'CURRENT'],
            'name': ['John Doe', 'Jane Doe', 'Jane Doe'], # jane owns two accounts
            'branch': ['BR1', 'BR1', 'BR2'],
            'institution': ['NIBL', 'NIBL', 'NCC'],
            'pep_flag': [0, 0, 0],
            'sanctions_hit': [0, 0, 0]
        })
        
        self.tx_df = pd.DataFrame({
            'Sender_account': [101, 102],
            'Receiver_account': [102, 103],
            'amount_local_npr': [200000.0, 500000.0],
            'cross_border_flag': [0, 0],
            'Date': ['2023-01-01', '2023-01-01'],
            'Time': ['10:00:00', '10:05:00']
        })
        
        self.ge = ContinuousTimeGraphEngine()
        self.ge.build_multigraph(self.tx_df, self.accounts_df)
        self.ge.compute_centrality_features()
        self.ge.compute_hawkes_intensity()
        
    def test_embeddings_dimensions(self):
        generator = DynamicGraphEmbeddings(self.ge, embedding_dim=8)
        
        # Test DeepWalk SVD NetMF
        dw = generator.generate_deepwalk_embeddings()
        self.assertEqual(dw.shape, (3, 8))
        
        # Test TGAT continuous-time temporal embeddings
        tgat = generator.generate_tgat_embeddings()
        self.assertEqual(tgat.shape, (3, 8))
        
        # Test HAN metapath-based embeddings
        han = generator.generate_han_embeddings()
        self.assertEqual(han.shape, (3, 8))
        
        # Test combined embeddings export
        df = generator.compute_all_embeddings()
        self.assertEqual(len(df), 3)
        self.assertIn('emb_dw_0', df.columns)
        self.assertIn('emb_tgat_0', df.columns)
        self.assertIn('emb_han_0', df.columns)

if __name__ == '__main__':
    unittest.main()
