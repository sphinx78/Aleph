"""
AMLIOS-X Graph Engine Module

Handles:
- Building continuous-time directed heterogeneous multigraph from transaction data
- Legitimate entity whitelisting to reduce false positives
- Computing structural centrality metrics (PageRank, degree)
- Directed Flow Asymmetry (DFA) calculation
- Hawkes Process intensity scoring
- Threshold Proximity Score (TPS) for structuring detection
- Structural hole exploitation scoring (Burt's constraint)
- Leiden and SCAN community detection
- Topological Data Analysis (TDA) via Persistence Homology (Betti-0 barcodes)
- Temporal Motif Mining (triangles, cycles, fan-in/fan-out stars)
- Exporting the unified node feature matrix
"""

import networkx as nx
import pandas as pd
import numpy as np
import scipy.sparse as sp
from collections import defaultdict
from src.utils import setup_logger, PROCESSED_DATA_DIR

logger = setup_logger()

# Try importing cdlib for Leiden
try:
    import cdlib
    from cdlib import algorithms
    HAS_CDLIB = True
except ImportError:
    HAS_CDLIB = False


class ContinuousTimeGraphEngine:
    """
    Constructs and analyzes the heterogeneous temporal transaction network
    to extract structural, community, topological, and motif-based features.
    """
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self.node_features = {}
        self.community_map = {}
        self.scan_community_map = {}
        self.whitelist = set()
        
    def build_multigraph(self, tx_df: pd.DataFrame, accounts_df: pd.DataFrame):
        """
        Builds a continuous-time directed heterogeneous multigraph.
        Models Accounts, Customers, Banks, Branches, and Countries.
        """
        logger.info("Building heterogeneous temporal multigraph from transactions...")
        
        # 1. Populate Account & Customer nodes
        for _, row in accounts_df.iterrows():
            acc_id = str(row['account_id'])
            name = str(row.get('name', ''))
            cust_id = f"cust_{name.replace(' ', '_')}" if name else f"cust_{acc_id}"
            branch_id = str(row.get('branch', 'UNKNOWN_BRANCH'))
            bank_id = str(row.get('institution', 'UNKNOWN_BANK'))
            
            # Account node
            self.G.add_node(
                acc_id,
                type='Account',
                risk_grade=row.get('risk_grade', 'UNKNOWN'),
                acct_type=row.get('acct_type', 'UNKNOWN'),
                pep_flag=int(row.get('pep_flag', 0)),
                sanctions_hit=int(row.get('sanctions_hit', 0))
            )
            
            # Customer node
            self.G.add_node(
                cust_id,
                type='Customer',
                name=name,
                is_person=row.get('is_person', True)
            )
            
            # Link Customer to Account (OWNS)
            self.G.add_edge(cust_id, acc_id, relation='OWNS')
            
            # Link Account to Branch
            self.G.add_node(branch_id, type='Branch')
            self.G.add_edge(acc_id, branch_id, relation='LOCATED_IN')
            
            # Link Branch to Bank
            self.G.add_node(bank_id, type='Bank')
            self.G.add_edge(branch_id, bank_id, relation='LOCATED_IN')
            
            self.node_features[acc_id] = {'account_id': acc_id}
            
        # Ensure timestamp sorting
        tx_df = tx_df.copy()
        if 'Date' in tx_df.columns and 'Time' in tx_df.columns:
            tx_df['datetime'] = pd.to_datetime(tx_df['Date'].astype(str) + ' ' + tx_df['Time'].astype(str))
        elif 'datetime' not in tx_df.columns:
            tx_df['datetime'] = pd.Timestamp.now()
            logger.warning("No datetime field found, using current timestamp.")
            
        # 2. Whitelisting Heuristic
        self._apply_whitelisting(tx_df, accounts_df)
        
        # 3. Populate SENDS transaction relationships
        edges = []
        for _, row in tx_df.iterrows():
            sender = str(row['Sender_account'])
            receiver = str(row['Receiver_account'])
            amount = float(row.get('amount_local_npr', row.get('Amount', 0.0)))
            ts = row.get('datetime', pd.Timestamp.now())
            cb = int(row.get('cross_border_flag', 0))
            
            # Check receiver/sender countries
            sender_country = str(row.get('Sender_bank_location', 'NP'))
            receiver_country = str(row.get('Receiver_bank_location', 'NP'))
            
            self.G.add_node(sender_country, type='Country')
            self.G.add_node(receiver_country, type='Country')
            
            # Link Banks to Countries
            sender_bank = str(row.get('sender_institution', 'UNKNOWN_BANK'))
            receiver_bank = str(row.get('receiver_institution', 'UNKNOWN_BANK'))
            self.G.add_edge(sender_bank, sender_country, relation='LOCATED_IN')
            self.G.add_edge(receiver_bank, receiver_country, relation='LOCATED_IN')
            
            # Account-to-Account transactional edge
            edges.append((
                sender,
                receiver,
                {
                    'relation': 'SENDS',
                    'amount': amount,
                    'timestamp': ts,
                    'cross_border': cb
                }
            ))
            
        self.G.add_edges_from(edges)
        logger.info(f"Heterogeneous graph built with {self.G.number_of_nodes()} nodes and {self.G.number_of_edges()} edges.")

    def _apply_whitelisting(self, tx_df: pd.DataFrame, accounts_df: pd.DataFrame):
        """Flags large-scale verified low-risk nodes to reduce false positive alerts."""
        logger.info("Applying legitimate entity whitelisting filters...")
        
        # Heuristic 1: Large corporate/governmental keyword names
        for _, row in accounts_df.iterrows():
            name = str(row.get('name', '')).upper()
            acc_id = str(row['account_id'])
            if any(keyword in name for keyword in ["GOVERNMENT", "TAX", "TELECOM", "UTILITY", "CLEARINGHOUSE", "MINISTRY", "MUNICIPALITY", "REVENUE", "HOSPITAL", "UNIVERSITY"]):
                self.whitelist.add(acc_id)
                
        # Heuristic 2: Out-degree / In-degree volume profile
        in_counts = tx_df.groupby('Receiver_account').size()
        high_freq_receivers = in_counts[in_counts > 100].index.astype(str)
        for node in high_freq_receivers:
            self.whitelist.add(node)
            
        logger.info(f"Whitelisted {len(self.whitelist)} legitimate low-risk accounts.")

    def compute_centrality_features(self):
        """Calculates network centralities (in-degree, out-degree, PageRank)."""
        logger.info("Computing degree centrality and PageRank...")
        
        in_degree = defaultdict(float)
        out_degree = defaultdict(float)
        
        # Calculate weighted volumes on SENDS edges
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS':
                amt = data.get('amount', 0.0)
                out_degree[u] += amt
                in_degree[v] += amt
                
        # PageRank on SENDS edges
        simple_G = nx.DiGraph()
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS':
                amt = data.get('amount', 0.0)
                if simple_G.has_edge(u, v):
                    simple_G[u][v]['weight'] += amt
                else:
                    simple_G.add_edge(u, v, weight=amt)
                    
        pagerank = nx.pagerank(simple_G, weight='weight', alpha=0.85) if simple_G.number_of_nodes() > 0 else {}
        
        for node in self.G.nodes():
            if self.G.nodes[node].get('type') == 'Account':
                if node not in self.node_features:
                    self.node_features[node] = {'account_id': node}
                self.node_features[node]['in_volume'] = in_degree[node]
                self.node_features[node]['out_volume'] = out_degree[node]
                
                in_v = in_degree[node]
                out_v = out_degree[node]
                self.node_features[node]['flow_ratio'] = out_v / (in_v + 1e-5)
                self.node_features[node]['pagerank'] = pagerank.get(node, 0.0)

    def compute_asymmetry_index(self):
        """Measures Directed Flow Asymmetry (DFA) for all account nodes."""
        logger.info("Computing Directed Flow Asymmetry (DFA)...")
        for node in self.G.nodes():
            if self.G.nodes[node].get('type') == 'Account':
                in_vol = self.node_features[node].get('in_volume', 0.0)
                out_vol = self.node_features[node].get('out_volume', 0.0)
                if in_vol + out_vol == 0:
                    dfa = 0.0
                else:
                    dfa = abs(out_vol - in_vol) / (out_vol + in_vol + 1e-5)
                self.node_features[node]['dfa_score'] = dfa

    def compute_hawkes_intensity(self, mu=0.01, alpha=0.5, beta=1.0):
        """Estimates the Hawkes process conditional intensity for temporal transaction clustering."""
        logger.info("Computing Hawkes Process Intensities...")
        for node in self.G.nodes():
            if self.G.nodes[node].get('type') == 'Account':
                times = []
                for _, _, data in self.G.in_edges(node, data=True):
                    if data.get('relation') == 'SENDS':
                        ts = data.get('timestamp')
                        if pd.notna(ts):
                            times.append(ts)
                for _, _, data in self.G.out_edges(node, data=True):
                    if data.get('relation') == 'SENDS':
                        ts = data.get('timestamp')
                        if pd.notna(ts):
                            times.append(ts)
                            
                if not times:
                    self.node_features[node]['hawkes_intensity'] = 0.0
                    continue
                    
                times = sorted(times)
                t_eval = times[-1]
                times_sec = np.array([(t_eval - t).total_seconds() / 3600.0 for t in times[:-1]]) # in hours
                
                decay_sum = np.sum(np.exp(-beta * times_sec))
                intensity = mu + alpha * decay_sum
                self.node_features[node]['hawkes_intensity'] = intensity

    def compute_threshold_proximity(self, threshold=1_000_000, tolerance=0.10):
        """Calculates Threshold Proximity Score (TPS) to detect structuring evasion."""
        logger.info("Computing Threshold Proximity Score (TPS)...")
        lower_bound = threshold * (1.0 - tolerance)
        
        for node in self.G.nodes():
            if self.G.nodes[node].get('type') == 'Account':
                out_edges = self.G.out_edges(node, data=True)
                out_count = 0
                structuring_count = 0
                
                for _, _, data in out_edges:
                    if data.get('relation') == 'SENDS':
                        out_count += 1
                        amt = data.get('amount', 0.0)
                        if lower_bound <= amt < threshold:
                            structuring_count += 1
                            
                tps = (structuring_count / out_count) if out_count > 0 else 0.0
                self.node_features[node]['tps_score'] = tps

    def detect_communities_leiden(self):
        """Applies Leiden community partitioning to detect dense transaction clusters."""
        logger.info("Applying Leiden community detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        sub_G = nx.Graph()
        sub_G.add_nodes_from(account_nodes)
        
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in sub_G and v in sub_G:
                sub_G.add_edge(u, v)
                
        if not HAS_CDLIB or sub_G.number_of_nodes() == 0:
            logger.warning("cdlib not available or graph empty. Mapping all accounts to community 0.")
            for node in account_nodes:
                self.community_map[node] = 0
                self.node_features[node]['community_id'] = 0
            return
            
        try:
            communities = algorithms.leiden(sub_G)
            for idx, comm in enumerate(communities.communities):
                for node in comm:
                    self.community_map[node] = idx
                    self.node_features[node]['community_id'] = idx
        except Exception as e:
            logger.error(f"Leiden algorithm failed, defaulting to 0: {e}")
            for node in account_nodes:
                self.community_map[node] = 0
                self.node_features[node]['community_id'] = 0

    def detect_communities_scan(self, epsilon=0.6, mu=3):
        """
        Applies SCAN (Structural Clustering Algorithm for Networks) density-based clustering.
        Finds overlapping communities, hubs (bridges), and outliers.
        """
        logger.info("Applying SCAN community detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        sub_G = nx.Graph()
        sub_G.add_nodes_from(account_nodes)
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in sub_G and v in sub_G:
                sub_G.add_edge(u, v)
                
        # Compute structural similarity for all incident node pairs
        def similarity(node1, node2):
            neighbors1 = set(sub_G.neighbors(node1)) | {node1}
            neighbors2 = set(sub_G.neighbors(node2)) | {node2}
            intersection = neighbors1 & neighbors2
            return len(intersection) / np.sqrt(len(neighbors1) * len(neighbors2) + 1e-9)
            
        cores = set()
        eps_neighbors = defaultdict(list)
        
        for u in sub_G.nodes():
            neighbors_u = list(sub_G.neighbors(u)) + [u]
            for v in neighbors_u:
                if similarity(u, v) >= epsilon:
                    eps_neighbors[u].append(v)
            if len(eps_neighbors[u]) >= mu:
                cores.add(u)
                
        clusters = []
        unclassified = set(sub_G.nodes())
        
        for core in cores:
            if core in unclassified:
                cluster = [core]
                unclassified.remove(core)
                queue = [core]
                while queue:
                    curr = queue.pop(0)
                    for neighbor in eps_neighbors[curr]:
                        if neighbor in unclassified:
                            unclassified.remove(neighbor)
                            cluster.append(neighbor)
                            if neighbor in cores:
                                queue.append(neighbor)
                        elif any(neighbor in c for c in clusters):
                            cluster.append(neighbor)
                clusters.append(cluster)
                
        node_to_cluster = {}
        for idx, cluster in enumerate(clusters):
            for node in cluster:
                node_to_cluster[node] = idx
                
        for node in unclassified:
            adj_clusters = set()
            for neighbor in sub_G.neighbors(node):
                if neighbor in node_to_cluster:
                    adj_clusters.add(node_to_cluster[neighbor])
            if len(adj_clusters) >= 2:
                self.scan_community_map[node] = -2  # HUB
            else:
                self.scan_community_map[node] = -1  # OUTLIER
                
        for node in account_nodes:
            c_val = node_to_cluster.get(node, self.scan_community_map.get(node, -1))
            self.scan_community_map[node] = c_val
            self.node_features[node]['scan_cluster'] = c_val

    def compute_community_risk_indices(self):
        """Calculates risk density indices for communities based on cross-border ratios."""
        logger.info("Computing community risk indices...")
        comm_stats = {}
        
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS':
                cu = self.community_map.get(u, -1)
                is_cb = data.get('cross_border', 0)
                if cu not in comm_stats:
                    comm_stats[cu] = {'tx_count': 0, 'cb_count': 0}
                comm_stats[cu]['tx_count'] += 1
                if is_cb:
                    comm_stats[cu]['cb_count'] += 1
                    
        for node in self.G.nodes():
            if self.G.nodes[node].get('type') == 'Account':
                cu = self.community_map.get(node, -1)
                if cu in comm_stats and comm_stats[cu]['tx_count'] > 0:
                    cb_ratio = comm_stats[cu]['cb_count'] / comm_stats[cu]['tx_count']
                else:
                    cb_ratio = 0.0
                self.node_features[node]['comm_cb_ratio'] = cb_ratio

    def compute_structural_holes(self):
        """Computes Burt's constraint index for structural hole exploitation."""
        logger.info("Computing structural hole constraint...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        sub_G = nx.DiGraph()
        sub_G.add_nodes_from(account_nodes)
        
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in sub_G and v in sub_G:
                sub_G.add_edge(u, v)
                
        try:
            constraint = nx.constraint(sub_G)
            for node, val in constraint.items():
                if node in self.node_features:
                    self.node_features[node]['structural_constraint'] = val if not pd.isna(val) else 1.0
        except Exception as e:
            logger.error(f"Failed to compute structural holes: {e}")
            for node in account_nodes:
                self.node_features[node]['structural_constraint'] = 1.0

    def compute_persistence_homology(self, steps=10):
        """
        Computes Topological Data Analysis (TDA) filtration using transaction thresholds.
        Evaluates Betti-0 persistence barcodes of clusters over time.
        Optimized using pandas dataframe edgelists.
        """
        logger.info("Computing Persistence Homology (Betti-0 barcodes)...")
        account_nodes = set([n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account'])
        
        # Gather all transaction amounts
        sends_edges = []
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in account_nodes and v in account_nodes:
                amt = data.get('amount', 0.0)
                sends_edges.append((u, v, amt))
                
        if not sends_edges:
            logger.warning("No transactions found, skipping persistence homology.")
            for node in account_nodes:
                self.node_features[node]['betti_birth'] = 0.0
                self.node_features[node]['betti_death'] = 0.0
                self.node_features[node]['betti_persistence'] = 0.0
            return
            
        sends_df = pd.DataFrame(sends_edges, columns=['u', 'v', 'amt'])
        amounts = sends_df['amt'].values
        thresholds = np.linspace(np.percentile(amounts, 10), np.percentile(amounts, 98), steps)
        
        # Track active components at each threshold
        birth_records = {}
        death_records = {}
        
        for t_idx, threshold in enumerate(thresholds):
            filtered_df = sends_df[sends_df['amt'] >= threshold]
            
            temp_G = nx.from_pandas_edgelist(filtered_df, source='u', target='v')
            # Add missing singleton nodes
            missing_nodes = account_nodes - set(temp_G.nodes())
            temp_G.add_nodes_from(missing_nodes)
            
            components = list(nx.connected_components(temp_G))
            for comp in components:
                comp_key = tuple(sorted(list(comp)))
                if comp_key not in birth_records:
                    birth_records[comp_key] = threshold
                death_records[comp_key] = threshold
                
        node_persistence = defaultdict(list)
        for comp_key, birth in birth_records.items():
            death = death_records[comp_key]
            persistence = death - birth
            for node in comp_key:
                node_persistence[node].append((birth, death, persistence))
                
        for node in account_nodes:
            records = node_persistence.get(node, [])
            if records:
                best_birth, best_death, best_persist = max(records, key=lambda x: x[2])
                self.node_features[node]['betti_birth'] = best_birth
                self.node_features[node]['betti_death'] = best_death
                self.node_features[node]['betti_persistence'] = best_persist
            else:
                self.node_features[node]['betti_birth'] = 0.0
                self.node_features[node]['betti_death'] = 0.0
                self.node_features[node]['betti_persistence'] = 0.0

    def compute_temporal_motifs(self, window_hours=24):
        """
        Performs temporal graphlet discovery for 3-node and 4-node motifs.
        Computes triangle, cycle, fan-in, and fan-out counts per account node.
        Optimized version utilizing local neighborhood index and binary search.
        """
        logger.info(f"Computing temporal motifs (sliding window {window_hours} hours)...")
        account_nodes = set([n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account'])
        
        # Build adjacency maps of SENDS edges
        adj_out = defaultdict(list)
        adj_in = defaultdict(list)
        edge_timestamps = defaultdict(list)
        
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in account_nodes and v in account_nodes:
                ts = data.get('timestamp')
                if pd.notna(ts):
                    adj_out[u].append((v, ts))
                    adj_in[v].append((u, ts))
                    edge_timestamps[(u, v)].append(ts)
                    
        # Sort adjacency lists and edge timestamps
        for node in adj_out:
            adj_out[node].sort(key=lambda x: x[1])
        for node in adj_in:
            adj_in[node].sort(key=lambda x: x[1])
        for pair in edge_timestamps:
            edge_timestamps[pair].sort()
            
        import bisect
        def count_edges_in_range(src, dest, t_low, t_high):
            ts_list = edge_timestamps.get((src, dest), [])
            if not ts_list:
                return 0
            idx_low = bisect.bisect_right(ts_list, t_low)
            idx_high = bisect.bisect_right(ts_list, t_high)
            return idx_high - idx_low

        motif_triangles = defaultdict(int)
        motif_cycles = defaultdict(int)
        motif_fanout = defaultdict(int)
        motif_fanin = defaultdict(int)
        
        window_sec = window_hours * 3600.0
        
        # 1. Compute Fan-out & Fan-in stars using sliding window per node
        for node in account_nodes:
            # Fan-out
            out_list = adj_out[node]
            for idx, (v, t1) in enumerate(out_list):
                for j in range(idx + 1, min(idx + 101, len(out_list))): # Cap lookahead at 100 for safety
                    v2, t2 = out_list[j]
                    if (t2 - t1).total_seconds() > window_sec:
                        break
                    if v != v2:
                        motif_fanout[node] += 1
                        motif_fanout[v] += 1
                        motif_fanout[v2] += 1
                        
            # Fan-in
            in_list = adj_in[node]
            for idx, (u, t1) in enumerate(in_list):
                for j in range(idx + 1, min(idx + 101, len(in_list))):
                    u2, t2 = in_list[j]
                    if (t2 - t1).total_seconds() > window_sec:
                        break
                    if u != u2:
                        motif_fanin[node] += 1
                        motif_fanin[u] += 1
                        motif_fanin[u2] += 1
                        
        # 2. Compute Temporal Triangles and Cycles
        for u in account_nodes:
            out_list = adj_out[u]
            for v, t1 in out_list:
                for w, t2 in adj_out[v]:
                    delta_t = (t2 - t1).total_seconds()
                    if 0 < delta_t <= window_sec and u != w:
                        t_high = t1 + pd.Timedelta(seconds=window_sec)
                        tri_count = count_edges_in_range(u, w, t2, t_high)
                        if tri_count > 0:
                            motif_triangles[u] += tri_count
                            motif_triangles[v] += tri_count
                            motif_triangles[w] += tri_count
                            
                        cyc_count = count_edges_in_range(w, u, t2, t_high)
                        if cyc_count > 0:
                            motif_cycles[u] += cyc_count
                            motif_cycles[v] += cyc_count
                            motif_cycles[w] += cyc_count
                            
        for node in account_nodes:
            self.node_features[node]['motif_triangle'] = motif_triangles[node]
            self.node_features[node]['motif_cycle'] = motif_cycles[node]
            self.node_features[node]['motif_fanout'] = motif_fanout[node]
            self.node_features[node]['motif_fanin'] = motif_fanin[node]

    def build_node_feature_matrix(self) -> pd.DataFrame:
        """Compiles all calculated features into a unified DataFrame."""
        logger.info("Building unified node feature matrix...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        filtered_features = {k: v for k, v in self.node_features.items() if k in account_nodes}
        df = pd.DataFrame.from_dict(filtered_features, orient='index')
        df.reset_index(drop=True, inplace=True)
        df.fillna(0, inplace=True)
        return df
        
    def export_features(self, df: pd.DataFrame, filename: str = "node_features.csv"):
        """Saves the node feature matrix to the processed data directory."""
        path = PROCESSED_DATA_DIR / filename
        df.to_csv(path, index=False)
        logger.info(f"Exported node features to {path}")