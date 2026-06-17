"""
AMLIOS-X Risk Fusion & Contagion Propagation Module

Implements:
1. Dempster-Shafer Evidence Fusion combining:
   - XGBoost supervised risk probability
   - GNN/TDA unsupervised graph anomaly score
   - Heuristic typology alert confidence
   - STR narrative verification matrix matches
2. Temporal Risk Contagion Propagation:
   - PageRank-style money flow propagation with temporal distance decay.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import defaultdict
from src.utils import setup_logger

logger = setup_logger()

class RiskFusionEngine:
    """
    Fuses multi-modal risk signals using Dempster-Shafer Theory and
    propagates risk contagion across the transaction network.
    """
    def __init__(self, graph_engine, alpha=0.05, max_iter=5):
        self.ge = graph_engine
        self.G = graph_engine.G
        self.alpha = alpha  # Time decay factor (per hour)
        self.max_iter = max_iter
        
    def dempster_combination(self, m1: Dict[str, float], m2: Dict[str, float]) -> Dict[str, float]:
        """
        Combines two mass functions using Dempster's Rule of Combination.
        Frame of discernment: {'S': Suspicious, 'NS': Not Suspicious, 'Theta': Uncertainty}
        """
        # Calculate conflict K
        K = m1.get('S', 0.0) * m2.get('NS', 0.0) + m1.get('NS', 0.0) * m2.get('S', 0.0)
        if K >= 0.999: # Extreme conflict limit
            return {'S': max(m1.get('S', 0.0), m2.get('S', 0.0)), 'NS': min(m1.get('NS', 0.0), m2.get('NS', 0.0)), 'Theta': 0.0}
            
        scaler = 1.0 / (1.0 - K)
        
        S_new = scaler * (m1.get('S', 0.0) * m2.get('S', 0.0) + 
                          m1.get('S', 0.0) * m2.get('Theta', 0.0) + 
                          m1.get('Theta', 0.0) * m2.get('S', 0.0))
                          
        NS_new = scaler * (m1.get('NS', 0.0) * m2.get('NS', 0.0) + 
                           m1.get('NS', 0.0) * m2.get('Theta', 0.0) + 
                           m1.get('Theta', 0.0) * m2.get('NS', 0.0))
                           
        Theta_new = scaler * (m1.get('Theta', 0.0) * m2.get('Theta', 0.0))
        
        # Normalize to ensure sum to 1.0
        tot = S_new + NS_new + Theta_new
        if tot > 0:
            return {'S': S_new / tot, 'NS': NS_new / tot, 'Theta': Theta_new / tot}
        return {'S': 0.0, 'NS': 1.0, 'Theta': 0.0}

    def fuse_risk_signals(
        self,
        xgb_scores_df: pd.DataFrame,
        typology_alerts_df: pd.DataFrame,
        str_verification_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Performs Dempster-Shafer combination on GNN, XGBoost, Typology, and STR inputs.
        """
        logger.info("Running Dempster-Shafer Risk Fusion on multi-modal evidence...")
        
        # Index all inputs by account_id for fast lookup
        xgb_map = xgb_scores_df.set_index('account_id')['risk_score'].to_dict() if not xgb_scores_df.empty else {}
        
        # Typology confidence map (maximum confidence among alerts for each account)
        typ_map = {}
        if not typology_alerts_df.empty and 'account_id' in typology_alerts_df.columns:
            typ_map = typology_alerts_df.groupby('account_id')['confidence'].max().to_dict()
            
        # STR verification confidence map
        str_map = {}
        if not str_verification_df.empty and 'account_id' in str_verification_df.columns:
            # Group by account and verify if any claim was CONFIRMED
            for acc_id, group in str_verification_df.groupby('account_id'):
                statuses = group['verification_status'].tolist()
                if 'CONFIRMED' in statuses:
                    str_map[str(acc_id)] = 0.95
                elif 'REFUTED' in statuses:
                    str_map[str(acc_id)] = 0.10
                else:
                    str_map[str(acc_id)] = 0.40
                    
        fused_records = []
        accounts = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        for acc in accounts:
            # 1. XGBoost Mass
            p_xgb = float(xgb_map.get(acc, 0.01))
            m_xgb = {
                'S': 0.80 * p_xgb,
                'NS': 0.80 * (1.0 - p_xgb),
                'Theta': 0.20
            }
            
            # 2. GNN Anomaly Mass (approximate using GNN/Hawkes features from graph engine)
            feat = self.ge.node_features.get(acc, {})
            # Hawkes intensity and TDA persistence relative to maximums act as GNN/graph anomaly indicators
            p_gnn = min(feat.get('hawkes_intensity', 0.0) / 5.0, 1.0)
            m_gnn = {
                'S': 0.70 * p_gnn,
                'NS': 0.70 * (1.0 - p_gnn),
                'Theta': 0.30
            }
            
            # 3. Typology Mass
            p_typ = float(typ_map.get(acc, 0.0))
            if p_typ > 0:
                m_typ = {
                    'S': 0.90 * p_typ,
                    'NS': 0.0,
                    'Theta': 1.0 - 0.90 * p_typ
                }
            else:
                m_typ = {'S': 0.0, 'NS': 0.0, 'Theta': 1.0}
                
            # 4. STR Mass
            p_str = float(str_map.get(acc, 0.0))
            if p_str > 0:
                m_str = {
                    'S': p_str,
                    'NS': 0.0,
                    'Theta': 1.0 - p_str
                }
            else:
                m_str = {'S': 0.0, 'NS': 0.0, 'Theta': 1.0}
                
            # Combine sequentially: m_xgb -> m_gnn -> m_typ -> m_str
            m_fused = self.dempster_combination(m_xgb, m_gnn)
            m_fused = self.dempster_combination(m_fused, m_typ)
            m_fused = self.dempster_combination(m_fused, m_str)
            
            fused_records.append({
                'account_id': acc,
                'risk_score_fused': m_fused['S'],
                'plausibility': m_fused['S'] + m_fused['Theta']
            })
            
        return pd.DataFrame(fused_records)

    def propagate_risk_contagion(self, fused_df: pd.DataFrame) -> pd.DataFrame:
        """
        Propagates fused risk scores downstream with chronological distance decay:
        R_prop(v) = R_fused(v) + sum_{u in N_in(v)} R_prop(u) * e^(-alpha * delta_t)
        """
        logger.info("Executing Temporal Risk Contagion Propagation...")
        fused_map = fused_df.set_index('account_id')['risk_score_fused'].to_dict()
        
        # Initialize propagated risk map
        prop_risk = {k: v for k, v in fused_map.items()}
        
        accounts = [n for n in self.G.nodes() if self.G.nodes[n].get('type') == 'Account']
        
        # Construct incoming edge adjacency with temporal intervals
        # in_edges_map[v] = list of (u, amount, timestamp)
        in_edges_map = defaultdict(list)
        for u, v, data in self.G.edges(data=True):
            if data.get('relation') == 'SENDS' and u in prop_risk and v in prop_risk:
                in_edges_map[v].append((u, data.get('amount', 0.0), data.get('timestamp')))
                
        # Run Jacobi iteration
        for iteration in range(self.max_iter):
            next_prop_risk = {}
            for v in accounts:
                fused_v = fused_map.get(v, 0.0)
                inflows = in_edges_map.get(v, [])
                
                if not inflows:
                    next_prop_risk[v] = fused_v
                    continue
                    
                # Reference time is the latest transaction involving v
                times = [tx[2] for tx in inflows if pd.notna(tx[2])]
                t_ref = max(times) if times else pd.Timestamp.now()
                
                propagation_sum = 0.0
                total_in_volume = sum(tx[1] for tx in inflows) + 1e-9
                
                for u, amt, ts in inflows:
                    if pd.isna(ts):
                        delta_t = 0.0
                    else:
                        delta_t = (t_ref - ts).total_seconds() / 3600.0 # hours
                        
                    # Calculate weight proportional to relative flow size
                    flow_weight = amt / total_in_volume
                    decay = np.exp(-self.alpha * max(0.0, delta_t))
                    
                    propagation_sum += prop_risk[u] * flow_weight * decay
                    
                # Fused baseline + weighted propagated neighbor risk
                next_prop_risk[v] = min(fused_v + 0.35 * propagation_sum, 1.0)
                
            prop_risk = next_prop_risk
            
        # Compile output dataframe
        records = []
        for acc in accounts:
            records.append({
                'account_id': acc,
                'risk_score': prop_risk[acc],
                'risk_score_fused': fused_map[acc]
            })
            
        df = pd.DataFrame(records)
        df["risk_percentile"] = (df["risk_score"].rank(pct=True) * 100).round(2)
        df["risk_band"] = pd.cut(
            df["risk_score"],
            bins=[-np.inf, 0.25, 0.50, 0.75, 0.90, np.inf],
            labels=["LOW", "ELEVATED", "HIGH", "SEVERE", "CRITICAL"],
        ).astype(str)
        
        # Rank by risk score descending
        df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
        df.insert(0, "rank", np.arange(1, len(df) + 1))
        return df
