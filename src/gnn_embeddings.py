"""
AMLIOS-X Graph Embeddings Module

Implements:
1. DeepWalk/Node2Vec: Matrix Factorization (NetMF SVD approximation) of transition probabilities.
2. TGAT (Temporal Graph Attention Network): Harmonic time encodings and temporal self-attention in pure NumPy.
3. HAN (Heterogeneous Attention Network): Metapath-based aggregation and semantic attention in pure NumPy/SciPy.
"""

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.linalg import svds
import networkx as nx
from typing import Dict, List, Tuple
from src.utils import setup_logger

logger = setup_logger()

class DynamicGraphEmbeddings:
    """
    Generates advanced structural, temporal (TGAT), and heterogeneous (HAN) 
    embeddings for accounts in the transaction knowledge graph.
    """
    def __init__(self, graph_engine, embedding_dim=16):
        self.ge = graph_engine
        self.G = graph_engine.G
        self.embedding_dim = embedding_dim
        # Get list of accounts
        self.accounts = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        self.node_to_idx = {node: idx for idx, node in enumerate(self.accounts)}
        
    def generate_deepwalk_embeddings(self) -> np.ndarray:
        """
        Approximates DeepWalk/Node2Vec structural embeddings using NetMF matrix factorization.
        Factorizes the log-transition probability matrix via truncated SVD.
        """
        logger.info("Generating DeepWalk/Node2Vec structural embeddings via NetMF...")
        num_nodes = len(self.accounts)
        if num_nodes == 0:
            return np.zeros((0, self.embedding_dim))
            
        # Build adjacency matrix
        row, col, data = [], [], []
        for u, v, val in self.G.edges(data=True):
            if val.get('relation') == 'SENDS' and u in self.node_to_idx and v in self.node_to_idx:
                row.append(self.node_to_idx[u])
                col.append(self.node_to_idx[v])
                data.append(1.0)
                # Undirected approximation
                row.append(self.node_to_idx[v])
                col.append(self.node_to_idx[u])
                data.append(1.0)
                
        if not row:
            # Empty graph fallback
            return np.random.normal(0, 0.1, (num_nodes, self.embedding_dim))
            
        A = sp.coo_matrix((data, (row, col)), shape=(num_nodes, num_nodes)).tocsr()
        
        # Transition matrix P = D^-1 * A
        degrees = np.array(A.sum(axis=1)).flatten()
        degrees_inv = np.divide(1.0, degrees, out=np.zeros_like(degrees), where=degrees != 0)
        D_inv = sp.diags(degrees_inv)
        P = D_inv.dot(A)
        
        # Compute multi-step transition matrix: M = log( (vol / T) * (sum_{r=1}^T P^r) * D^-1 )
        # Using T=3 steps for neighborhood integration
        P_sum = P.copy()
        P_curr = P.copy()
        for _ in range(2):
            P_curr = P_curr.dot(P)
            P_sum += P_curr
            
        vol = float(A.sum())
        T_steps = 3.0
        
        # M matrix
        D_inv_deg = sp.diags(degrees_inv)
        M = P_sum.dot(D_inv_deg) * (vol / T_steps)
        
        # Log representation with thresholding
        M.data = np.log(np.maximum(M.data, 1.0))
        
        # Singular Value Decomposition
        try:
            # We want embedding_dim dimensions
            k = min(self.embedding_dim, num_nodes - 2)
            if k <= 0:
                k = 1
            U, S, Vt = svds(M, k=k)
            # Embedding = U * sqrt(S)
            embeddings = U * np.sqrt(S)
            # Pad if shape is smaller than embedding_dim
            if embeddings.shape[1] < self.embedding_dim:
                padding = np.zeros((num_nodes, self.embedding_dim - embeddings.shape[1]))
                embeddings = np.hstack([embeddings, padding])
        except Exception as e:
            logger.error(f"SVD factorization failed, falling back to random init: {e}")
            embeddings = np.random.normal(0, 0.1, (num_nodes, self.embedding_dim))
            
        return embeddings

    def generate_tgat_embeddings(self) -> np.ndarray:
        """
        Implements Temporal Graph Attention Network (TGAT) forward pass.
        Projects nodes using continuous harmonic time encodings of transaction intervals.
        """
        logger.info("Generating TGAT continuous temporal embeddings...")
        num_nodes = len(self.accounts)
        if num_nodes == 0:
            return np.zeros((0, self.embedding_dim))
            
        # Harmonic time encoding function
        # Phi_d(t) = [cos(w_1 t), sin(w_1 t), ...]
        d = self.embedding_dim
        omega = 1.0 / (10000 ** (np.arange(0, d, 2) / d))
        
        def encode_time(t_diff_hours: float) -> np.ndarray:
            val = t_diff_hours * omega
            return np.hstack([np.cos(val), np.sin(val)])
            
        # Input features for account nodes: degree and PageRank
        features = []
        for acc in self.accounts:
            feat = self.ge.node_features.get(acc, {})
            features.append([
                feat.get('in_volume', 0.0),
                feat.get('out_volume', 0.0),
                feat.get('pagerank', 0.0),
                feat.get('hawkes_intensity', 0.0)
            ])
        X = np.array(features)
        # Standardize features
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
        
        # Project features to half dimension, time encoding to other half
        proj_dim = d // 2
        W_x = np.random.normal(0, 1.0 / np.sqrt(X.shape[1]), (X.shape[1], proj_dim))
        H_x = X.dot(W_x) # Node base projections
        
        # Self-attention weights
        W_q = np.random.normal(0, 0.1, proj_dim)
        W_k = np.random.normal(0, 0.1, proj_dim)
        W_t = np.random.normal(0, 0.1, d) # Time projection
        
        embeddings = np.zeros((num_nodes, d))
        
        for idx, node in enumerate(self.accounts):
            # Find neighbors and transaction times
            neighbors = []
            
            # Incoming transactions
            for u, _, val in self.G.in_edges(node, data=True):
                if val.get('relation') == 'SENDS' and u in self.node_to_idx:
                    neighbors.append((self.node_to_idx[u], val.get('timestamp')))
            # Outgoing transactions
            for _, v, val in self.G.out_edges(node, data=True):
                if val.get('relation') == 'SENDS' and v in self.node_to_idx:
                    neighbors.append((self.node_to_idx[v], val.get('timestamp')))
                    
            if not neighbors:
                # Padding
                embeddings[idx, :proj_dim] = H_x[idx]
                continue
                
            # Compute time differences relative to the last transaction of this node
            times = [n[1] for n in neighbors if pd.notna(n[1])]
            if not times:
                embeddings[idx, :proj_dim] = H_x[idx]
                continue
            t_eval = max(times)
            
            h_neigh_list = []
            att_weights = []
            
            for neigh_idx, t in neighbors:
                if pd.isna(t):
                    t_diff = 0.0
                else:
                    t_diff = (t_eval - t).total_seconds() / 3600.0 # hours
                    
                time_enc = encode_time(t_diff)
                
                # neighbor feature projection
                h_v = H_x[neigh_idx]
                
                # attention energy
                q = H_x[idx].dot(W_q)
                k = h_v.dot(W_k)
                t_score = time_enc.dot(W_t)
                
                energy = q * k + t_score
                att_weights.append(energy)
                
                # neighbor feature concatenated with time representation
                h_neigh_list.append(np.hstack([h_v, time_enc[:proj_dim]]))
                
            # Softmax attention
            att_weights = np.array(att_weights)
            exp_weights = np.exp(att_weights - np.max(att_weights))
            softmax_weights = exp_weights / np.sum(exp_weights)
            
            # Weighted average
            h_neigh_agg = np.zeros(d)
            for w, h_feat in zip(softmax_weights, h_neigh_list):
                h_neigh_agg += w * h_feat
                
            embeddings[idx] = h_neigh_agg
            
        return embeddings

    def generate_han_embeddings(self) -> np.ndarray:
        """
        Implements Heterogeneous Attention Network (HAN) forward pass.
        Aggregates node behaviors across Customer and Branch meta-paths.
        """
        logger.info("Generating HAN metapath-based heterogeneous embeddings...")
        num_nodes = len(self.accounts)
        if num_nodes == 0:
            return np.zeros((0, self.embedding_dim))
            
        # 1. Metapath 1: Account -> Customer -> Account
        # (Accounts sharing the same customer name/profile)
        # 2. Metapath 2: Account -> Branch -> Account
        # (Accounts sharing the same branch)
        
        # Build mapping matrices
        # Node indices for Customers and Branches
        customers = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Customer']
        branches = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Branch']
        
        cust_to_idx = {c: i for i, c in enumerate(customers)}
        branch_to_idx = {b: i for i, b in enumerate(branches)}
        
        # Matrix M_ac: Account-Customer adjacency
        row_ac, col_ac = [], []
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'OWNS':
                # Customer (u) -> Account (v)
                if v in self.node_to_idx and u in cust_to_idx:
                    row_ac.append(self.node_to_idx[v])
                    col_ac.append(cust_to_idx[u])
                    
        # Matrix M_ab: Account-Branch adjacency
        row_ab, col_ab = [], []
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'LOCATED_IN':
                # Account (u) -> Branch (v)
                if u in self.node_to_idx and v in branch_to_idx:
                    row_ab.append(self.node_to_idx[u])
                    col_ab.append(branch_to_idx[v])
                    
        # If mappings are empty, return random initialization
        if not row_ac or not row_ab:
            return np.random.normal(0, 0.1, (num_nodes, self.embedding_dim))
            
        M_ac = sp.coo_matrix((np.ones(len(row_ac)), (row_ac, col_ac)), shape=(num_nodes, len(customers))).tocsr()
        M_ab = sp.coo_matrix((np.ones(len(row_ab)), (row_ab, col_ab)), shape=(num_nodes, len(branches))).tocsr()
        
        # Metapath Adjacencies:
        # Metapath 1: A_cust = M_ac * M_ac^T
        A_cust = M_ac.dot(M_ac.T)
        # Metapath 2: A_branch = M_ab * M_ab^T
        A_branch = M_ab.dot(M_ab.T)
        
        # Standardize metapath transition matrices
        def get_transition_matrix(A_sp):
            degrees = np.array(A_sp.sum(axis=1)).flatten()
            degrees_inv = np.divide(1.0, degrees, out=np.zeros_like(degrees), where=degrees != 0)
            D_inv = sp.diags(degrees_inv)
            return D_inv.dot(A_sp)
            
        P_cust = get_transition_matrix(A_cust)
        P_branch = get_transition_matrix(A_branch)
        
        # Node features matrix X (PageRank, flow ratio, TPS, Hawkes)
        features = []
        for acc in self.accounts:
            feat = self.ge.node_features.get(acc, {})
            features.append([
                feat.get('flow_ratio', 0.0),
                feat.get('tps_score', 0.0),
                feat.get('pagerank', 0.0),
                feat.get('hawkes_intensity', 0.0)
            ])
        X = np.array(features)
        
        # Compute metapath-specific embeddings: Z_path = P_path * X * W
        W_proj = np.random.normal(0, 0.1, (X.shape[1], self.embedding_dim))
        X_proj = X.dot(W_proj)
        
        Z_cust = P_cust.dot(X_proj)
        Z_branch = P_branch.dot(X_proj)
        
        # Semantic Attention
        # Aggregate Z_cust and Z_branch using semantic attention vector q_s
        q_s = np.random.normal(0, 0.1, self.embedding_dim)
        
        # w_cust = mean( tanh( Z_cust * W_s ) * q_s )
        W_s = np.random.normal(0, 0.1, (self.embedding_dim, self.embedding_dim))
        
        w_cust = np.mean(np.tanh(Z_cust.dot(W_s)).dot(q_s))
        w_branch = np.mean(np.tanh(Z_branch.dot(W_s)).dot(q_s))
        
        # Softmax semantic weights
        betas = np.exp([w_cust, w_branch])
        betas = betas / np.sum(betas)
        
        # Combined embedding
        Z_fused = betas[0] * Z_cust + betas[1] * Z_branch
        return Z_fused

    def compute_all_embeddings(self) -> pd.DataFrame:
        """
        Generates DeepWalk, TGAT, and HAN embeddings, compiles them, 
        and returns a unified DataFrame of size (num_accounts, 3 * embedding_dim).
        """
        dw = self.generate_deepwalk_embeddings()
        tgat = self.generate_tgat_embeddings()
        han = self.generate_han_embeddings()
        
        records = []
        for idx, node in enumerate(self.accounts):
            emb_dict = {'account_id': node}
            
            # Save DeepWalk features
            for dim in range(self.embedding_dim):
                emb_dict[f'emb_dw_{dim}'] = dw[idx, dim]
            # Save TGAT features
            for dim in range(self.embedding_dim):
                emb_dict[f'emb_tgat_{dim}'] = tgat[idx, dim]
            # Save HAN features
            for dim in range(self.embedding_dim):
                emb_dict[f'emb_han_{dim}'] = han[idx, dim]
                
            records.append(emb_dict)
            
        return pd.DataFrame(records)
