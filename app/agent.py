# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pathlib
import logging
import google.auth
from google.cloud import bigquery

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Import native ADK Skills modules
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

# Import our custom BigQuery analytical tools
from .tools import (
    get_seat_adoption_metrics,
    analyze_use_case_clusters,
    inspect_dislike_hotspots,
    calculate_roi_and_time_saved,
)

# Set up Cloud environment variables
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    pass

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Load local skills into ADK Skills Registry
skills_dir = pathlib.Path(__file__).parent / "skills"
if not skills_dir.exists():
    skills_dir = pathlib.Path(__file__).parent.parent / "skills"

skills = [
    load_skill_from_dir(skills_dir / "license-reclamation"),
    load_skill_from_dir(skills_dir / "grounding-forensics"),
    load_skill_from_dir(skills_dir / "roi-analysis"),
]

# Instantiate SkillToolset with custom tools passed as additional_tools (dynamically registered upon skill load)
skill_toolset = SkillToolset(
    skills=skills,
    additional_tools=[
        get_seat_adoption_metrics,
        analyze_use_case_clusters,
        inspect_dislike_hotspots,
        calculate_roi_and_time_saved,
    ]
)

# Eval-compatible subclass of Agent to handle Toolset serialization in local evaluator
class CompassAgent(Agent):
    def __getattribute__(self, name):
        if name == "tools":
            import inspect
            try:
                stack = inspect.stack()
                is_eval = False
                for frame in stack:
                    if (
                        frame.function == "_get_tool_declarations_from_agent" or
                        "vertexai" in frame.filename or
                        "eval" in frame.filename
                    ):
                        is_eval = True
                        break
                if is_eval:
                    # Return flat tools list for the evaluator to serialize
                    flat_tools = []
                    # Core skill tools
                    flat_tools.extend(skill_toolset._tools)
                    # Custom additional tools wrapped as FunctionTools
                    flat_tools.extend(list(skill_toolset._provided_tools_by_name.values()))
                    return flat_tools
            except Exception:
                pass
        return super().__getattribute__(name)

# Core ge-app-compass Agent Definition
root_agent = CompassAgent(
    name="ge_app_compass",
    model=Gemini(
        model="gemini-3.7-flash",  # Upgraded to Gemini 3.7 Flash per request
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Gemini Adoption Compass (ge-app-compass), an autonomous enterprise audit agent. "
        "Your mission is to audit Gemini license adoption, analyze usage clusters, diagnose feedback quality dislikes, "
        "and calculate corporate ROI from telemetry logs.\n\n"
        "Crucial Operating Rules:\n"
        "1. Start by listing your available skills to find the most relevant one for the user request.\n"
        "2. Once a relevant skill is selected, you MUST load it using load_skill(name='<skill-name>').\n"
        "3. Loading a skill automatically registers and unlocks its corresponding specialized tools in your active context.\n"
        "4. Follow the skill instructions and utilize its dynamically bound tools to satisfy the request.\n"
        "5. Present reports using rich aesthetics, clear markdown tables, and premium scorecards (e.g., total savings in bold, green highlights if helpful)."
    ),
    tools=[skill_toolset],
)

# Initialize BigQuery Analytics Plugin for Observability
_plugins = []
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", project_id)
_dataset_id = os.environ.get("BQ_ANALYTICS_DATASET_ID", "ge_app_compass_telemetry") # Unified ge_app_compass_telemetry dataset
_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if _project_id:
    try:
        from google.adk.plugins.bigquery_agent_analytics_plugin import (
            BigQueryAgentAnalyticsPlugin,
            BigQueryLoggerConfig,
        )
        bq = bigquery.Client(project=_project_id)
        bq.create_dataset(f"{_project_id}.{_dataset_id}", exists_ok=True)

        _plugins.append(
            BigQueryAgentAnalyticsPlugin(
                project_id=_project_id,
                dataset_id=_dataset_id,
                location=_location,
                config=BigQueryLoggerConfig(
                    gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET"),
                    connection_id=os.environ.get("BQ_ANALYTICS_CONNECTION_ID"),
                ),
            )
        )
    except Exception as e:
        logging.warning(f"Failed to initialize BigQuery Analytics: {e}")

# ADK App initialization
app = App(
    root_agent=root_agent,
    name="app",  # Matches the directory name 'app' to avoid session failures in local evaluation
    plugins=_plugins,
)
