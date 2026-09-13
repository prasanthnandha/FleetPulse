# FleetPulse — Project Specification

## 1. Overview

**FleetPulse** is an agentic system for enterprise Mobile Device Management (MDM). It predicts device health/compliance degradation (battery, patch lag, compliance drift) before failure, and helps IT ops act on it — retrieving the exact replacement part and repair procedure for the predicted failure via a RAG layer, all through a conversational web UI.

**Goal:** demonstrate end-to-end ML + agentic engineering skills — data pipelines, predictive modeling, RAG, tool-calling agents, MLOps/CI-CD, and serving — as a portfolio project for DS/AI/ML/GenAI Engineer roles.

**Required stack:** Databricks (PySpark, Delta Lake, MLflow, Unity Catalog, Model Serving, Vector Search), GitHub Actions (CI/CD), a chat-based web UI.

---

## 2. Problem Statement

Enterprises manage large device fleets via MDM tools (Intune, Jamf, Workspace ONE). Devices degrade over time — battery capacity fades, OS/security patches fall behind, apps crash more, compliance policies get violated. IT teams typically react only after failure or a compliance flag. FleetPulse predicts degradation *before* it's visible downstream, and tells IT ops what to do about it.

---

## 3. Datasets

| Purpose | Source | Notes |
|---|---|---|
| Battery degradation (core predictive signal) | NASA Li-ion Battery Aging dataset | Real, public, cycle-level voltage/current/temperature/capacity-fade data — genuinely sequential |
| Compliance/patch-lag risk layer | NVD (National Vulnerability Database) CVE feed | Used to derive "days since last patch" risk feature |
| Device specs / assembly parts (for RAG) | Synthetic catalog you generate (device model → component → part number → supplier) + public manufacturer spec sheets/service manual PDFs | No public "MDM parts catalog" exists — synthetic structured reference data is reasonable here since it's not simulating human behavior |

---

## 4. Architecture

### 4.1 Data & Feature Engineering
- PySpark job on Databricks ingests raw battery-cycle data + patch/CVE feed
- Computes rolling degradation features per device: capacity fade rate, cycle count, temperature exposure, days-since-patch, OS version lag
- Stored as Delta tables in Unity Catalog

### 4.2 Prediction Model
- Gradient-boosted regressor (XGBoost/LightGBM) predicts remaining useful battery life / days-to-non-compliance
- Isolation Forest as secondary anomaly flag (sudden drops — e.g., device compromise or misconfiguration)
- Experiment tracking via MLflow, model registered in Unity Catalog Model Registry
- Deployed to a **Databricks Model Serving** endpoint (real-time REST inference)

### 4.3 RAG Layer (device info + parts lookup)
- Ingestion pipeline: chunk manufacturer spec sheets/service manuals + synthetic parts catalog
- Embed with a sentence-transformer model
- Store/query via **Databricks Vector Search** (Unity Catalog-backed)
- Exposed to the agent as a tool: `get_device_repair_info(device_model, predicted_failure_component)` → returns part number, supplier, replacement procedure
- **Guardrail:** only return a part number if retrieval confidence clears a threshold; otherwise respond "no confident match — escalate to IT" rather than hallucinate

### 4.4 Agent Layer
- Tool-calling LLM orchestrates:
  1. **Prediction tool** — calls the Model Serving endpoint for a device/fleet
  2. **RAG tool** — retrieves part/repair info for the predicted failing component
  3. **Ticket-drafting tool** — drafts a remediation/replacement ticket
- Example flow: IT admin asks "Which devices in the Sales fleet need attention this week?" → agent ranks at-risk devices, explains the driving factor (battery vs. patch lag vs. compliance drift), retrieves the part/repair info, and drafts a ticket

### 4.5 CI/CD
- **Databricks Asset Bundles** (`databricks.yml`) define Jobs (feature pipeline, training, reindexing), Model Serving endpoint config, and Vector Search index as code
- **GitHub Actions** workflow: lint/test → `databricks bundle deploy` → triggers retraining/reindexing on schedule or on registry updates → redeploys serving endpoint

### 4.6 Web UI
- Chat interface (agent frontend) showing:
  - Natural-language Q&A ("Show me devices likely to fail compliance in 30 days")
  - Fleet-level risk dashboard/trend charts
  - Retrieved part/repair info alongside predictions

---

## 5. End-to-End Flow (example)

1. IT admin: *"Which devices in the Sales fleet need attention this week?"*
2. Agent calls **prediction endpoint** → Device X (iPhone 13) flagged: battery health trending to failure in ~18 days
3. Agent calls **RAG tool** → retrieves battery part number, supplier, estimated repair time for that exact device model
4. Agent responds with a synthesized answer and drafts a remediation ticket

---

## 6. Tech Stack Summary

- **Compute/Data:** Databricks, PySpark, Delta Lake, Unity Catalog
- **ML:** XGBoost/LightGBM, Isolation Forest, MLflow
- **Serving:** Databricks Model Serving
- **RAG:** Databricks Vector Search, sentence-transformer embeddings
- **Agent/Orchestration:** Tool-calling LLM (Claude, via Antigravity for dev)
- **CI/CD:** Databricks Asset Bundles + GitHub Actions
- **Frontend:** Chat-based web UI

---

## 7. Suggested Build Order

1. Data ingestion + feature engineering pipeline (PySpark/Databricks)
2. Prediction model training + MLflow tracking + registry
3. Model Serving endpoint deployment
4. Synthetic parts catalog + manuals corpus → Vector Search index
5. Agent tool-calling layer (prediction tool + RAG tool + ticket tool)
6. Web UI (chat interface)
7. Databricks Asset Bundle definitions
8. GitHub Actions CI/CD pipeline
9. End-to-end testing + guardrail/eval pass
