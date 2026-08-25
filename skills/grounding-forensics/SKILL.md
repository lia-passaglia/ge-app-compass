---
name: grounding-forensics
description: Instructions and tools for inspecting dislike hotspots and identifying grounding/connector gaps.
metadata:
  adk_additional_tools:
    - inspect_dislike_hotspots
    - analyze_use_case_clusters
---

# Grounding Forensics Skill

This skill helps you diagnose quality feedback, analyze semantic prompt clusters, and resolve high dislike rates by suggesting missing grounding data stores.

## Operating Instructions

1. **Analyze Prompt Clusters**:
   - Call the `analyze_use_case_clusters` tool to see the semantic distribution of user queries.
   - Note the average dislike counts and semantic themes.
2. **Diagnose Dislike Hotspots**:
   - Call the `inspect_dislike_hotspots` tool to locate clusters/departments with high negative feedback rates.
   - Examine the `core_complaint` column (e.g., generic answers, missing private knowledge).
3. **Determine Remediation Actions**:
   - Recommend a connector linking plan (using `references/connector_setup_guide.md` as reference).
   - Format a remediation plan with concrete data connector steps (GCS, Drive, or BigQuery connectors).
