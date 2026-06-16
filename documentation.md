# Technical Specification: AMLIOS-X (Anti-Money Laundering Intelligence Operating System - eXtended)

**Track 3: Network & Graph Intelligence**  
**Document Classification:** System Architecture Design & Implementation Blueprint  

---

## System Overview & Bidirectional Evidence Mesh

**AMLIOS-X** is an integrated financial knowledge graph, temporal network analyzer, and risk-prioritization system designed to address the detection of structured financial crime. Rather than utilizing a linear pipeline, AMLIOS-X is architected as a **bidirectional evidence mesh** across 14 specialized processing layers. 

```
                               ┌────────────────────────────────────────┐
                               │     Layer 1: Unified Knowledge Graph   │◄────────────────┐
                               └───────────────────┬────────────────────┘                 │
                                                   │                                      │
                                                   ▼                                      │
                               ┌────────────────────────────────────────┐                 │
                               │     Layers 2-5: Engine & Typologies    │                 │
                               └───────────────────┬────────────────────┘                 │
                                                   │                                      │
                                                   ▼                                      │
                               ┌────────────────────────────────────────┐                 │
                               │     Layers 6-9: Community, ML & GNN    │                 │
                               └───────────────────┬────────────────────┘                 │
                                                   │                                      │
                                                   ▼                                      │
                               ┌────────────────────────────────────────┐                 │
                               │  Layers 10-13: Explainability & Copilot│                 │
                               └───────────────────┬────────────────────┘                 │
                                                   │                                      │
                                                   ▼                                      │
                               ┌────────────────────────────────────────┐                 │
                               │     Layer 14: Interactive Dashboard    │─────────────────┘
                               └────────────────────────────────────────┘
```

The core innovation of this architecture is its feedback loop: downstream analytical insights, risk scores, and explainability subgraphs are written back to the primary database as structural node properties. This enables iterative refinement across multiple inference passes, dynamically updating risk baselines in response to both machine metrics and analyst annotations.

---

## The 14-Layer Multi-Entity Architecture

```
Layer 1: Unified Knowledge Graph ──► Layer 2: Temporal Graph Engine ──► Layer 3: Feature Fabric (500+ Feats)
                                                                                  │
Layer 6: Community Intelligence  ◄── Layer 5: Typology Classifier  ◄── Layer 4: Motif Mining Engine
            │
            ▼
Layer 7: Graph Embeddings        ──► Layer 8: TGAT & Hetero GNN     ──► Layer 9: Risk Fusion Engine
                                                                                  │
Layer 12: Investigation Engine   ◄── Layer 11: Explainability Layer ◄── Layer 10: STR Intelligence Module
            │
            ▼
Layer 13: Analyst Copilot (LLM)  ──► Layer 14: Interactive Dashboard
```

### Layer 1 — Unified Knowledge Graph (Neo4j)
A multi-entity heterogeneous schema modeling multiple distinct node types:
*   **Nodes:** `Account`, `Customer`, `Bank`, `Branch`, `Country`, `STR_Report`, `Device`, `Location`.
*   **Relationships:** `OWNS` (Customer $\rightarrow$ Account), `SENDS` (Account $\rightarrow$ Account, containing precise millisecond timestamps, transaction mode, and amounts), `LOCATED_IN` (Account $\rightarrow$ Branch $\rightarrow$ Bank $\rightarrow$ Country), `REPORTED_IN` (Account/Customer $\rightarrow$ STR_Report).
*   **Legitimate Entity Whitelisting:** Includes verified low-risk nodes (e.g., large government payroll departments, established utility organizations, institutional clearinghouses) to reduce false positives by discounting standard, highly repetitive payments.

### Layer 2 — Temporal Graph Engine
Constructs a Continuous-Time Dynamic Graph (CTDG) representation instead of coarse snapshots. Transactions are modeled as fine-grained temporal events, preserving the millisecond-level chronological ordering necessary to calculate real-world forwarding delays.

### Layer 3 — Feature Fabric
Extracts a comprehensive set of structural and behavioral attributes:
*   **Temporal Burstiness:** Analyzes structural variations in transaction intervals.
*   **Directed Flow Asymmetry:** Compares directional money flows to detect unidirectional routes.
*   **Structural Hole Exploitation:** Identifies accounts bridging otherwise disconnected communities.
*   **Hawkes Process Intensity & Threshold Proximity:** Modeled mathematically in Section 3.

### Layer 4 — Motif Mining Engine
Executes temporal graphlet discovery using Exact + Approximate motif counting. This engine identifies patterns based on structural shapes and temporal activation order within defined time windows.

### Layer 5 — Typology Classifier
A hybrid engine combining rule-based heuristics with machine learning to identify specific laundering patterns. It maps anomalies directly to target typologies and computes confidence metrics alongside structural evidence chains.

### Layer 6 — Community Intelligence
Applies **Leiden** hierarchical partitioning and **SCAN** (Structural Clustering Algorithm for Networks) to identify overlapping communities. This layer also utilizes persistence homology to track how community densities evolve over time.

### Layer 7 — Graph Embeddings
Generates low-dimensional vector representations using static **Node2Vec** (optimized for neighborhood structure via DFS-biased walks) and **HTNE** (Hawkes Temporal Network Embedding) to capture temporal burst patterns.

### Layer 8 — Temporal Graph Neural Network (TGAT + HAN Ensemble)
Ensembles a **Temporal Graph Attention Network (TGAT)**, which uses harmonic time encodings to capture timing dependencies, with a **Heterogeneous Attention Network (HAN)** to aggregate type-specific neighborhoods (e.g., Accounts, Customers, and Countries).

### Layer 9 — Risk Fusion Engine
Combines risk signals using **Dempster–Shafer Evidence Fusion**, aggregating GNN classification probabilities, heuristic typology scores, community risk indexes, and fuzzy STR links. 

It then propagates these fused risk scores across the network using a directional money-flow model with exponential distance decay:

$$R_{\text{prop}}(v) = R_{\text{fused}}(v) + \sum_{u \in \mathcal{N}_{\text{in}}(v)} R_{\text{prop}}(u) \cdot e^{-\alpha \cdot \Delta t_{u \rightarrow v}}$$

### Layer 10 — STR Intelligence Module
Applies Named Entity Recognition (NER) and phonetic fuzzy matching to link structured XML transactions with unstructured narratives, generating verification scores for claims made in report texts.

### Layer 11 — Explainability Layer
Uses **GNNExplainer** to extract minimal self-contained subgraphs responsible for high risk scores. This layer also performs counterfactual analyses (e.g., calculating the risk drop if a specific transaction edge were removed) to pinpoint suspicious activity.

### Layer 12 — Investigation Engine
Maintains an analyst priority queue based on risk score, community risk, and verification status. It generates structured case files for analyst review.

### Layer 13 — Analyst Copilot (LLM)
Uses local, open-weight language models to generate natural language investigation summaries and auto-draft draft filings matching regulatory standards.

### Layer 14 — Interactive Dashboard
Provides a user interface featuring live money-flow animations, risk contagion heatmaps, community visualizations, and side-by-side evidence matching views.

---

## Advanced Feature Engineering Specifications

AMLIOS-X incorporates several advanced, mathematically grounded features to detect patterns that standard centrality metrics often miss.

```
                     ┌──────────────────────────────────────────────┐
                     │          Advanced Feature Layer              │
                     └──────────────────────┬───────────────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
┌─────────────────────────┐        ┌─────────────────────────┐        ┌─────────────────────────┐
│ Hawkes self-excitation  │        │   Threshold Proximity   │        │ Directed Flow Asymmetry │
│  λ(t) Intensity Score   │        │     Structuring Score   │        │     Index Calculation   │
└─────────────────────────┘        └─────────────────────────┘        └─────────────────────────┘
```

### 1. Hawkes Process Intensity Score
We model an account's transaction times as a self-exciting point process to capture temporal clustering. The conditional intensity function $\lambda(t)$ is defined as:

$$\lambda(t) = \mu + \sum_{t_i < t} \alpha e^{-\beta(t - t_i)}$$

Where:
*   $\mu$ is the baseline transaction arrival rate.
*   $\alpha$ is the self-excitation scale factor.
*   $\beta$ is the exponential decay rate.
*   $t_i$ are the historical timestamps of transactions involving the account.

Laundering operations using automated rapid routing (such as automated layering chains) exhibit elevated $\alpha$ and $\lambda(t)$ values during rapid-forwarding bursts.

### 2. Threshold Proximity Score (TPS)
To detect structured deposits or withdrawals designed to evade regulatory reporting thresholds (e.g., the standard NPR 1,000,000 threshold in Nepal), we calculate the Threshold Proximity Score ($TPS$) for each node:

$$TPS(v) = \frac{\sum_{e \in E_{\text{out}}(v)} \mathbb{I}\left( (1 - \epsilon) \cdot T \le A(e) < T \right)}{|E_{\text{out}}(v)|}$$

Where:
*   $T$ is the regulatory reporting limit (e.g., NPR 1,000,000).
*   $\epsilon$ is the proximity tolerance window (e.g., $0.10$ for transactions between 900,000 and 999,999).
*   $A(e)$ is the transaction amount for edge $e$.
*   $\mathbb{I}$ is the indicator function.

Nodes with high $TPS$ values indicate systematic evasion behavior.

### 3. Directed Flow Asymmetry Index ($DFA$)
Legitimate business accounts typically exhibit bidirectional transactions (invoicing and payments) over time, whereas laundering networks often rely on unidirectional pipelines. For any connected pair of accounts $(u, v)$, the flow asymmetry is calculated as:

$$DFA(u, v) = \frac{\left| \Phi(u \rightarrow v) - \Phi(v \rightarrow u) \right|}{\Phi(u \rightarrow v) + \Phi(v \rightarrow u) + \epsilon}$$

Where $\Phi(u \rightarrow v)$ is the aggregate transaction volume from $u$ to $v$ over a sliding time window. We then calculate a node-level $DFA$ by averaging these asymmetric scores across its local neighborhood.

### 4. Structural Hole Exploitation Score
Using Burt's structural constraint index $C_i$, we identify nodes that act as bridges between otherwise isolated communities. Intermediary layering accounts typically exploit these structural holes:

$$C_i = \sum_{j} \left( p_{ij} + \sum_{k} p_{ik} p_{kj} \right)^2$$

Where $p_{ij}$ is the proportion of node $i$'s network energy invested in relationship $j$. Accounts with low constraint scores and unidirectional flow asymmetry act as bridges between distinct financial clusters, marking them as potential layering coordinators.

---

## Domain-Specific Financial Typologies

The system implements specific pattern-matching algorithms to detect complex laundering typologies common in cross-border and digital finance networks.

```
                          ┌──────────────────────────┐
                          │   Typology Classifier    │
                          └─────────────┬────────────┘
                                        │
        ┌───────────────────────┬───────┴───────┬───────────────────────┐
        ▼                       ▼               ▼                       ▼
┌──────────────┐        ┌──────────────┐┌──────────────┐        ┌──────────────┐
│ Hundi/Hawala │        │  Loan-Back   ││  Ghost Payroll│       │ Accumulation │
│  Ghost Flows │        │   Triangles  ││  Diversion   │       │ Spike-Disperse│
└──────────────┘        └──────────────┘└──────────────┘        └──────────────┘
```

### 1. Hundi / Hawala Network Detection (Ghost Flows)
Informal value transfer systems (Hawala/Hundi) operate via domestic ledger offsets rather than international wire transfers. AMLIOS-X flags Hawala corridors (such as Nepal-India-UK flows) by identifying synchronized transaction pairs:
*   **The Pattern:** Sender $S_1$ in Country $A$ sends to intermediary $I_1$ in Country $A$. Almost simultaneously (within a narrow temporal window $\Delta t$), intermediary $I_2$ in Country $B$ sends an equivalent amount to receiver $R_1$ in Country $B$. 
*   **The Detection:** The system flags these parallel, unlinked transaction pairs by matching high-correlation transaction volumes and time intervals across countries without a direct cross-border link between the origin and destination.

### 2. Loan-Back Schemes
Laundering operations can involve depositing illicit cash in one institution and taking a "clean" loan from another, using shell entities to cycle the funds and repay the loan.
*   **The Pattern:** Cycle pathways of the form $A \rightarrow B \rightarrow C \rightarrow A$, where $A$ is the primary account, $B$ is an offshore intermediary, and $C$ is a shell entity.
*   **The Detection:** Checks for cyclic graphs where edge $C \rightarrow A$ is labeled as a "loan disbursement" or "business loan" and edge $A \rightarrow C$ acts as "repayment," with cumulative transaction amounts matching within a $5\%$ variance.

### 3. Trade-Based Money Laundering (TBML) Signals
TBML often involves misrepresenting transaction values on invoices to move funds across borders.
*   **The Detection:** Identifies cross-border transfers to foreign suppliers that significantly exceed the historical median invoice size for that sector, followed by smaller, rapid offsetting transfers to related shell accounts.

### 4. Ghost Employee Payroll Diversion
This pattern exploits corporate accounts to route funds to unauthorized individuals who then consolidate the money.
*   **The Pattern:** A corporate account distributes regular, uniform payments (simulating salary) to multiple newly opened accounts. Rather than remaining in those accounts, the funds are immediately forwarded to a single consolidating account.
*   **The Detection:** Identifies payroll-like outflows where the recipients forward $>90\%$ of the received funds within 12 hours to a shared destination.

### 5. Rapid Cycling (Carousel Fraud)
*   **The Pattern:** High-velocity circular loops where funds pass through multiple intermediate entities to obscure their origin.
*   **The Detection:** Detects temporal cycles where $|Cycle| \ge 3$, the loop completes within 24 hours, and the amount conservation exceeds $98\%$, indicating that the intermediaries are serving as pass-through nodes rather than transactional endpoints.

### 6. Shell Company Layering Networks
*   **The Pattern:** Newly registered entities transacting exclusively within a closed network before routing a large payment outward.
*   **The Detection:** Isolates clusters of nodes with low account ages and high internal transaction ratios (internal volume / total volume $> 0.90$) that suddenly execute large outbound transfers to external entities.

### 7. Mule Account Networks
*   **The Pattern:** Dormant accounts that suddenly experience high-volume transactional activity.
*   **The Detection:** Flags accounts with high dormancy scores (defined as the time since the last transaction) that experience a sudden spike in velocity coupled with near-immediate, high-volume forwarding.

### 8. Accumulation-Spike-Disperse Pattern
*   **The Pattern:** Multiple small inbound transfers followed by a brief holding period and a rapid outbound distribution.
*   **The Detection:** Applies time-series segmentation to account balances to detect a three-phase pattern:
    1. A gradual accumulation phase (multiple low-value incoming edges).
    2. A brief, high-volume balance spike.
    3. A rapid dispersal phase (multiple low-value outgoing edges executed within a short time window).

---

## Graph Machine Learning & Training Innovations

The machine learning architecture leverages advanced temporal graph representations and specialized training strategies to address class imbalance.

```
                    ┌──────────────────────────────────────────────┐
                    │               Graph ML Engine                │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│ Temporal Graph Attention│       │  Heterogeneous GNN      │       │ Unsupervised Anomaly    │
│    TGAT Time Encoding   │       │   (HAN Metapath Heads)  │       │   (DOMINANT framework)  │
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

### 1. Temporal Graph Attention Network (TGAT)
To capture timing-dependent patterns, AMLIOS-X uses TGAT layers in its GNN ensemble. TGAT replaces static edge embeddings with continuous-time harmonic representations, mapping timestamps into a vector space using sine and cosine transformations:

$$\Phi_d(t) = \left[ \cos(\omega_1 t), \sin(\omega_1 t), \dots, \cos(\omega_d t), \sin(\omega_d t) \right]$$

This allows the attention mechanism to weigh transactions based on their temporal proximity, helping the model identify rapid-forwarding patterns.

### 2. Heterogeneous Attention Networks (HAN)
Laundering patterns often involve multiple entity types (e.g., Accounts, Customers, Countries). The HAN layer uses meta-paths (such as $\text{Account} \xrightarrow{\text{OWNS}} \text{Customer} \xrightarrow{\text{OWNS}} \text{Account}$) to learn semantic-specific node representations, aggregating information across different node and relationship types.

### 3. Unsupervised Anomaly Detection (DOMINANT)
To detect novel laundering typologies that do not match known labels, the ensemble includes the **DOMINANT** (Deep Anomaly Detection on Attributed Networks) framework. 

DOMINANT uses a joint autoencoder architecture:
*   A **Network Structure Reconstruction Autoencoder** that uses a GCN to reconstruct the adjacency matrix $\mathbf{A}$.
*   A **Node Attribute Reconstruction Autoencoder** that reconstructs the node feature matrix $\mathbf{X}$.

Nodes that exhibit high reconstruction errors across both structure and attributes are flagged as anomalous, helping detect previously unobserved transaction patterns.

### 4. GraphSMOTE for Class Imbalance
Supervised classifiers often struggle with extreme class imbalances (e.g., $<0.5\%$ positive labels). To address this, we use **GraphSMOTE** to generate synthetic positive examples in the GNN's latent embedding space. 

By interpolating between the embeddings of confirmed laundering nodes and introducing synthetic transaction edges based on reconstructed link probabilities, the training process improves model recall on minority classes without increasing false positive rates.

---

## Explainability & Verification Systems

To support compliance investigations, AMLIOS-X provides three explainability mechanisms that translate network statistics into actionable findings.

```
                  ┌─────────────────────────────────────────────┐
                  │            Explainability Layer             │
                  └──────────────────────┬──────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│ Counterfactual Analysis│      │  Subgraph Extraction   │      │   Multi-Level SHAP     │
│   Score Perturbation   │      │     (GNNExplainer)     │      │     Decomposition      │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

### 1. Counterfactual Graph Explanations
For any high-risk classification, the system identifies the critical transaction edges driving the risk score. By applying gradient-based edge perturbation, it identifies the minimum change in transaction volume or edge structure required to reduce the risk score below the suspicion threshold:

$$\arg\min_{\Delta \mathbf{A}} \left( \mathcal{L}_{\text{risk}}(G \setminus \Delta \mathbf{A}) + \gamma \|\Delta \mathbf{A}\|_1 \right)$$

This helps investigators pinpoint the specific transactions responsible for flagging an account.

### 2. Evidence-Based Subgraph Extraction (GNNExplainer)
Rather than presenting an unreadable global network, the system uses **GNNExplainer** to isolate the minimal, self-contained flow network (typically 2-hops) that preserves the node's high risk score. This extracted subgraph is rendered as an interactive visual flow map, highlighting load-bearing edges and nodes for the investigator.

### 3. Multi-Level SHAP Decomposition
To clarify the factors driving a risk score, AMLIOS-X uses SHAP to decompose the final score into four distinct attribution categories:
*   **Actor Behavior ($S_{\text{self}}$):** Attributed to the node's own transaction patterns (e.g., threshold proximity, timing velocity).
*   **Counterparty Contagion ($S_{\text{neighbor}}$):** Attributed to the risk profiles of direct transacting partners.
*   **Community Contagion ($S_{\text{community}}$):** Attributed to the overall risk density of the local Leiden partition.
*   **External Evidence ($S_{\text{external}}$):** Attributed to matches found in unstructured STR files.

The results are presented in a stacked bar chart, giving investigators a clear breakdown of the risk drivers.

---

## Implementation Codebase

### Script 1: Entity Resolution & Phonetic Linker
This module parses incoming `strs.xml` reports, applies phonetic normalization algorithms, and links individuals to the central Knowledge Graph.

```python
import xml.etree.ElementTree as ET
import pandas as pd
import re

def calculate_soundex(name):
    """
    Computes the standard Soundex code for string matching.
    """
    if not name:
        return ""
    name = name.upper()
    cleaned = re.sub(r'[^A-Z]', '', name)
    if not cleaned:
        return ""
    
    first_char = cleaned[0]
    mapping = {
        'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3',
        'L': '4', 'MN': '5', 'R': '6'
    }
    
    soundex_digits = []
    for char in cleaned[1:]:
        for key, digit in mapping.items():
            if char in key:
                if not soundex_digits or soundex_digits[-1] != digit:
                    soundex_digits.append(digit)
                break
        else:
            # Vowels, H, W, Y are ignored
            pass
            
    # Format to exactly 1 letter and 3 digits
    soundex_str = first_char + "".join(soundex_digits)
    soundex_str = (soundex_str + "000")[:4]
    return soundex_str

def match_and_link_entities(xml_path, party_registry_path):
    """
    Parses STR XML reports and links referenced entities to the KYC registry 
    using phonetic and alphanumeric matching.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    registry = pd.read_csv(party_registry_path)
    
    # Pre-calculate phonetic indices on KYC registry
    registry['phonetic_first'] = registry['first_name'].apply(calculate_soundex)
    registry['phonetic_last'] = registry['last_name'].apply(calculate_soundex)
    
    links = []
    for person_node in root.findall('.//t_person'):
        str_first = person_node.findtext('first_name')
        str_last = person_node.findtext('last_name')
        str_passport = person_node.findtext('passport_number')
        str_tax = person_node.findtext('tax_number')
        
        # Priority 1: Direct Alphanumeric Identifier Matches
        direct_match = registry[
            ((registry['passport_number'] == str_passport) & (str_passport is not None)) |
            ((registry['tax_number'] == str_tax) & (str_tax is not None))
        ]
        
        if not direct_match.empty:
            links.append({
                'str_entity': f"{str_first} {str_last}",
                'registry_id': direct_match.iloc[0]['Account_ID'],
                'match_method': 'direct_identifier',
                'confidence': 1.0
            })
            continue
            
        # Priority 2: Phonetic Match Pipeline
        phon_first = calculate_soundex(str_first)
        phon_last = calculate_soundex(str_last)
        
        phonetic_matches = registry[
            (registry['phonetic_first'] == phon_first) & 
            (registry['phonetic_last'] == phon_last)
        ]
        
        for _, match_row in phonetic_matches.iterrows():
            links.append({
                'str_entity': f"{str_first} {str_last}",
                'registry_id': match_row['Account_ID'],
                'match_method': 'phonetic_match',
                'confidence': 0.85
            })
            
    return pd.DataFrame(links)
```

### Script 2: Temporal Path DFS Tracker & Flow Asymmetry Analyzer
Tracks transaction sequences and measures directional asymmetry across the network.

```python
import networkx as nx
import pandas as pd
import numpy as np

def compute_asymmetry_and_conservation(G, source_node, target_node, window_hours=72):
    """
    Computes Directed Flow Asymmetry (DFA) and tracks temporal multi-hop paths 
    exhibiting high amount conservation.
    """
    # 1. Compute Directed Flow Asymmetry
    out_flow = 0.0
    if G.has_edge(source_node, target_node):
        out_flow = sum(edge['amount_local_npr'] for edge in G[source_node][target_node].values())
        
    in_flow = 0.0
    if G.has_edge(target_node, source_node):
        in_flow = sum(edge['amount_local_npr'] for edge in G[target_node][source_node].values())
        
    dfa = abs(out_flow - in_flow) / (out_flow + in_flow + 1e-5)
    
    # 2. Path-Level Amount Conservation Tracker (Chains starting from source_node)
    conserved_paths = []
    
    def dfs_path_tracker(current_node, path_edges, current_depth):
        if current_depth >= 3:
            # Calculate path-level conservation
            amounts = [edge_data['amount_local_npr'] for _, _, edge_data in path_edges]
            conservation = min(amounts) / max(amounts)
            if conservation >= 0.97:
                conserved_paths.append({
                    'path': [edge[0] for edge in path_edges] + [current_node],
                    'conservation': conservation,
                    'volume': max(amounts)
                })
        if current_depth == 6:
            return
            
        last_edge_data = path_edges[-1][2]
        last_time = pd.to_datetime(f"{last_edge_data['Date']} {last_edge_data['Time']}")
        
        for neighbor in G.successors(current_node):
            for key in G[current_node][neighbor]:
                edge_data = G[current_node][neighbor][key]
                edge_time = pd.to_datetime(f"{edge_data['Date']} {edge_data['Time']}")
                
                # Enforce chronological ordering
                time_delta = (edge_time - last_time).total_seconds() / 3600.0
                if 0 < time_delta <= window_hours:
                    path_edges.append((current_node, neighbor, edge_data))
                    dfs_path_tracker(neighbor, path_edges, current_depth + 1)
                    path_edges.pop()

    # Initialize DFS from start node edges
    for neighbor in G.successors(source_node):
        for key in G[source_node][neighbor]:
            edge_data = G[source_node][neighbor][key]
            dfs_path_tracker(neighbor, [(source_node, neighbor, edge_data)], 1)
            
    return dfa, conserved_paths
```

### Script 3: Hawkes Self-Excitation & Threshold Proximity Feature Extractor
Quantifies transactional clustering and structuring behaviors for each account.

```python
import numpy as np
import pandas as pd

def compute_hawkes_intensity(timestamps, t_eval, mu=0.01, alpha=0.5, beta=1.0):
    """
    Estimates the Hawkes process conditional intensity lambda(t) for an account's transaction sequence.
    """
    if len(timestamps) == 0:
        return mu
    timestamps = np.sort(np.array(timestamps))
    # Select events that occurred prior to the evaluation time
    past_events = timestamps[timestamps < t_eval]
    if len(past_events) == 0:
        return mu
    
    # Calculate self-excitation sum: alpha * sum( exp( -beta * (t_eval - t_i) ) )
    decay_sum = np.sum(np.exp(-beta * (t_eval - past_events)))
    intensity = mu + alpha * decay_sum
    return intensity

def extract_advanced_features(tx_df, target_threshold=1000000, tolerance=0.10):
    """
    Calculates Hawkes intensity and Threshold Proximity Scores (TPS) across the dataset.
    """
    tx_df['datetime'] = pd.to_datetime(tx_df['Date'] + ' ' + tx_df['Time'])
    accounts = pd.concat([tx_df['Sender_account'], tx_df['Receiver_account']]).unique()
    
    features = {}
    lower_bound = target_threshold * (1.0 - tolerance)
    
    for acc in accounts:
        # Get transaction times for the account
        acc_tx = tx_df[(tx_df['Sender_account'] == acc) | (tx_df['Receiver_account'] == acc)].sort_values('datetime')
        times_sec = (acc_tx['datetime'] - acc_tx['datetime'].min()).dt.total_seconds().values / 3600.0 # Convert to hours
        
        # Calculate Hawkes intensity at the time of the last transaction
        if len(times_sec) > 0:
            last_t = times_sec[-1]
            h_intensity = compute_hawkes_intensity(times_sec[:-1], last_t)
        else:
            h_intensity = 0.0
            
        # Calculate Threshold Proximity Score (TPS) on outbound transactions
        out_tx = tx_df[tx_df['Sender_account'] == acc]
        out_count = len(out_tx)
        
        if out_count > 0:
            structuring_tx = out_tx[
                (out_tx['amount_local_npr'] >= lower_bound) & 
                (out_tx['amount_local_npr'] < target_threshold)
            ]
            tps_score = len(structuring_tx) / out_count
        else:
            tps_score = 0.0
            
        features[acc] = {
            'hawkes_intensity': h_intensity,
            'threshold_proximity': tps_score
        }
        
    return pd.DataFrame.from_dict(features, orient='index')
```

---

## 7-Day Implementation Roadmap

```
Day 1: Graph & Data Foundation ──► Day 2: Advanced Feature Engineering ──► Day 3: ML & GNN Pipeline
                                                                                  │
Day 6: STR Alignment Engine    ◄── Day 5: Explainability Engine        ◄── Day 4: Typology Systems
            │
            ▼
Day 7: Dashboard & Testing
```

### Day 1: Graph & Data Foundation
*   **Tasks:** Import datasets and parse unstructured files.
*   **Deliverables:** Build a unified knowledge graph in Neo4j (or multi-entity NetworkX) linking Accounts, Customers, Countries, and STR reports. Configure whitelists for known-good institutional accounts.
*   **Validation:** Verify that node and relationship counts match the source datasets.

### Day 2: Advanced Feature Engineering & Unsupervised Communities
*   **Tasks:** Calculate advanced behavioral, flow, and temporal features.
*   **Deliverables:** Run the Hawkes Intensity, Threshold Proximity, Flow Asymmetry, and Structural Hole models. Apply Leiden and SCAN partitioning to establish risk baselines.
*   **Validation:** Confirm that community boundaries separate known high-volume nodes.

### Day 3: ML, GNN, & Risk Fusion Pipeline
*   **Tasks:** Train the supervised and unsupervised modeling ensemble.
*   **Deliverables:** Train the GNN model using GraphSMOTE. Train the XGBoost model and compile SHAP feature attributions. Implement the risk fusion engine.
*   **Validation:** Evaluate precision and recall using cross-validation.

### Day 4: Typology Systems Implementation
*   **Tasks:** Configure rule-based and ML-driven pattern matching for financial typologies.
*   **Deliverables:** Deploy detection models for the target typologies (including Hundi, Loan-Back, Shell Layering, and Mule networks).
*   **Validation:** Run tests against synthetic test cases to verify detection accuracy.

### Day 5: Explainability Engine
*   **Tasks:** Integrate explanation models for the risk-prioritization queue.
*   **Deliverables:** Deploy GNNExplainer to extract minimal subgraphs and configure counterfactual analysis routines for high-risk accounts.
*   **Validation:** Confirm that risk scores decrease appropriately during edge perturbation tests.

### Day 6: STR Alignment Engine & Copilot Generation
*   **Tasks:** Match textual claims with structural transactional evidence.
*   **Deliverables:** Deploy the phonetic entity resolution module to align XML narratives with the transaction graph. Set up the local open-weight model to generate analyst summaries.
*   **Validation:** Verify the alignment accuracy on known STR filings.

### Day 7: Interactive Dashboard & System Verification
*   **Tasks:** Build the analyst interface and conduct end-to-end testing.
*   **Deliverables:** Launch the dashboard, showcasing money-flow animations, risk heatmap visualizations, and the case builder tool. Package all submission materials.
*   **Validation:** Run end-to-end tests to verify system stability under mock investigator workflows.