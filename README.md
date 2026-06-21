# ALEPH א Anti-Laundering Entity & Pattern Hunter
## AI/ML Intelligence Hackathon 2026 - Track 3: Network & Graph Intelligence

ALEPH is an enterprise-grade financial intelligence engine, continuous-time temporal network analyzer, and risk-prioritization system built to isolate structured money laundering networks. 

It processes **~1,000,000 transactions** across **~6,800 accounts** as a temporal multigraph, fusing rule-based typology alerts with graph embeddings and emulated GNN attention scores through a unified evidence-mesh architecture.

---

## System Architecture

```
Layer 1: Unified Knowledge Graph ──► Layer 2: Temporal Graph Engine ──► Layer 3: Feature Fabric
                                                                                │
Layer 6: Community Intelligence  ◄── Layer 5: Typology Classifier  ◄── Layer 4: Motif Mining
            │
            ▼
Layer 7: Graph Embeddings        ──► Layer 8: TGAT & Hetero GNN     ──► Layer 9: Risk Fusion
                                                                                │
Layer 12: Investigation Engine   ◄── Layer 11: Explainability       ◄── Layer 10: STR Intel
            │
            ▼
Layer 13: Analyst Copilot (LLM)  ──► Layer 14: Interactive Dashboard
```

---

## Core Features & Scientific Methods

* **Temporal Flow Modeling:** Models transactions as continuous-time timestamped edges. It tracks cash flow speed and decay using self-exciting **Hawkes Processes** and **Directed Flow Asymmetry (DFA)**.
* **Neo4j AuraDB Graph Integration:** Securely queries 2-hop undirected subgraphs via the official Neo4j Python Driver, capturing both inbound and outbound counterparties in a single Cypher traversal.
* **Force-Directed Topology Visualization:** Renders interactive counterparty networks using `react-force-graph-2d` wrapped in glassmorphic cards, featuring node role-coloring (Terracotta/Orange/Sage) and hover halos.
* **Streaming Graph RAG Copilot:** A Server-Sent Events (SSE) chat terminal powered by a local Ollama server running `llama3.1` to stream compliance insights token-by-token alongside built-in connectivity alerts.
* **Structuring Evasion Detection:** The **Threshold Proximity Score (TPS)** flags transaction frequencies structured right below regulatory reporting limits (NPR 1,000,000).
* **Soundex Entity Linking:** Resolves unstructured names in compliance narratives to database accounts using Soundex phonetic hashing and Levenshtein edit distance thresholds.
* **Dempster-Shafer Evidence Fusion:** Combines conflicting indicators (rule triggers, structural embeddings, and ML classifications) into a unified risk probability.
* **Explainable AI & Counterfactuals:** Decomposes risk profiles into SHAP attributions and simulates target risk reduction under hypothetical transaction deletions.

---

## Project Structure

```
├── .gitignore
├── .env.example               # Template for backend and LLM variables
├── README.md                  # Project documentation (this file)
├── architecture.md            # Deep-dive system specifications
├── explanation.md             # Core logic and line-by-line walks
├── commit_messages.md         # Commit registry & workflow guide
├── requirements.txt           # Python backend dependencies
├── main.py                    # End-to-end pipeline runner
│
├── data/
│   ├── STUDENT_DATASET/       # Raw transaction & KYC data (git-ignored)
│   └── processed/             # Pipeline metrics and output scores
│
├── notebooks/
│   └── 01_eda_raw_analysis.ipynb # Jupyter notebook for Exploratory Data Analysis
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # Soundex phonetic linkage & XML parser
│   ├── graph_engine.py        # Temporal graph structures & feature fabric
│   ├── typologies.py          # BFS/DFS chains, loops, Hawala, star detectors
│   ├── ml_models.py           # XGBoost training & metric evaluator
│   ├── explainability.py      # SHAP attribution & counterfactual edge calculations
│   └── utils.py               # Logging, constants, mathematical helpers
│
├── app/
│   ├── app.py                 # Streamlit visualizer (Legacy)
│   ├── main.py                # Asynchronous FastAPI backend server with SSE streaming
│   └── components/
│       ├── flow_visualizer.py # Network graph plotting utilities
│       └── str_validator.py   # Narrative claim alignment checks
│
├── frontend/                  # React (Vite) Frontend Application
│   ├── index.html             # Main HTML template
│   ├── package.json           # Frontend packages & scripts
│   ├── vite.config.js         # Dev server settings
│   └── src/
│       ├── App.jsx            # Core React root
│       ├── index.css          # Tailwind configurations & custom styles
│       ├── main.jsx           # App mounting entry point
│       ├── components/
│       │   ├── GlobeLanding.jsx      # Light-theme spinning orthographic globe
│       │   ├── WorkspaceShell.jsx    # Sidebar navigation & connection telemetry
│       │   ├── DynamicMetricCard.jsx # Mouse-tracking indicator widget
│       │   ├── AlephCard.jsx         # Custom glassmorphic mouse-tracking card
│       │   ├── LayeringAlluvial.jsx  # D3 alluvial transfer flow map
│       │   ├── ClaimsVerification.jsx# Narrative vs. transaction validator card
│       │   ├── ForceGraphPanel.jsx   # 2-hop Force Directed transaction network panel
│       │   ├── GraphRagCopilot.jsx   # Streaming RAG Chat assistant
│       │   └── DashboardMain.jsx     # Master workspace layout
│       └── services/
│           └── apiService.js         # API request client
│
└── tests/                     # Verification suite
    ├── test_data_loader.py
    └── test_typologies.py
```

---

## Setup & Running Instructions

### Backend & Database Configuration
1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   Fill in your Neo4j AuraDB credentials (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).

4. Ensure your local **Ollama** engine is running:
   ```bash
   ollama pull llama3.1
   ollama run llama3.1
   ```

5. Run the end-to-end data pipeline to train models and generate features:
   ```bash
   python main.py
   ```
6. Start the FastAPI backend server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

### Frontend Configuration & Launch
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```
3. Launch the React dev server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:5173](http://localhost:5173) in your browser to access the dashboard.

---

## Verification & Testing

Verify that all backend algorithms and modules execute correctly:
```bash
python -m pytest tests/ -v
```