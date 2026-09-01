# SAT-SA — Scale & Performance Engineering Benchmark Report

> **Empirical Performance Verification**: All figures below represent actual runtime measurements executed on local hardware across progressive scale tiers.

---

## 1. Scale Tiers Summary Table

| Scale Tier | Records | Data Size | Ingest / Insert Time | Analytics Time | Total Pipeline Time | Throughput | Peak RAM | DB Size | Findings | Queue | Nodes / Edges | Status |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| **Tier (1M records)** | 1,000,000 | 243.0 MB | 1231.96s | 741.16s | 1973.12s | **506.8 rec/s** | 3666.4 MB | 841.0 MB | 495 | 10 | 1,000,390 / 1,000,375 | `PASS` |

---

## 2. Analytical Stage Breakdown

| Scale Tier | Execution Gap | Negative Space | Evidence Assembly | Risk Engine | Prioritization | Graph Construction |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier (1M records)** | 329.64s | 205.83s | 0.05s | 0.55s | 0.30s | 204.83s |
