# 🧭 Gemini Adoption Compass (`ge-app-compass`)

> **Autonomous Enterprise Audit Agent for Gemini Adoption, Grounding Forensics, and Financial ROI Analysis.**

[![CI/CD Pipeline](https://github.com/lia-passaglia/ge-app-compass/actions/workflows/deploy_staging.yaml/badge.svg)](https://github.com/lia-passaglia/ge-app-compass/actions)
[![Agent Runtime Deployed](https://img.shields.io/badge/Vertex%20AI-Reasoning%20Engines-blue)](https://cloud.google.com/vertex-ai)

---

## 📖 Description & Purpose

Enterprises deploying **Gemini Enterprise / Gemini Apps** often face three critical operational challenges:
1. **License Inefficiencies**: Underutilized or idle seat assignments causing wasted SaaS spending.
2. **Quality & Grounding Gaps**: High user dislike rates due to missing corporate grounding sources (e.g., contracts, pricing catalogs, internal wikis).
3. **ROI Quantification**: Difficulty measuring real hours saved and executive-level financial value delivered by generative AI.

**Gemini Adoption Compass (`ge-app-compass`)** is an autonomous audit agent built on Google's **Agent Development Kit (ADK)** and powered by **Gemini 3.7 Flash / Pro**. It integrates directly with Google Cloud telemetry to continuously audit seat utilization, cluster semantic user prompts, diagnose negative feedback hotspots, and generate executive-grade ROI reports with built-in Human-in-the-Loop governance.

---

## 🎯 Specialized Skills & Use Cases

`ge-app-compass` utilizes modular ADK **`SkillToolset`** dynamic capability loading to provide specialized analytical workflows:

```
                                  ┌────────────────────────┐
                                  │  ge-app-compass Root   │
                                  │  (Gemini 3.7 Flash)    │
                                  └───────────┬────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
         ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
         │ License Reclamation │   │ Grounding Forensics │   │    ROI Analysis     │
         │        Skill        │   │        Skill        │   │        Skill        │
         └──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘
                    │                         │                         │
                    ▼                         ▼                         ▼
         • Seat Adoption Audit     • Prompt Clustering       • Hours Saved Model
         • 40% Benchmark Filter    • Dislike Hotspot Root-   • Custom Hourly Rates
         • Human-in-the-Loop Sign-   Cause Analysis          • Executive Financial
           off for De-provisioning • Connector Linking Plan    Scorecards
```

### 1. 🪪 License Reclamation (`license-reclamation`)
* **Purpose**: Discovers seat adoption across departments, identifies teams with active utilization below corporate benchmark thresholds (e.g., < 40%), and plans license reallocation.
* **Key Tools**: `get_seat_adoption_metrics`, `request_human_license_reclamation_approval`
* **Human-in-the-Loop**: High-stakes license de-provisioning triggers a gated confirmation flow requiring explicit administrator approval (`confirmed_by_admin=True`) before executing changes.

### 2. 🔍 Grounding Forensics (`grounding-forensics`)
* **Purpose**: Identifies why users hit "thumbs down" on Gemini responses by performing semantic clustering on user prompt logs and analyzing negative feedback themes.
* **Key Tools**: `analyze_use_case_clusters`, `inspect_dislike_hotspots`
* **Data Privacy**: Automatic real-time redaction of SSNs, credit cards, and API keys, alongside SHA-256 email hashing (`hash_email`).
* **Output**: Prescriptive remediation plans recommending specific Google Cloud connectors (e.g., Google Drive, GCS buckets, BigQuery datasets).

### 3. 💰 Corporate ROI Analysis (`roi-analysis`)
* **Purpose**: Quantifies productivity gains by calculating monthly prompts processed, active employee hours saved, and financial value in USD across business units.
* **Key Tools**: `calculate_roi_and_time_saved`
* **Customization**: Supports dynamic departmental hourly rate overrides (e.g., Legal: $150/hr, Engineering: $80/hr).

---

## 📊 Enterprise Telemetry & Data Sources

`ge-app-compass` integrates seamlessly with GCP enterprise telemetry pipelines:

* **BigQuery Telemetry Logs**: Queries partitioned Gemini Enterprise user activity logs (`discoveryengine_googleapis_com_gemini_enterprise_user_activity_*`) in dataset `ge_observability`.
* **ADK BigQuery Agent Analytics Plugin**: Real-time event logging capturing session traces, tool inputs/outputs, and user feedback into `ge_app_compass_telemetry`.
* **Cloud Trace & OpenTelemetry**: Distributed tracing spans instrumenting every LLM call, tool invocation, and latency metric.
* **PII Redaction Engine**: In-memory regex scrubbing and deterministic hashing ensuring zero raw PII is exposed to LLM context or logs.

---

## 🎬 End-to-End Demo Flows

### Flow 1: License Adoption Audit & Human-in-the-Loop Reclamation
```text
User: "Audit our Gemini license utilization across all departments and reclaim idle seats."

Agent: 
1. Loads skill `license-reclamation`
2. Calls `get_seat_adoption_metrics(min_utilization_threshold_pct=0.40)`
3. Returns Department Adoption Scorecard:
   • Engineering: 82.0% (410/500 active) — Low priority
   • Sales:       25.0% (75/300 active)  — HIGH priority (225 idle seats)
   • Marketing:   15.0% (30/200 active)  — HIGH priority (170 idle seats)
   • Legal:       10.0% (5/50 active)    — HIGH priority (45 idle seats)
4. Initiates Human-in-the-Loop Hook:
   Status: PENDING_HUMAN_CONFIRMATION
   "Reclaiming 440 seats across Sales, Marketing, and Legal will save $13,200/month.
   Do you approve de-provisioning these licenses? Reply 'Approve' to proceed."
```

### Flow 2: Grounding Diagnostics & Data Connector Setup
```text
User: "Why are our legal and sales teams giving negative feedback on Gemini responses?"

Agent:
1. Loads skill `grounding-forensics`
2. Calls `inspect_dislike_hotspots()` and `analyze_use_case_clusters()`
3. Delivers Root Cause Analysis:
   • Legal (30% dislike rate): Prompts around contract reviews lack private knowledge grounding.
     → Remediation: Connect GCS Contract Vault bucket via Vertex AI Search.
   • Sales (34% dislike rate): Prompts around RFPs use stale Q3 product data.
     → Remediation: Ingest real-time BigQuery pricing catalog connector.
```

### Flow 3: Executive ROI & Financial Impact Summary
```text
User: "Generate our executive ROI report for Q3 with custom Legal rates of $175/hr."

Agent:
1. Loads skill `roi-analysis`
2. Calls `calculate_roi_and_time_saved(department_hourly_rates={"Legal": 175.0})`
3. Renders Executive Scorecard:
   ┌─────────────────────────────────────────────────────────────┐
   │ 🌟 Total Hours Saved: 5,160.0 hrs                           │
   │ 💵 Total Monthly Savings: $354,800.00                       │
   └─────────────────────────────────────────────────────────────┘
   • Detailed breakdown by Engineering, Sales, Marketing, HR, and Legal.
```

---

## 🚀 Quick Start & Local Testing

### Prerequisites
- Python 3.11+ / 3.12 / 3.13 with [uv](https://docs.astral.sh/uv/)
- Google Cloud SDK (`gcloud`) authenticated to project `passaglia-demos`

```bash
# 1. Install dependencies
agents-cli install

# 2. Run the interactive web playground
agents-cli playground

# 3. Run the automated test suite (14 unit & integration tests)
uv run pytest
```

---

## 🚢 Deployment & CI/CD

`ge-app-compass` uses automated GitHub Actions CI/CD with Workload Identity Federation (WIF) and Terraform IaC:

| Environment | Platform | Status |
|---|---|---|
| **Staging / Dev** | Vertex AI Reasoning Engines (`us-central1`) | **Deployed & Active** |
| **CI/CD** | GitHub Actions (`deploy_staging.yaml`) | **Passing** |
| **IaC** | Terraform in `deployment/terraform/cicd` | **Applied** |

To query the live deployed Reasoning Engine in Python:

```python
import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="passaglia-demos", location="us-central1")
agent = reasoning_engines.ReasoningEngine(
    "projects/991026205836/locations/us-central1/reasoningEngines/4203694086999244800"
)

# Stream responses live from Vertex AI
for event in agent.stream_query(message="Run a department seat audit", user_id="admin"):
    print(event)
```
