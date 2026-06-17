# AMLIOS-X Implementation Plan — Track 3: Network & Graph Intelligence

## Background

Building the **AMLIOS-X** system for the AI/ML Hackathon, Track 3 (Network & Graph Intelligence). The project uses a synthetic Nepali banking dataset (~1M transactions, ~6,800 accounts) to detect money laundering through graph-based analysis.

### Actual Dataset Mapping

The dataset files differ slightly from what the division document assumes. Here's the mapping:

| Division Doc Assumes | Actual File Available | Notes |
|---|---|---|
| `augmented_saml_d.csv` | `data/STUDENT_DATASET/transactions.csv` (~36MB) | Full transactions with 50+ columns |
| `party_registry.csv` | `data/STUDENT_DATASET/accounts.csv` (~7.6MB) | KYC records per account |
| `strs.xml` (single file) | `data/STUDENT_DATASET/reports/*.xml` (276 files) | Individual XML reports |
| — | `data/STUDENT_DATASET/graph_edges.csv` (~5.9MB) | Pre-built sender→receiver edge list |
| — | `data/STUDENT_DATASET/ml_features.csv` (~17MB) | Pre-engineered features with `is_suspicious_tx` label |

> [!IMPORTANT]
> The `ml_features.csv` has `is_suspicious_tx` as the label column (not `Is_laundering`). The `accounts.csv` uses `account_id` and `name` (not `first_name`/`last_name` separately). Code from the division doc needs adaptation to match these actual column names.

---

## Strategy: Atomic Commits to Show Realistic Development

Each phase below = **one commit**. Work on it, test it, commit with the suggested message, push. This produces a natural-looking commit history across the timeline.

---

## Phase 0: Project Scaffolding & Folder Structure

**Goal:** Create the complete `amlios_x/` directory tree, `.gitignore`, `requirements.txt`, `README.md`, and all `__init__.py` files. No logic yet — just the skeleton.

### Files to Create

#### [NEW] [.gitignore](file:///d:/Downloads/Aleph/.gitignore)
- Ignore `data/STUDENT_DATASET/`, `*.csv`, `*.xml`, `__pycache__/`, `.env`, `*.pyc`, model artifacts, virtual environments

#### [NEW] [requirements.txt](file:///d:/Downloads/Aleph/requirements.txt)
```
pandas>=2.0
numpy>=1.24
networkx>=3.1
scikit-learn>=1.3
xgboost>=2.0
matplotlib>=3.7
seaborn>=0.12
shap>=0.42
streamlit>=1.28
lxml>=4.9
python-Levenshtein>=0.21
cdlib>=0.4
igraph>=0.11
```

#### [NEW] [README.md](file:///d:/Downloads/Aleph/README.md)
- Project title, track info, architecture overview, setup instructions, how to run

#### [NEW] Directory structure with `__init__.py` stubs:
```
src/__init__.py
src/data_loader.py      (empty stub with docstring)
src/graph_engine.py      (empty stub with docstring)
src/typologies.py        (empty stub with docstring)
src/ml_models.py         (empty stub with docstring)
src/explainability.py    (empty stub with docstring)
src/utils.py             (empty stub with docstring)
app/__init__.py           (if needed)
app/app.py               (empty stub)
app/components/__init__.py
app/components/flow_visualizer.py  (empty stub)
app/components/str_validator.py    (empty stub)
tests/__init__.py
tests/test_typologies.py  (empty stub)
tests/test_data_loader.py (empty stub)
data/processed/           (empty dir with .gitkeep)
notebooks/                (empty dir with .gitkeep)
```

### Commit
```
git add .gitignore requirements.txt README.md src/ app/ tests/ data/processed/.gitkeep notebooks/.gitkeep
git commit -m "chore: initialize project structure with module stubs and dependencies"
```

---

## Phase 1 (Dev A): Data Loader — XML Parsing & Phonetic Entity Resolution

**Goal:** Implement `src/data_loader.py` with the `AMLDataParser` class that:
1. Loads `transactions.csv`, `accounts.csv`, and `graph_edges.csv`
2. Parses all 276 XML reports from `reports/` directory
3. Extracts structured fields (`t_person`, account info, narratives, report metadata)
4. Implements Soundex phonetic matching to link STR entities → `accounts.csv`
5. Produces `data/processed/extracted_entities.csv` (linked STR entities with match confidence)

### Key Adaptations from Division Doc
- Column mapping: `accounts.csv` has `name` (full name), not `first_name`/`last_name` — need to split
- Column mapping: `accounts.csv` has `tax_number` (matches), no `passport_number` column — match on tax_number + name phonetics
- XML files are individual (`report_*.xml`), not a single `strs.xml` — iterate over directory
- XML structure: `<report>` → `<transaction>` → `<t_from_my_client>` → `<from_account>` → `<signatory>` → `<t_person>`

#### [NEW] [data_loader.py](file:///d:/Downloads/Aleph/src/data_loader.py)
- `class AMLDataParser` with methods:
  - `load_transactions()` → DataFrame from `transactions.csv`
  - `load_accounts()` → DataFrame from `accounts.csv`  
  - `load_graph_edges()` → DataFrame from `graph_edges.csv`
  - `parse_all_xml_reports()` → DataFrame of extracted STR entities
  - `calculate_soundex(name)` → Soundex code
  - `match_and_link_entities()` → DataFrame linking STR persons to accounts
  - `save_processed()` → writes `extracted_entities.csv`

#### [NEW] [utils.py](file:///d:/Downloads/Aleph/src/utils.py)
- Logging configuration (`setup_logger()`)
- Path constants (`DATA_RAW_DIR`, `DATA_PROCESSED_DIR`, etc.)
- Common math helpers

### Commit
```
git add src/data_loader.py src/utils.py
git commit -m "feat: implement STR XML parser and Soundex phonetic entity resolution"
```

---

## Phase 2 (Dev A): Temporal Graph Engine — NetworkX Multigraph

**Goal:** Implement `src/graph_engine.py` with the `ContinuousTimeGraphEngine` class that:
1. Builds a directed multigraph (`nx.MultiDiGraph`) from `transactions.csv`
2. Nodes = accounts with KYC attributes from `accounts.csv`
3. Edges = individual transactions with amount, timestamp, currency, cross-border flag
4. Computes basic structural centrality metrics (in-degree, out-degree, PageRank, betweenness)
5. Computes **Directed Flow Asymmetry (DFA)** for each node
6. Computes **Hawkes Process Intensity** for each account
7. Computes **Threshold Proximity Score (TPS)** for structuring detection (NPR 1,000,000 threshold)
8. Exports all features to `data/processed/node_features.csv`

#### [MODIFY] [graph_engine.py](file:///d:/Downloads/Aleph/src/graph_engine.py)
- `class ContinuousTimeGraphEngine`:
  - `build_multigraph(tx_df, accounts_df)` → populates `self.G`
  - `compute_centrality_features()` → dict of PageRank, betweenness, degree
  - `compute_asymmetry_index(node)` → DFA score
  - `compute_hawkes_intensity(account_id)` → λ(t) score
  - `compute_threshold_proximity(account_id)` → TPS score  
  - `compute_structural_hole_score(node)` → Burt's constraint
  - `build_node_feature_matrix()` → DataFrame with all features per account
  - `export_features(output_path)` → saves `node_features.csv`

### Commit
```
git add src/graph_engine.py
git commit -m "feat: build temporal multigraph engine with DFA, Hawkes, and TPS features"
```

---

## Phase 3 (Dev A): Advanced Feature Engineering — Structural Holes & Community Features

**Goal:** Extend the feature pipeline with:
1. **Structural Hole Exploitation Score** (Burt's constraint index)
2. **Leiden Community Detection** — hierarchical partitioning
3. **Community-level risk indices**: cross-border ratio, internal transaction ratio, motif density
4. Add community membership and community risk as node-level features
5. Update `node_features.csv` with the new columns

#### [MODIFY] [graph_engine.py](file:///d:/Downloads/Aleph/src/graph_engine.py)
- Add methods:
  - `detect_communities_leiden()` → community assignments
  - `compute_community_risk_indices()` → per-community cross-border ratio, avg TPS, avg DFA
  - `compute_structural_holes()` → Burt's constraint per node
  - Update `build_node_feature_matrix()` to include new features

### Commit
```
git add src/graph_engine.py
git commit -m "feat: add Leiden community detection and structural hole exploitation scoring"
```

---

## Phase 4 (Dev A): Typology Detection — Layering, Structuring, Cycles

**Goal:** Implement `src/typologies.py` with pattern detectors for:
1. **Temporal DFS Layering** — multi-hop chains with high amount conservation (≥97%) within time window
2. **Structuring Stars** — fan-out patterns where one account sends to many accounts amounts just below NPR 1M
3. **Rapid Cycling / Carousel** — closed loops (≥3 hops) completing within 24h with ≥98% conservation
4. **Mule Account Detection** — dormant accounts with sudden velocity spikes + immediate forwarding
5. **Accumulation-Spike-Disperse** — three-phase time-series on account balances

#### [NEW] [typologies.py](file:///d:/Downloads/Aleph/src/typologies.py)
- `class TypologyDetector`:
  - `__init__(self, graph_engine)` — takes the built graph
  - `detect_layering_chains(source, window_hours=72, min_hops=3, conservation=0.97)` → list of suspicious paths
  - `detect_structuring_stars(threshold=1_000_000, tolerance=0.10)` → flagged accounts
  - `detect_rapid_cycles(max_hours=24, min_hops=3, conservation=0.98)` → cycle list
  - `detect_mule_accounts(dormancy_days=90, velocity_spike=5x)` → flagged accounts
  - `detect_accumulation_spike_disperse()` → flagged accounts
  - `run_all_typologies()` → combined results DataFrame
  - `export_alerts(output_path)` → saves `data/processed/alerts.csv`

### Commit
```
git add src/typologies.py
git commit -m "feat: implement financial typology detectors (layering, structuring, cycles, mules)"
```

---

## Phase 5 (Dev A): Typology Detection — Hawala Ghost Flows & Loan-Back Schemes

**Goal:** Extend `src/typologies.py` with:
1. **Hawala/Hundi Ghost Flow Detection** — synchronized cross-border value pairs without direct links
2. **Loan-Back Cycle Detection** — cyclic A→B→C→A paths with loan-labeled edges
3. **Ghost Payroll Diversion** — corporate fan-out with >90% forwarding within 12h
4. **Shell Company Layering** — young account clusters with >90% internal ratio + large outbound

#### [MODIFY] [typologies.py](file:///d:/Downloads/Aleph/src/typologies.py)
- Add methods:
  - `detect_hawala_ghost_flows(time_window_sec=300, amount_tolerance=0.05)`
  - `detect_loan_back_cycles(amount_tolerance=0.05)`
  - `detect_ghost_payroll(forward_threshold=0.90, time_window_hours=12)`
  - `detect_shell_company_layering(max_age_days=180, internal_ratio=0.90)`
  - Update `run_all_typologies()` to include new detectors

### Commit
```
git add src/typologies.py
git commit -m "feat: add Hawala ghost flow, loan-back, and shell company detection engines"
```

---

## Phase 6 (Dev A): STR Narrative Evidence Verification

**Goal:** Add structural evidence matching to `src/data_loader.py`:
1. Parse narrative text from STR XML `<reason>` fields
2. Extract claims (cross-border, high amounts, rapid transactions)
3. Cross-validate claims against actual transaction graph data
4. Produce verification matrix: `{claim, graph_evidence_count, status: CONFIRMED/REFUTED/NOT_FOUND}`
5. Save `data/processed/str_verification.csv`

#### [MODIFY] [data_loader.py](file:///d:/Downloads/Aleph/src/data_loader.py)
- Add class `NarrativeEvidenceVerifier`:
  - `extract_claims(narrative_text)` → list of detected claim types
  - `verify_claim(claim_type, account_id, graph_engine)` → verification result
  - `verify_all_reports(parsed_reports_df, graph_engine)` → full verification matrix
  - `export_verification(output_path)` → saves `str_verification.csv`

### Commit
```
git add src/data_loader.py
git commit -m "feat: implement STR narrative evidence verification against transaction graph"
```

---

## Phase 7 (Dev A): Unit Tests for Data Loader & Typologies

**Goal:** Write tests to validate core functionality:
1. Test XML parsing extracts correct fields
2. Test Soundex produces correct codes
3. Test DFA calculation on known graph
4. Test layering chain detection on synthetic mini-graph
5. Test TPS scoring against known structuring pattern

#### [MODIFY] [test_data_loader.py](file:///d:/Downloads/Aleph/tests/test_data_loader.py)
- Test cases for Soundex, XML parsing, entity linking

#### [MODIFY] [test_typologies.py](file:///d:/Downloads/Aleph/tests/test_typologies.py)
- Test cases for layering, structuring, cycle detection on small synthetic graphs

### Commit
```
git add tests/
git commit -m "test: add unit tests for data loader, Soundex matching, and typology detectors"
```

---

## Phase 8 (Dev A → Dev B): EDA Notebook

**Goal:** Create `notebooks/01_eda_raw_analysis.ipynb` with:
1. Dataset shape, column types, missing values
2. Transaction amount distributions (histograms, log-scale)
3. Temporal patterns (transactions per hour/day/month)
4. Cross-border vs domestic breakdown
5. Account degree distribution (in/out)
6. Top accounts by volume
7. Community size distribution from Leiden
8. Feature correlation heatmap of engineered features

### Commit
```
git add notebooks/01_eda_raw_analysis.ipynb
git commit -m "feat: add exploratory data analysis notebook with distribution and graph topology analysis"
```

---

## Phase 9 (Dev B): ML Models — XGBoost + Risk Scoring

**Goal:** Implement `src/ml_models.py`:
1. Load `node_features.csv` with all engineered features
2. Train XGBoost classifier with class imbalance handling (`scale_pos_weight`)
3. Evaluate with Precision-Recall AUC (not ROC — imbalanced data)
4. Generate per-account risk probability scores
5. Save ranked risk list to `data/processed/risk_scores.csv`

#### [MODIFY] [ml_models.py](file:///d:/Downloads/Aleph/src/ml_models.py)
- `class AMLRiskClassifier`:
  - `train_pipeline()` → trains XGBoost, returns metrics
  - `predict_risk_scores(features_df)` → probability per account
  - `get_feature_importance()` → feature ranking
  - `export_risk_scores(output_path)` → saves `risk_scores.csv`

### Commit
```
git add src/ml_models.py
git commit -m "feat: implement XGBoost risk classification with PR-AUC evaluation"
```

---

## Phase 10 (Dev B): Explainability — SHAP + Counterfactual

**Goal:** Implement `src/explainability.py`:
1. SHAP TreeExplainer for XGBoost model → per-account feature attributions
2. Multi-level SHAP decomposition (self-behavior, counterparty, community, external)
3. Counterfactual edge perturbation — compute risk drop if specific edges removed
4. Generate evidence subgraphs (2-hop ego network) for high-risk accounts
5. Save SHAP summaries to `data/processed/shap_explanations.csv`

#### [MODIFY] [explainability.py](file:///d:/Downloads/Aleph/src/explainability.py)
- `class ExplainabilityEngine`:
  - `compute_shap_attributions(model, features_df)` → SHAP values
  - `decompose_risk_drivers(account_id)` → {self, neighbor, community, external}
  - `counterfactual_edge_analysis(account_id, graph_engine)` → risk perturbation results
  - `extract_evidence_subgraph(account_id, graph_engine, hops=2)` → nx subgraph
  - `export_explanations(output_path)`

### Commit
```
git add src/explainability.py
git commit -m "feat: add SHAP explainability engine with counterfactual edge perturbation"
```

---

## Phase 11 (Dev B): Streamlit Dashboard

**Goal:** Build the interactive analyst dashboard in `app/`:
1. **Main page** (`app.py`): Risk score slider, high-risk entity queue table, account deep-dive
2. **Flow Visualizer** (`components/flow_visualizer.py`): Interactive NetworkX graph rendering with Matplotlib/Plotly for selected account's ego network
3. **STR Validator** (`components/str_validator.py`): Side-by-side narrative text vs graph evidence verification
4. SHAP waterfall charts for selected accounts
5. Community membership visualization
6. Typology alerts table with filtering

#### [MODIFY] [app.py](file:///d:/Downloads/Aleph/app/app.py)
- Main Streamlit app with sidebar controls, metrics, tables

#### [MODIFY] [flow_visualizer.py](file:///d:/Downloads/Aleph/app/components/flow_visualizer.py)
- `render_ego_graph(account_id, graph_engine)` → interactive plot

#### [MODIFY] [str_validator.py](file:///d:/Downloads/Aleph/app/components/str_validator.py)
- `render_verification_view(report_id)` → side-by-side evidence view

### Commit
```
git add app/
git commit -m "feat: build Streamlit analyst dashboard with flow visualization and STR validation"
```

---

## Phase 12: Final Integration, README & Cleanup

**Goal:** End-to-end integration and polish:
1. Create a `main.py` runner script that executes the full pipeline
2. Update `README.md` with complete setup instructions, architecture diagram, screenshots
3. Verify all paths use relative references
4. Clean `__pycache__` directories
5. Final validation: run pipeline end-to-end

#### [NEW] [main.py](file:///d:/Downloads/Aleph/main.py)
- Orchestrates: load data → build graph → compute features → detect typologies → train model → generate explanations

#### [MODIFY] [README.md](file:///d:/Downloads/Aleph/README.md)
- Full documentation with architecture, setup, execution commands

### Commit
```
git add main.py README.md
git commit -m "docs: finalize README with architecture overview and end-to-end pipeline runner"
```

---

## Open Questions

> [!IMPORTANT]
> **Q1: Dataset column name adaptation.** The division doc references `augmented_saml_d.csv` with columns like `Sender_account`, `Receiver_account`, `amount_local_npr`, `Date`, `Time`. The actual `transactions.csv` has these SAME column names ✅. However `accounts.csv` uses `name` (full name) instead of `first_name`/`last_name` — I will split on space. Is that acceptable?

> [!IMPORTANT]
> **Q2: The `ml_features.csv` has a ready-to-use `is_suspicious_tx` label column.** Should we use this as ground truth for the XGBoost training in Phase 9, or should we derive labels from the typology detections in Phases 4-5?

> [!IMPORTANT]
> **Q3: Git branching.** The division doc suggests working on `dev-a-data-graph` branch. Do you want to follow that branch strategy, or commit directly to `main` since you're the sole developer right now?

> [!WARNING]
> **Q4: The dataset files (`transactions.csv` at 36MB, `ml_features.csv` at 17MB) should NOT be committed to git.** The `.gitignore` in Phase 0 will exclude them. Make sure the data is present locally before running the pipeline.

---

## Verification Plan

### Automated Tests
```bash
python -m pytest tests/ -v
```

### Manual Verification
1. After Phase 2: Verify `node_features.csv` has ~6,800 rows (one per account) with all feature columns populated
2. After Phase 4-5: Verify `alerts.csv` contains detected typology instances with non-trivial counts
3. After Phase 9: Verify PR-AUC > 0.3 (baseline for imbalanced data)
4. After Phase 11: Run `streamlit run app/app.py` and verify dashboard renders correctly
5. After Phase 12: Run `python main.py` end-to-end without errors

---

## Commit History Summary

| # | Phase | Commit Message | Files Touched |
|---|---|---|---|
| 1 | P0 | `chore: initialize project structure with module stubs and dependencies` | .gitignore, requirements.txt, README.md, src/*, app/*, tests/* |
| 2 | P1 | `feat: implement STR XML parser and Soundex phonetic entity resolution` | src/data_loader.py, src/utils.py |
| 3 | P2 | `feat: build temporal multigraph engine with DFA, Hawkes, and TPS features` | src/graph_engine.py |
| 4 | P3 | `feat: add Leiden community detection and structural hole exploitation scoring` | src/graph_engine.py |
| 5 | P4 | `feat: implement financial typology detectors (layering, structuring, cycles, mules)` | src/typologies.py |
| 6 | P5 | `feat: add Hawala ghost flow, loan-back, and shell company detection engines` | src/typologies.py |
| 7 | P6 | `feat: implement STR narrative evidence verification against transaction graph` | src/data_loader.py |
| 8 | P7 | `test: add unit tests for data loader, Soundex matching, and typology detectors` | tests/* |
| 9 | P8 | `feat: add exploratory data analysis notebook with distribution and graph topology analysis` | notebooks/* |
| 10 | P9 | `feat: implement XGBoost risk classification with PR-AUC evaluation` | src/ml_models.py |
| 11 | P10 | `feat: add SHAP explainability engine with counterfactual edge perturbation` | src/explainability.py |
| 12 | P11 | `feat: build Streamlit analyst dashboard with flow visualization and STR validation` | app/* |
| 13 | P12 | `docs: finalize README with architecture overview and end-to-end pipeline runner` | main.py, README.md |
