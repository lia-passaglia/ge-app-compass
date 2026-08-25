---
name: license-reclamation
description: Instructions and tools for auditing Gemini App seat utilization and reclaiming idle licenses.
metadata:
  adk_additional_tools:
    - get_seat_adoption_metrics
---

# License Reclamation Skill

This skill helps you audit, flag, and process Gemini Enterprise seat utilization across corporate departments.

## Operating Instructions

1. **Discovery & Audit**:
   - Use the `get_seat_adoption_metrics` tool to scan all departments for seat utilization.
   - Look for departments with **under 40% active seat utilization** (which is our corporate benchmark threshold).
2. **Reclamation Targeting**:
   - Departments with under 40% utilization must be highlighted as **HIGH** reclamation priority.
   - Calculate potential licenses to reclaim: `idle_seats = total_seats - active_seats`.
3. **Presenting the Plan**:
   - Generate a clear markdown table listing departments, total seats, active seats, utilization percentages, idle seats, and reclamation priority.
   - Recommend corporate communication steps (using the playbook located in `references/reclamation_playbook.md` as reference).
