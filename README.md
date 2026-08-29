# SAT-SA — Smart Assessment Tool for Security Analytics

> "SAT-SA is an offline, evidence-first supervisory intelligence platform that detects both improper SOC execution and missing expected evidence, compares behaviour with peers, and prioritizes cases for human examination."

## Overview
SAT-SA is an offline, supervisory analytics platform used by NCIIPC-style examiners to evaluate Critical Sector Entities (CSEs) based on operational evidence (alerts, investigations, escalations, closures, asset profiles).

## Features & Innovation Pillars
1. **Negative Space Intelligence Engine**: Detects missing expected evidence and visibility gaps with context validation.
2. **Supervisory Evidence Graph Engine**: Network graph model (`CSE -> Asset -> Alert -> Investigation -> Analyst -> Escalation -> Case -> Closure`) to surface broken or anomalous workflow paths.
3. **Peer-Relative Risk**: Statistical benchmarking against defensible peer groups (sector, size, asset profile).
4. **Decomposable Supervisory Risk Score**: Fully additive and transparent score breakdown (+Execution Gap, +Negative Space, +Peer Deviation, +Investigation Anomaly, +Asset Criticality).
5. **Review Prioritization Engine**: Multi-criteria ranking with diversity sampling constraints to select high-value cases for human review.
6. **Evidence-First AI**: Layered local-only ML (Isolation Forest, K-Means clustering, local NLP) with full provenance and reproducibility (`DatasetImport -> AnalysisRun -> RuleVersion/ModelVersion -> Finding -> Evidence`).

## Architecture & Technology Stack
- **Frontend**: React 18, TypeScript, Vite, Tailwind/Vanilla CSS, Recharts, Network Visualization
- **Backend**: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL, Pandas, NumPy, scikit-learn, NetworkX
- **Deployment**: Pure local offline Docker containerization (`docker-compose.yml`)

## Quickstart (Local Dev)
1. **Backend**:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Docker (Offline Production Stack)**:
   ```bash
   docker-compose up --build
   ```
