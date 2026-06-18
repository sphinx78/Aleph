# AMLIOS-X: Anti-Money Laundering Intelligence Operating System

**AI/ML Intelligence Hackathon 2026**  
Track 3: Network & Graph Intelligence

---

## Overview

AMLIOS-X is an integrated financial knowledge graph, temporal network analyzer, and risk-prioritization system designed to detect structured financial crime. It models ~1,000,000 transactions across ~6,800 accounts as a continuous-time directed multigraph and applies multi-layer analysis spanning 14 specialized processing layers.

## Architecture

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

## Setup

```bash
# Clone the repository
git clone <repository-url>
cd Aleph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Data Setup

Place the dataset files in `data/STUDENT_DATASET/`:
- `transactions.csv` — Full transaction table
- `accounts.csv` — KYC records
- `graph_edges.csv` — Pre-built edge list
- `ml_features.csv` — Pre-engineered ML features
- `reports/` — STR XML reports (276 files)

> **Note:** Data files are git-ignored due to their size. Obtain them from the hackathon dataset distribution.

## Usage

```bash
# Run the full pipeline
python main.py

# Prepare dashboard outputs without model-training dependencies (fast run)
python main.py --no-train-model

# Launch the FastAPI backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Launch the React + Vite frontend
cd frontend
npm install
npm run dev

# (Legacy) Launch the Streamlit dashboard
streamlit run app/app.py
```


## Project Structure

```
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                    # End-to-end pipeline orchestrator
│
├── data/
│   ├── STUDENT_DATASET/       # Raw data (git-ignored)
│   └── processed/             # Pipeline outputs
│
├── notebooks/
│   └── 01_eda_raw_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # XML parsing & phonetic entity resolution
│   ├── graph_engine.py        # Temporal multigraph & feature extraction
│   ├── typologies.py          # Financial crime pattern detectors
│   ├── ml_models.py           # XGBoost risk classification
│   ├── explainability.py      # SHAP, counterfactuals, evidence subgraphs
│   └── utils.py               # Logging, constants, helpers
│
├── app/
│   ├── app.py                 # Streamlit dashboard entry point (Legacy)
│   ├── main.py                # FastAPI backend server
│   └── components/
│       ├── flow_visualizer.py # Money-flow graph rendering
│       └── str_validator.py   # STR narrative vs graph evidence
│
├── frontend/                  # React (Vite) Frontend application
│   ├── index.html             # Main HTML page template
│   ├── package.json           # Frontend dependencies & scripts
│   ├── postcss.config.js      # PostCSS configuration for Tailwind
│   ├── tailwind.config.js     # Tailwind CSS config
│   ├── vite.config.js         # Vite development server config
│   └── src/
│       ├── App.css
│       ├── App.jsx            # Core React root component
│       ├── index.css          # Tailwind directives & theme configuration
│       ├── main.jsx           # App entry point
│       ├── components/
│       │   ├── GlobeLanding.jsx      # Canvas-based 3D spinning globe landing state
│       │   ├── WorkspaceShell.jsx    # Dashboard navigation sidebar and header layout
│       │   ├── DynamicMetricCard.jsx # Mouse-pointer-tracking custom glow card
│       │   ├── LayeringAlluvial.jsx  # D3-rendered multi-hop transfer alluvial flow
│       │   ├── ClaimsVerification.jsx# Narrative vs. transaction evidence cross-check card
│       │   └── DashboardMain.jsx     # Master workspace layout & state controller
│       └── services/
│           └── apiService.js         # Backend fetch services client
│
└── tests/
    ├── test_data_loader.py
    └── test_typologies.py
```

## License

This project was developed for the AI/ML Intelligence Hackathon 2026.
