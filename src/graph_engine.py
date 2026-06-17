"""
AMLIOS-X Graph Engine Module

Handles:
- Building continuous-time directed multigraph from transaction data
- Computing structural centrality metrics (PageRank, betweenness, degree)
- Directed Flow Asymmetry (DFA) calculation
- Hawkes Process intensity scoring
- Threshold Proximity Score (TPS) for structuring detection
- Structural hole exploitation scoring (Burt's constraint)
- Leiden community detection and community-level risk indices
- Exporting the unified node feature matrix
"""

import networkx as nx
import pandas as pd
import numpy as np
import cdlib
from cdlib import algorithms
from src.utils import setup_logger, PROCESSED_DATA_DIR
logger = setup_logger()
class ContinuousTimeGraphEngine:
    """
    Constructs and analyzes the temporal transaction network to extract 
    structural and behavioral features.
    """
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self.node_features = {}
        self.community_map = {}
        
    def build_multigraph(self, tx_df: pd.DataFrame, accounts_df: pd.DataFrame):
        """Builds a continuous-time directed multigraph."""
        logger.info("Building temporal multigraph from transactions...")
        
        # Add nodes with basic KYC attributes
        for _, row in accounts_df.iterrows():
            acc_id = row['account_id']
            self.G.add_node(
                acc_id,
                risk_grade=row.get('risk_grade', 'UNKNOWN'),
                acct_type=row.get('acct_type', 'UNKNOWN'),
                pep_flag=row.get('pep_flag', 0),
                sanctions_hit=row.get('sanctions_hit', 0)
            )
            self.node_features[acc_id] = {'account_id': acc_id}
            
        # Ensure timestamp sorting
        tx_df = tx_df.copy()
        if 'Date' in tx_df.columns and 'Time' in tx_df.columns:
            tx_df['datetime'] = pd.to_datetime(tx_df['Date'].astype(str) + ' ' + tx_df['Time'].astype(str))
        elif 'datetime' not in tx_df.columns:
            logger.warning("No datetime field found, cannot enforce chronological ordering.")
            
        # Add edges
        edges = []
        for _, row in tx_df.iterrows():
            edges.append((
                row['Sender_account'],
                row['Receiver_account'],
                {
                    'amount': row.get('amount_local_npr', 0.0),
                    'timestamp': row.get('datetime', pd.Timestamp.now()),
                    'cross_border': row.get('cross_border_flag', 0)
                }
            ))
        
        self.G.add_edges_from(edges)
        logger.info(f"Graph built with {self.G.number_of_nodes()} nodes and {self.G.number_of_edges()} edges.")
        
    def compute_centrality_features(self):
        """Calculates standard network centralities."""
        logger.info("Computing degree centrality and PageRank...")
        
        # In/Out Degree (Weighted by volume)
        in_degree = self.G.in_degree(weight='amount')
        out_degree = self.G.out_degree(weight='amount')
        
        # PageRank (on a simplified DiGraph since PR doesn't fully support MultiDiGraph weights cleanly)
        simple_G = nx.DiGraph()
        for u, v, data in self.G.edges(data=True):
            if simple_G.has_edge(u, v):
                simple_G[u][v]['weight'] += data.get('amount', 0)
            else:
                simple_G.add_edge(u, v, weight=data.get('amount', 0))
                
        pagerank = nx.pagerank(simple_G, weight='weight', alpha=0.85)
        
        for node in self.G.nodes():
            if node in self.node_features:
                self.node_features[node]['in_volume'] = in_degree[node] if node in in_degree else 0
                self.node_features[node]['out_volume'] = out_degree[node] if node in out_degree else 0
                
                in_v = self.node_features[node]['in_volume']
                out_v = self.node_features[node]['out_volume']
                self.node_features[node]['flow_ratio'] = out_v / (in_v + 1e-5)
                self.node_features[node]['pagerank'] = pagerank.get(node, 0)
                
    def compute_asymmetry_index(self):
        """Measures Directed Flow Asymmetry (DFA) for all nodes."""
        logger.info("Computing Directed Flow Asymmetry (DFA)...")
        for node in self.G.nodes():
            in_vol = self.node_features[node].get('in_volume', 0)
            out_vol = self.node_features[node].get('out_volume', 0)
            
            if in_vol + out_vol == 0:
                dfa = 0.0
            else:
                dfa = abs(out_vol - in_vol) / (out_vol + in_vol + 1e-5)
            self.node_features[node]['dfa_score'] = dfa
            
    def compute_hawkes_intensity(self, mu=0.01, alpha=0.5, beta=1.0):
        """Estimates the Hawkes process conditional intensity for temporal clustering."""
        logger.info("Computing Hawkes Process Intensities...")
        for node in self.G.nodes():
            # Get all timestamps for node
            in_edges = self.G.in_edges(node, data='timestamp')
            out_edges = self.G.out_edges(node, data='timestamp')
            
            times = []
            for _, _, ts in list(in_edges) + list(out_edges):
                if pd.notna(ts):
                    times.append(ts)
                    
            if not times:
                self.node_features[node]['hawkes_intensity'] = 0.0
                continue
                
            times = sorted(times)
            t_eval = times[-1]
            times_sec = np.array([(t_eval - t).total_seconds() / 3600.0 for t in times[:-1]]) # hours
            
            # Decay sum: alpha * sum(exp(-beta * time_diff))
            decay_sum = np.sum(np.exp(-beta * times_sec))
            intensity = mu + alpha * decay_sum
            
            self.node_features[node]['hawkes_intensity'] = intensity
            
    def compute_threshold_proximity(self, threshold=1_000_000, tolerance=0.10):
        """Calculates Threshold Proximity Score (TPS) for structuring evasion."""
        logger.info("Computing Threshold Proximity Score (TPS)...")
        lower_bound = threshold * (1.0 - tolerance)
        
        for node in self.G.nodes():
            out_edges = self.G.out_edges(node, data='amount')
            out_count = 0
            structuring_count = 0
            
            for _, _, amt in out_edges:
                out_count += 1
                if lower_bound <= amt < threshold:
                    structuring_count += 1
                    
            tps = (structuring_count / out_count) if out_count > 0 else 0.0
            self.node_features[node]['tps_score'] = tps
    def detect_communities_leiden(self):
        """Applies Leiden hierarchical partitioning to detect communities."""
        logger.info("Applying Leiden community detection...")
        # Leiden requires simple undirected graph via igraph or cdlib
        simple_G = nx.Graph(self.G) 
        try:
            communities = algorithms.leiden(simple_G)
            for idx, comm in enumerate(communities.communities):
                for node in comm:
                    self.community_map[node] = idx
                    if node in self.node_features:
                        self.node_features[node]['community_id'] = idx
        except Exception as e:
            logger.error(f"Leiden algorithm failed, defaulting to 0: {e}")
            for node in self.G.nodes():
                self.node_features[node]['community_id'] = 0
                
    def compute_community_risk_indices(self):
        """Calculates risk density indices for each community."""
        logger.info("Computing community risk indices...")
        comm_stats = {}
        
        for u, v, data in self.G.edges(data=True):
            cu = self.community_map.get(u, -1)
            is_cb = data.get('cross_border', 0)
            if cu not in comm_stats:
                comm_stats[cu] = {'tx_count': 0, 'cb_count': 0}
            
            comm_stats[cu]['tx_count'] += 1
            if is_cb:
                comm_stats[cu]['cb_count'] += 1
                
        # Assign community risk scores back to nodes
        for node in self.G.nodes():
            cu = self.community_map.get(node, -1)
            if cu in comm_stats and comm_stats[cu]['tx_count'] > 0:
                cb_ratio = comm_stats[cu]['cb_count'] / comm_stats[cu]['tx_count']
            else:
                cb_ratio = 0.0
            self.node_features[node]['comm_cb_ratio'] = cb_ratio
    def compute_structural_holes(self):
        """Computes Burt's constraint index for structural hole exploitation."""
        logger.info("Computing structural hole constraint...")
        # Constraint index is computationally heavy, use simple graph
        simple_G = nx.DiGraph(self.G)
        try:
            constraint = nx.constraint(simple_G)
            for node, val in constraint.items():
                if node in self.node_features:
                    self.node_features[node]['structural_constraint'] = val if not pd.isna(val) else 1.0
        except Exception as e:
            logger.error(f"Failed to compute structural holes: {e}")
    def build_node_feature_matrix(self) -> pd.DataFrame:
        """Compiles all calculated features into a unified DataFrame."""
        logger.info("Building unified node feature matrix...")
        df = pd.DataFrame.from_dict(self.node_features, orient='index')
        df.reset_index(drop=True, inplace=True)
        # Fill missing values with 0
        df.fillna(0, inplace=True)
        return df
        
    def export_features(self, df: pd.DataFrame, filename: str = "node_features.csv"):
        """Saves the node feature matrix to the processed data directory."""
        path = PROCESSED_DATA_DIR / filename
        df.to_csv(path, index=False)
        logger.info(f"Exported node features to {path}")