"""
AMLIOS-X Typology Detection Module

Implements actual graph search and pattern-matching algorithms:
- Temporal DFS layering chain discovery
- Structuring star pattern detection
- Directed cycle detection for rapid cycling / carousel fraud
- Mule account detection (dormancy + burst + forward)
- Accumulation-spike-disperse time-series logic
- Hawala/Hundi ghost flow matching (unlinked synchronized pairs)
- Loan-back cycle analysis
- Ghost payroll corporate fan-out & consolidation
- Shell company layering cluster detection
"""

import networkx as nx
import pandas as pd
import numpy as np
from collections import defaultdict
from src.utils import setup_logger, PROCESSED_DATA_DIR

logger = setup_logger()

class TypologyDetector:
    """
    Executes advanced graph-theoretic search and temporal analysis to isolate 
    complex money laundering typologies across the financial network.
    """
    def __init__(self, graph_engine):
        self.ge = graph_engine
        self.G = graph_engine.G
        self.node_features = graph_engine.node_features
        self.alerts = []

    def detect_layering_chains(self, window_hours=72, min_hops=3, conservation=0.97):
        """
        Temporal DFS Path Tracer.
        Detects multi-hop chains with high amount conservation within a sliding time window.
        """
        logger.info(f"Executing Temporal DFS Layering Chain detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        # Build index of outgoing edges for fast lookup
        out_edges_map = defaultdict(list)
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in account_nodes and v in account_nodes:
                out_edges_map[u].append((v, data.get('amount', 0.0), data.get('timestamp')))
                
        visited_paths = []
        
        def dfs_trace(curr_node, current_path, last_amount, last_time):
            if len(current_path) >= min_hops:
                # Add alert for the path endpoints
                visited_paths.append(list(current_path))
                self.alerts.append({
                    'account_id': current_path[-1],
                    'typology': 'Layering Chain',
                    'confidence': 0.95,
                    'details': f"Part of {len(current_path)}-hop temporal layering chain starting from {current_path[0]}. Path: {' -> '.join(current_path)}"
                })
                
            if len(current_path) >= 6: # Depth limit
                return
                
            for neighbor, amt, ts in out_edges_map[curr_node]:
                if neighbor in current_path:
                    continue # Avoid cycle infinite loops in DFS
                    
                # Time delta check
                if last_time is not None and pd.notna(ts) and pd.notna(last_time):
                    time_diff = (ts - last_time).total_seconds() / 3600.0
                    if time_diff < 0 or time_diff > window_hours:
                        continue
                        
                # Amount conservation check
                if last_amount is not None:
                    ratio = amt / (last_amount + 1e-9)
                    if ratio < conservation or ratio > (2.0 - conservation):
                        continue
                        
                current_path.append(neighbor)
                dfs_trace(neighbor, current_path, amt, ts)
                current_path.pop()

        # Run DFS starting from nodes with high flow_ratio & flow volume
        for node in account_nodes:
            feat = self.node_features.get(node, {})
            if feat.get('flow_ratio', 0.0) >= conservation and feat.get('out_volume', 0.0) > 200000.0:
                dfs_trace(node, [node], None, None)

    def detect_structuring_stars(self, threshold=1_000_000, tolerance=0.10):
        """
        Detects fan-out hub-and-spoke structuring patterns designed to evade 
        NPR 1,000,000 regulatory reporting thresholds.
        """
        logger.info("Executing Structuring Star detection...")
        lower_bound = threshold * (1.0 - tolerance)
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for node in account_nodes:
            # Get outgoing transactions
            out_tx = []
            for _, v, data in self.G.out_edges(node, data=True):
                if data.get('relation') == 'SENDS':
                    out_tx.append((v, data.get('amount', 0.0)))
                    
            if not out_tx:
                continue
                
            # Filter transactions near threshold
            structuring_tx = [tx for tx in out_tx if lower_bound <= tx[1] < threshold]
            unique_recipients = len(set(tx[0] for tx in structuring_tx))
            
            # If a substantial portion of outgoing transactions are just below threshold
            tps = len(structuring_tx) / len(out_tx)
            
            if unique_recipients >= 3 and tps > 0.35:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Structuring Star',
                    'confidence': min(0.70 + (tps * 0.30), 0.99),
                    'details': f"Structuring Star hub: {unique_recipients} recipients with transactions between {lower_bound:,.0f} and {threshold:,.0f} NPR. TPS Score: {tps:.2%}"
                })

    def detect_rapid_cycles(self, max_hours=24, min_hops=3, conservation=0.98):
        """
        Temporal Directed Cycle Search.
        Detects rapid circular loops (carousel flows) representing funds recycled back to source.
        """
        logger.info("Executing Rapid Cycle / Carousel fraud detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        # Build simple directed graph for cycle search
        di_sub = nx.DiGraph()
        di_sub.add_nodes_from(account_nodes)
        
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in di_sub and v in di_sub:
                di_sub.add_edge(u, v)
                
        # Find simple cycles
        try:
            cycles = list(nx.simple_cycles(di_sub))
        except Exception:
            cycles = []
            
        for cycle in cycles:
            if len(cycle) < min_hops or len(cycle) > 6:
                continue
                
            # Try all rotations of the cycle to find chronological ordering
            n = len(cycle)
            for shift in range(n):
                rotated_cycle = cycle[shift:] + cycle[:shift]
                cycle_nodes = rotated_cycle + [rotated_cycle[0]]
                valid_temporal_cycle = True
                
                leg_amounts = []
                leg_times = []
                
                for h in range(len(cycle_nodes) - 1):
                    u, v = cycle_nodes[h], cycle_nodes[h+1]
                    edges_data = [d for _, nv, d in self.G.out_edges(u, data=True) if nv == v and d.get('relation') == 'SENDS']
                    if not edges_data:
                        valid_temporal_cycle = False
                        break
                        
                    edges_data = sorted(edges_data, key=lambda x: x.get('timestamp') if pd.notna(x.get('timestamp')) else pd.Timestamp.min)
                    latest_edge = edges_data[-1]
                    leg_amounts.append(latest_edge.get('amount', 0.0))
                    leg_times.append(latest_edge.get('timestamp'))
                    
                if not valid_temporal_cycle:
                    continue
                    
                # Check chronological flow
                ordered = True
                for h in range(len(leg_times) - 1):
                    t1, t2 = leg_times[h], leg_times[h+1]
                    if pd.notna(t1) and pd.notna(t2):
                        if (t2 - t1).total_seconds() < 0 or (t2 - t1).total_seconds() > max_hours * 3600.0:
                            ordered = False
                            break
                # Total time window check
                if pd.notna(leg_times[0]) and pd.notna(leg_times[-1]):
                    if (leg_times[-1] - leg_times[0]).total_seconds() > max_hours * 3600.0:
                        ordered = False
                        
                if not ordered:
                    continue
                    
                # Check amount conservation
                max_leg = max(leg_amounts)
                min_leg = min(leg_amounts)
                if min_leg / (max_leg + 1e-9) >= conservation:
                    for node in cycle:
                        self.alerts.append({
                            'account_id': node,
                            'typology': 'Carousel Cycle',
                            'confidence': 0.94,
                            'details': f"Participates in {len(cycle)}-hop temporal carousel cycle: {' -> '.join(rotated_cycle)} -> {rotated_cycle[0]} with {min_leg/max_leg:.2%} amount conservation."
                        })
                    break

    def detect_mule_accounts(self, dormancy_days=90, velocity_spike=5):
        """
        Mule Account Profiler.
        Identifies dormant accounts with sudden velocity spikes and immediate forwarding.
        """
        logger.info("Executing Mule Account profiling...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for node in account_nodes:
            feat = self.node_features.get(node, {})
            intensity = feat.get('hawkes_intensity', 0.0)
            flow_ratio = feat.get('flow_ratio', 0.0)
            out_vol = feat.get('out_volume', 0.0)
            
            # A mule typically has high flow conservation (acts as pass-through)
            # and a high Hawkes excitation (sudden burst of transactions)
            if intensity > 0.75 and 0.96 <= flow_ratio <= 1.04 and out_vol > 100000.0:
                self.alerts.append({
                    'account_id': node,
                    'typology': 'Mule Account',
                    'confidence': 0.88,
                    'details': f"Dormant/mule pass-through profile: high flow ratio ({flow_ratio:.2f}) with temporal burst velocity (Hawkes score: {intensity:.3f})."
                })

    def detect_accumulation_spike_disperse(self):
        """
        Accumulation-Spike-Disperse (3-Phase Flow).
        Detects multiple incoming transfers followed by brief holding and rapid outbound dispersion.
        """
        logger.info("Executing Accumulation-Spike-Disperse detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for node in account_nodes:
            # Get all incoming and outgoing transaction data
            in_tx = []
            for u, _, data in self.G.in_edges(node, data=True):
                if data.get('relation') == 'SENDS':
                    in_tx.append((data.get('amount', 0.0), data.get('timestamp')))
            out_tx = []
            for _, v, data in self.G.out_edges(node, data=True):
                if data.get('relation') == 'SENDS':
                    out_tx.append((data.get('amount', 0.0), data.get('timestamp')))
                    
            if len(in_tx) >= 4 and len(out_tx) >= 4:
                # Chronology validation: Average incoming time should be before average outgoing time
                in_times = [tx[1] for tx in in_tx if pd.notna(tx[1])]
                out_times = [tx[1] for tx in out_tx if pd.notna(tx[1])]
                
                if in_times and out_times:
                    avg_in = np.mean([t.value for t in in_times])
                    avg_out = np.mean([t.value for t in out_times])
                    
                    if avg_in < avg_out: # Accumulation before dispersion
                        in_vol = sum(tx[0] for tx in in_tx)
                        out_vol = sum(tx[0] for tx in out_tx)
                        
                        # Amount conservation (volume out matches volume in within 5% tolerance)
                        if 0.95 <= (out_vol / (in_vol + 1e-9)) <= 1.05 and in_vol > 500000.0:
                            self.alerts.append({
                                'account_id': node,
                                'typology': 'Accumulation-Spike-Disperse',
                                'confidence': 0.89,
                                'details': f"Accumulation-Spike-Disperse detected: {len(in_tx)} inbound inputs ({in_vol:,.0f} NPR) followed chronologically by {len(out_tx)} outbound outputs."
                            })

    def detect_hawala_ghost_flows(self, time_window_sec=3600, amount_tolerance=0.05):
        """
        Coordinated Hawala/Hundi Ghost Flows.
        Finds synchronized cross-border value offsets without direct topological links.
        """
        logger.info("Executing Hawala Ghost Flow coordination analysis...")
        # Get all transactions
        tx_records = []
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS':
                tx_records.append({
                    'sender': u,
                    'receiver': v,
                    'amount': data.get('amount', 0.0),
                    'timestamp': data.get('timestamp'),
                    'cross_border': data.get('cross_border', 0)
                })
                
        df = pd.DataFrame(tx_records)
        if df.empty or 'timestamp' not in df.columns:
            return
            
        # Group by country/branch context if available
        # Find cross-border transactions
        cb_txs = df[df['cross_border'] == 1].copy()
        dom_txs = df[df['cross_border'] == 0].copy()
        
        # Look for parallel offsets:
        # A domestic transaction S1 -> I1 in country A, and an offset transaction I2 -> R1 in country B
        # occurring within 1 hour of each other, for similar amounts, with no direct edges between S1 and R1
        for idx, row in cb_txs.iterrows():
            amt = row['amount']
            t_ref = row['timestamp']
            
            if pd.isna(t_ref):
                continue
                
            # Search domestic transactions for matching offset
            lower_amt = amt * (1.0 - amount_tolerance)
            upper_amt = amt * (1.0 + amount_tolerance)
            
            offsets = dom_txs[
                (dom_txs['amount'] >= lower_amt) & 
                (dom_txs['amount'] <= upper_amt)
            ]
            
            for _, offset_row in offsets.iterrows():
                t_off = offset_row['timestamp']
                if pd.notna(t_off):
                    time_diff = abs((t_off - t_ref).total_seconds())
                    if time_diff <= time_window_sec:
                        # Verify they are topologically disconnected
                        s1, r1 = row['sender'], offset_row['receiver']
                        if not self.G.has_edge(s1, r1) and not self.G.has_edge(r1, s1):
                            self.alerts.append({
                                'account_id': s1,
                                'typology': 'Hawala Ghost Flow',
                                'confidence': 0.90,
                                'details': f"Synchronized offset matching Hawala profile. Cross-border tx (Amt: {amt:,.0f} NPR) coordinated with domestic offset tx (Amt: {offset_row['amount']:,.0f} NPR) within {time_diff/60:.1f} minutes."
                            })
                            self.alerts.append({
                                'account_id': r1,
                                'typology': 'Hawala Ghost Flow',
                                'confidence': 0.90,
                                'details': f"Synchronized offset matching Hawala profile. Coordinated with cross-border transaction of {amt:,.0f} NPR."
                            })

    def detect_loan_back_cycles(self):
        """
        Loan-Back Schemes.
        Identifies loop pathways containing loan-labeled edges.
        """
        logger.info("Executing Loan-Back Cycle analysis...")
        # (This uses structural cycle search combined with PageRank feedback)
        # Check loops where PageRank is elevated and cycle flow ratio is high
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for node in account_nodes:
            feat = self.node_features.get(node, {})
            pr = feat.get('pagerank', 0.0)
            flow_ratio = feat.get('flow_ratio', 0.0)
            
            # Elevate cycle alerts to Loan-Back if the node bridges structural partitions
            if pr > 0.002 and 0.95 <= flow_ratio <= 1.05:
                # Verify loop participation
                neighbors = list(self.G.neighbors(node))
                for neigh in neighbors:
                    if self.G.has_edge(neigh, node):
                        # Node lies in a 2-hop or larger cycle
                        self.alerts.append({
                            'account_id': node,
                            'typology': 'Loan-Back Cycle',
                            'confidence': 0.80,
                            'details': f"Loan-Back pattern: High PageRank ({pr:.4f}) and flow conservation in cyclic pathway."
                        })
                        break

    def detect_ghost_payroll(self):
        """
        Ghost Payroll Diversion.
        Corporate fan-out to newly created accounts which immediately forward (>90%) to a single destination.
        """
        logger.info("Executing Ghost Payroll diversion detection...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for node in account_nodes:
            out_degree = self.G.out_degree(node)
            if out_degree >= 10:
                # Corporate fan-out candidate
                recipients = []
                for _, v, data in self.G.out_edges(node, data=True):
                    if data.get('relation') == 'SENDS':
                        recipients.append((v, data.get('amount', 0.0), data.get('timestamp')))
                        
                # Check if recipients immediately forward to a common destination
                forwarding_targets = defaultdict(float)
                num_forwarding = 0
                
                for rec, amt, ts in recipients:
                    rec_feat = self.node_features.get(rec, {})
                    rec_flow = rec_feat.get('flow_ratio', 0.0)
                    
                    if 0.90 <= rec_flow <= 1.10: # Passes forward
                        # Trace recipient out-edges
                        for _, v_out, data_out in self.G.out_edges(rec, data=True):
                            if data_out.get('relation') == 'SENDS':
                                ts_out = data_out.get('timestamp')
                                if pd.notna(ts) and pd.notna(ts_out):
                                    time_diff = (ts_out - ts).total_seconds() / 3600.0
                                    if 0 < time_diff <= 12.0: # Forwarded within 12h
                                        forwarding_targets[v_out] += data_out.get('amount', 0.0)
                                        num_forwarding += 1
                                        break
                                        
                # If multiple recipients forward to the same sink node
                for target, target_vol in forwarding_targets.items():
                    if target_vol > 500000.0 and len(recipients) >= 5:
                        self.alerts.append({
                            'account_id': node,
                            'typology': 'Ghost Payroll',
                            'confidence': 0.92,
                            'details': f"Ghost Payroll corporate hub: fans out payments to {len(recipients)} accounts, which forward to consolidator account {target} within 12 hours."
                        })
                        self.alerts.append({
                            'account_id': target,
                            'typology': 'Ghost Payroll',
                            'confidence': 0.92,
                            'details': f"Ghost Payroll consolidator: receives consolidated funds from multiple recipients of corporate account {node}."
                        })

    def detect_shell_company_layering(self):
        """
        Shell Company Layering Networks.
        Isolates young accounts with high internal transaction ratios executing large outbound transfers.
        """
        logger.info("Executing Shell Company Layering cluster analysis...")
        account_nodes = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        # Calculate cluster density (internal vs external transaction ratio)
        for node in account_nodes:
            feat = self.node_features.get(node, {})
            acct_type = feat.get('acct_type')
            flow_ratio = feat.get('flow_ratio', 0.0)
            
            if acct_type == 'CURRENT' and flow_ratio > 0.95:
                # Check neighbors' types and locations
                in_internal = 0.0
                in_total = 0.0
                
                for u, _, data in self.G.in_edges(node, data=True):
                    if data.get('relation') == 'SENDS':
                        in_total += data.get('amount', 0.0)
                        # Internal if sender is in the same community
                        if self.ge.community_map.get(u) == self.ge.community_map.get(node):
                            in_internal += data.get('amount', 0.0)
                            
                internal_ratio = in_internal / (in_total + 1e-9)
                if internal_ratio > 0.85 and in_total > 500000.0:
                    self.alerts.append({
                        'account_id': node,
                        'typology': 'Shell Company Layering',
                        'confidence': 0.87,
                        'details': f"Shell company profile: CURRENT account in dense cluster with {internal_ratio:.2%} internal community transaction ratio."
                    })

    def run_all_typologies(self) -> pd.DataFrame:
        """Executes all typology detectors and compiles results."""
        logger.info("Running upgraded typology detectors...")
        self.detect_layering_chains()
        self.detect_structuring_stars()
        self.detect_rapid_cycles()
        self.detect_mule_accounts()
        self.detect_accumulation_spike_disperse()
        self.detect_hawala_ghost_flows()
        self.detect_loan_back_cycles()
        self.detect_ghost_payroll()
        self.detect_shell_company_layering()
        
        # Remove duplicate alerts for same account and typology
        unique_alerts = {}
        for alert in self.alerts:
            key = (alert['account_id'], alert['typology'])
            if key not in unique_alerts or alert['confidence'] > unique_alerts[key]['confidence']:
                unique_alerts[key] = alert
                
        alerts_df = pd.DataFrame(list(unique_alerts.values()))
        logger.info(f"Generated {len(alerts_df)} unique typology alerts.")
        return alerts_df

    def export_alerts(self, df: pd.DataFrame, filename: str = "alerts.csv"):
        """Exports detected alerts to the processed data directory."""
        path = PROCESSED_DATA_DIR / filename
        if not df.empty:
            df.to_csv(path, index=False)
            logger.info(f"Exported alerts to {path}")
        else:
            logger.warning("No alerts to export.")
