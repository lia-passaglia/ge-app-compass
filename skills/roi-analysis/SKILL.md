---
name: roi-analysis
description: Instructions and tools for calculating corporate ROI and productivity time saved.
metadata:
  adk_additional_tools:
    - calculate_roi_and_time_saved
---

# ROI Analysis Skill

This skill helps you model, compute, and report financial ROI and productivity hours saved across corporate departments utilizing Gemini Apps.

## Operating Instructions

1. **Calculate ROI**:
   - Call the `calculate_roi_and_time_saved` tool to run the standard productivity calculations.
   - If the user specifies custom department hourly rates, pass them in as key-value pairs (e.g., `{"Engineering": 90, "Legal": 180}`).
2. **Compile Report**:
   - Show the total estimated hours saved and total monthly financial savings in a prominent, premium scorecard section.
   - Provide a department breakdown showing monthly prompts, hours saved, and cost savings.
   - Summarize the business impact and efficiency gains for executive presentation.
