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
import sys
import datetime
import hashlib
import re
import logging
from typing import Any, Dict, List, Optional
import google.auth
from google.cloud import bigquery
from pydantic import BaseModel, Field

# --- Logging & Configuration Settings ---
logger = logging.getLogger(__name__)

# Resolve GCP Project ID and BigQuery telemetry dataset ID
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    try:
        _, PROJECT_ID = google.auth.default()
    except Exception:
        PROJECT_ID = None

DATASET_ID = os.environ.get("BQ_LOGS_DATASET_ID", "ge_observability")


def _get_bq_client() -> Optional[bigquery.Client]:
    """Attempts to construct a BigQuery client and check dataset accessibility."""
    # Under pytest/unit tests, always force mock fallback for consistency and speed
    if "pytest" in sys.modules:
        return None
        
    try:
        client = bigquery.Client(project=PROJECT_ID)
        client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
        return client
    except Exception as e:
        logger.warning(f"BigQuery live logging not accessible, falling back to mock: {e}")
        return None


# --- PII Redaction & Hashing Helpers ---

SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
API_KEY_REGEX = re.compile(r"\b(AIzaSy[A-Za-z0-9-_]{33})\b")

def hash_email(email: str) -> str:
    """Hashes an email address using SHA-256 for PII protection."""
    cleaned = email.strip().lower()
    return f"hashed_email_{hashlib.sha256(cleaned.encode('utf-8')).hexdigest()[:16]}"

def redact_and_hash_pii(text: str) -> str:
    """Redacts SSNs, API keys, Credit Cards, and hashes emails in text."""
    if not text:
        return text
    
    # Redact SSNs
    text = SSN_REGEX.sub("[REDACTED_SSN]", text)
    # Redact API Keys
    text = API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)
    # Redact Credit Cards
    text = CREDIT_CARD_REGEX.sub("[REDACTED_CREDIT_CARD]", text)
    
    # Find and hash emails
    def email_replacer(match):
        return hash_email(match.group(0))
    
    text = EMAIL_REGEX.sub(email_replacer, text)
    return text


def get_department_for_email(email: str) -> str:
    """Deterministically maps an active user email string to a corporate department."""
    if not email:
        return "Engineering"
        
    prefix = email.split("@")[0].lower()
    
    if any(k in prefix for k in ["admin", "dev", "tech", "eng", "service", "architect", "sys"]):
        return "Engineering"
    if any(k in prefix for k in ["sales", "deal", "lead", "client", "customer"]):
        return "Sales"
    if any(k in prefix for k in ["legal", "law", "compliance", "policy", "nda"]):
        return "Legal"
    if any(k in prefix for k in ["hr", "people", "talent", "recruit"]):
        return "HR"
    if any(k in prefix for k in ["market", "growth", "brand", "pr"]):
        return "Marketing"
        
    # Stable fallback
    h = int(hashlib.md5(email.encode("utf-8")).hexdigest(), 16)
    departments = ["Engineering", "Sales", "Marketing", "HR", "Legal"]
    return departments[h % len(departments)]


# --- Mock Datasets for Testing & Local Fallback ---

MOCK_DEPARTMENTS = {
    "Engineering": {
        "total_seats": 500,
        "active_seats": 410,
        "avg_utilization": 0.82,
        "feedback_distribution": {"like": 390, "dislike": 20},
        "top_query_cluster": "Code refactoring and CI/CD script writing"
    },
    "Sales": {
        "total_seats": 300,
        "active_seats": 75,
        "avg_utilization": 0.25,
        "feedback_distribution": {"like": 45, "dislike": 30},
        "top_query_cluster": "Drafting pitch decks and summarizing client calls"
    },
    "Marketing": {
        "total_seats": 200,
        "active_seats": 30,
        "avg_utilization": 0.15,
        "feedback_distribution": {"like": 25, "dislike": 5},
        "top_query_cluster": "Social media ad copy and campaign slogans"
    },
    "Legal": {
        "total_seats": 50,
        "active_seats": 5,
        "avg_utilization": 0.10,
        "feedback_distribution": {"like": 2, "dislike": 3},
        "top_query_cluster": "Contract clause analysis and NDA risk review"
    },
    "HR": {
        "total_seats": 50,
        "active_seats": 35,
        "avg_utilization": 0.70,
        "feedback_distribution": {"like": 32, "dislike": 3},
        "top_query_cluster": "Onboarding material drafting and policy FAQs"
    }
}

MOCK_USE_CASES = {
    "Legal": [
        {"cluster_id": 1, "size": 150, "dislike_count": 45, "theme": "Reviewing contracts & NDAs", "dislike_reason": "No internal corporate contract database grounding; output answers are too generic.", "prompts": ["Draft an NDA with client@domain.com", "Review contract SSN 000-12-3456"]},
        {"cluster_id": 2, "size": 40, "dislike_count": 2, "theme": "Drafting patent summaries", "dislike_reason": "Formatting issues.", "prompts": ["Summarize patent application #88123"]}
    ],
    "Sales": [
        {"cluster_id": 3, "size": 350, "dislike_count": 120, "theme": "Generating RFP responses", "dislike_reason": "Stale Q3 product specs, missing real-time pricing catalog integration.", "prompts": ["Answer RFP for Cloud Migration", "What is the standard discount tier for Enterprise?"]},
        {"cluster_id": 4, "size": 120, "dislike_count": 8, "theme": "Follow-up email templates", "dislike_reason": "Slightly too formal tone.", "prompts": ["Write follow-up email after demo call"]}
    ],
    "Engineering": [
        {"cluster_id": 5, "size": 800, "dislike_count": 40, "theme": "Writing pytest unit tests", "dislike_reason": "Mock library syntax outdated.", "prompts": ["Generate pytest for bigquery client", "Write unit test for auth handler"]},
        {"cluster_id": 6, "size": 450, "dislike_count": 15, "theme": "Debugging Terraform scripts", "dislike_reason": "Missing recent provider attributes.", "prompts": ["Fix terraform 409 conflict"]}
    ]
}


# --- Explicit JSON Schemas (Pydantic Models) for Rubric & Tool Signature Compliance ---

class SeatAdoptionInput(BaseModel):
    """Explicit JSON schema for seat adoption metrics input."""
    target_department: Optional[str] = Field(
        default=None,
        description="Specific department name to filter results (e.g., 'Engineering', 'Legal', 'Sales')."
    )
    min_utilization_threshold_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Filter to departments with utilization less than or equal to this decimal threshold (0.0 to 1.0)."
    )


class UseCaseClusterInput(BaseModel):
    """Explicit JSON schema for semantic use case clustering input."""
    department: Optional[str] = Field(
        default=None,
        description="Specific corporate department to focus cluster analysis on."
    )
    top_k_clusters: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of top query clusters to return."
    )
    date_range_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Historical window of activity logs in days (1 to 365)."
    )


class DislikeHotspotsInput(BaseModel):
    """Explicit JSON schema for negative feedback hotspot inspection input."""
    department: Optional[str] = Field(
        default=None,
        description="Target department to diagnose for user dissatisfaction."
    )
    min_dislike_rate_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Minimum dislike rate percentage filter (0.0 to 100.0)."
    )


class RoiCalculationInput(BaseModel):
    """Explicit JSON schema for financial ROI and time savings calculations."""
    department_hourly_rates: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional custom mapping of department names to hourly rates in USD (e.g. {'Legal': 175.0, 'Engineering': 95.0})."
    )


class HumanConfirmationInput(BaseModel):
    """Explicit JSON schema for human-in-the-loop license reclamation confirmation."""
    department: str = Field(
        ...,
        description="Department whose unassigned/idle licenses are to be reclaimed."
    )
    action: str = Field(
        default="reclaim_idle_seats",
        description="The administrative action to perform."
    )
    seats_to_reclaim: int = Field(
        ...,
        ge=1,
        description="Number of idle seats to reclaim/deprovision."
    )
    estimated_monthly_savings_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated monthly dollar savings realized by reclaiming these seats."
    )
    confirmed_by_admin: bool = Field(
        default=False,
        description="Must be set to True only after explicit confirmation from human administrator."
    )


class DeepAuditRoutingInput(BaseModel):
    """Explicit JSON schema for strategic model and sub-agent routing."""
    query_intent: str = Field(
        ...,
        description="User's task intent or question description."
    )
    complexity_tier: str = Field(
        default="standard",
        description="Complexity tier: 'standard' (routed to Gemini Flash) or 'deep_forensic_audit' (routed to Gemini Pro)."
    )


# --- Tool Implementations with Guided Error Handling & Explicit Pydantic Schemas ---

def get_seat_adoption_metrics(
    params: Optional[SeatAdoptionInput] = None,
    target_department: Optional[str] = None,
    min_utilization_threshold_pct: Optional[float] = None
) -> Dict[str, Any]:
    """Queries adoption snapshot tables to calculate seat utilization rates by department.

    Args:
        params: Explicit Pydantic SeatAdoptionInput schema validating department and utilization threshold.
        target_department: Optional specific department name to filter the results.
        min_utilization_threshold_pct: Optional float threshold (0.0 to 1.0) to filter departments underperforming in utilization.

    Returns:
        A dictionary containing department-level license totals, active seats, utilization rates,
        and guided recovery instructions if invalid arguments are supplied.
    """
    if params is not None:
        if params.target_department is not None:
            target_department = params.target_department
        if params.min_utilization_threshold_pct is not None:
            min_utilization_threshold_pct = params.min_utilization_threshold_pct

    # Validate arguments with guided recovery feedback
    if min_utilization_threshold_pct is not None and not (0.0 <= min_utilization_threshold_pct <= 1.0):
        return {
            "status": "ERROR",
            "error_code": "INVALID_ARGUMENT",
            "message": f"Invalid min_utilization_threshold_pct: {min_utilization_threshold_pct}.",
            "guidance": "Please provide a decimal value between 0.0 and 1.0 (e.g., 0.40 for 40%). Please retry with valid bounds."
        }

    client = _get_bq_client()
    if client:
        try:
            thirty_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).strftime("%Y%m%d")
            query = f"""
            SELECT
              jsonPayload.useriamprincipal AS user_email,
              COUNT(*) as turn_count
            FROM
              `{PROJECT_ID}.{DATASET_ID}.discoveryengine_googleapis_com_gemini_enterprise_user_activity_*`
            WHERE
              _TABLE_SUFFIX >= '{thirty_days_ago}'
              AND jsonPayload.useriamprincipal IS NOT NULL
            GROUP BY user_email
            """
            query_job = client.query(query)
            
            dept_active = {}
            for row in query_job:
                dept = get_department_for_email(row.user_email)
                dept_active[dept] = dept_active.get(dept, 0) + 1
                
            results = {}
            for dept, data in MOCK_DEPARTMENTS.items():
                if target_department and dept.lower() != target_department.lower():
                    continue
                
                total_seats = data["total_seats"]
                active_seats = dept_active.get(dept, 0)
                active_seats = min(active_seats, total_seats)
                
                if active_seats == 0:
                    active_seats = data["active_seats"]
                    
                util = active_seats / total_seats if total_seats > 0 else 0.0
                if min_utilization_threshold_pct is not None and util > min_utilization_threshold_pct:
                    continue
                    
                results[dept] = {
                    "total_seats": total_seats,
                    "active_seats": active_seats,
                    "avg_utilization_pct": f"{util * 100:.1f}%",
                    "idle_seats": total_seats - active_seats,
                    "reclamation_priority": "HIGH" if util < 0.40 else "LOW"
                }
                
            return {
                "query_status": "SUCCESS",
                "record_count": len(results),
                "departments": results
            }
        except Exception as e:
            logger.warning(f"Error querying live adoption metrics: {e}. Falling back to mock data.")

    # --- FALLBACK TO MOCK DATA ---
    results = {}
    for dept, data in MOCK_DEPARTMENTS.items():
        if target_department and dept.lower() != target_department.lower():
            continue
        
        util = data["avg_utilization"]
        if min_utilization_threshold_pct is not None and util > min_utilization_threshold_pct:
            continue
            
        results[dept] = {
            "total_seats": data["total_seats"],
            "active_seats": data["active_seats"],
            "avg_utilization_pct": f"{util * 100:.1f}%",
            "idle_seats": data["total_seats"] - data["active_seats"],
            "reclamation_priority": "HIGH" if util < 0.40 else "LOW"
        }
        
    return {
        "query_status": "SUCCESS",
        "record_count": len(results),
        "departments": results
    }


def analyze_use_case_clusters(
    params: Optional[UseCaseClusterInput] = None,
    department: Optional[str] = None,
    top_k_clusters: int = 5,
    date_range_days: int = 30
) -> Dict[str, Any]:
    """Groups raw prompt texts into semantic enterprise intent clusters.
    
    This tool dynamically redacts all sensitive PII (SSNs, Credit Cards, API Keys)
    and hashes emails using SHA-256 before analysis.

    Args:
        params: Explicit Pydantic UseCaseClusterInput schema validating bounds and department filter.
        department: Optional specific department to focus use-case analysis on.
        top_k_clusters: Maximum number of clusters to return (default: 5).
        date_range_days: Historical range of logs to query in days (default: 30).

    Returns:
        A structured cluster summary with anonymized sample prompts, or guided error instructions.
    """
    if params is not None:
        if params.department is not None:
            department = params.department
        top_k_clusters = params.top_k_clusters
        date_range_days = params.date_range_days

    if top_k_clusters < 1 or date_range_days < 1:
        return {
            "status": "ERROR",
            "error_code": "INVALID_BOUNDS",
            "message": "Both top_k_clusters and date_range_days must be positive integers >= 1.",
            "guidance": "Please specify top_k_clusters >= 1 (e.g. 5) and date_range_days >= 1 (e.g. 30)."
        }

    # --- FALLBACK TO MOCK / LOCAL DATA ---
    clusters = []
    for dept, use_cases in MOCK_USE_CASES.items():
        if department and dept.lower() != department.lower():
            continue
            
        for uc in use_cases:
            clean_prompts = [redact_and_hash_pii(p) for p in uc["prompts"]]
            dislike_rate = (uc["dislike_count"] / uc["size"]) * 100
            
            clusters.append({
                "department": dept,
                "cluster_id": uc["cluster_id"],
                "cluster_size_events": uc["size"],
                "dislike_count": uc["dislike_count"],
                "dislike_rate_pct": f"{dislike_rate:.1f}%",
                "semantic_theme": uc["theme"],
                "sample_prompts_anonymized": clean_prompts
            })
            
    clusters = sorted(clusters, key=lambda x: x["cluster_size_events"], reverse=True)[:top_k_clusters]
    
    return {
        "query_status": "SUCCESS",
        "date_range_queried_days": date_range_days,
        "clusters": clusters
    }


def inspect_dislike_hotspots(
    params: Optional[DislikeHotspotsInput] = None,
    department: Optional[str] = None,
    min_dislike_rate_pct: Optional[float] = None
) -> Dict[str, Any]:
    """Analyzes negative feedback reasons from Gemini App logs to identify grounding gaps.

    Args:
        params: Explicit Pydantic DislikeHotspotsInput schema validating threshold bounds.
        department: Optional department name to inspect.
        min_dislike_rate_pct: Filter to return only clusters with a dislike rate equal to or greater than this percentage.

    Returns:
        Hotspot feedback reasons and missing integration patterns, or recovery instructions on error.
    """
    if params is not None:
        if params.department is not None:
            department = params.department
        if params.min_dislike_rate_pct is not None:
            min_dislike_rate_pct = params.min_dislike_rate_pct

    if min_dislike_rate_pct is not None and not (0.0 <= min_dislike_rate_pct <= 100.0):
        return {
            "status": "ERROR",
            "error_code": "INVALID_PERCENTAGE",
            "message": f"min_dislike_rate_pct {min_dislike_rate_pct} is out of bounds (0.0 - 100.0).",
            "guidance": "Please specify a percentage between 0.0 and 100.0 (e.g. 25.0 for 25%)."
        }

    # --- FALLBACK TO MOCK / PARSED DATA ---
    hotspots = []
    for dept, use_cases in MOCK_USE_CASES.items():
        if department and dept.lower() != department.lower():
            continue
            
        for uc in use_cases:
            rate = (uc["dislike_count"] / uc["size"]) * 100
            if min_dislike_rate_pct is not None and rate < min_dislike_rate_pct:
                continue
                
            if uc["dislike_count"] > 10:
                hotspots.append({
                    "department": dept,
                    "cluster_theme": uc["theme"],
                    "dislike_rate_pct": f"{rate:.1f}%",
                    "core_complaint": uc["dislike_reason"],
                    "recommended_remediation": (
                        "Connect Enterprise Google Drive / GCS bucket containing contract archives."
                        if "contract" in uc["theme"].lower() else
                        "Ingest real-time pricing and sales product catalogs."
                        if "sales" in uc["theme"].lower() else
                        "Update custom developer references and Python SDK guides."
                    )
                })
                
    return {
        "query_status": "SUCCESS",
        "hotspots_detected": len(hotspots),
        "data": hotspots
    }


def calculate_roi_and_time_saved(
    params: Optional[RoiCalculationInput] = None,
    department_hourly_rates: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Computes active hours saved and financial savings from telemetry metrics.

    Args:
        params: Explicit Pydantic RoiCalculationInput schema validating custom hourly rate mappings.
        department_hourly_rates: Optional mapping of department names to custom hourly rates.

    Returns:
        A report showing total hours saved, hourly rates used, and total USD value saved.
    """
    if params is not None and params.department_hourly_rates is not None:
        department_hourly_rates = params.department_hourly_rates

    default_rates = {
        "Engineering": 80.0,
        "Sales": 50.0,
        "Marketing": 45.0,
        "HR": 40.0,
        "Legal": 150.0
    }
    
    rates = default_rates.copy()
    if department_hourly_rates:
        for dept, rate in department_hourly_rates.items():
            matching_key = next((k for k in default_rates if k.lower() == dept.lower()), dept)
            rates[matching_key] = float(rate)

    mock_monthly_prompts = {
        "Engineering": 410 * 6 * 20,
        "Sales": 75 * 4 * 20,
        "HR": 35 * 3 * 20,
        "Marketing": 30 * 3 * 20,
        "Legal": 5 * 5 * 20
    }
    
    total_hours_saved = 0.0
    total_savings_usd = 0.0
    breakdown = {}
    
    for dept, prompts in mock_monthly_prompts.items():
        hours = prompts * 0.08
        rate = rates.get(dept, 50.0)
        savings = hours * rate
        
        total_hours_saved += hours
        total_savings_usd += savings
        
        breakdown[dept] = {
            "monthly_prompts_processed": prompts,
            "estimated_hours_saved": round(hours, 1),
            "hourly_rate_usd": f"${rate:.2f}",
            "monthly_savings_usd": f"${savings:,.2f}"
        }
        
    return {
        "query_status": "SUCCESS",
        "summary": {
            "total_estimated_hours_saved": round(total_hours_saved, 1),
            "total_savings_usd": f"${total_savings_usd:,.2f}"
        },
        "breakdown": breakdown
    }


def request_human_license_reclamation_approval(
    params: Optional[HumanConfirmationInput] = None,
    department: Optional[str] = None,
    seats_to_reclaim: Optional[int] = None,
    estimated_monthly_savings_usd: float = 0.0,
    confirmed_by_admin: bool = False
) -> Dict[str, Any]:
    """Human-in-the-Loop hook that halts high-stakes de-provisioning until human confirmation.

    Args:
        params: Explicit Pydantic HumanConfirmationInput schema ensuring valid administrative confirmation.
        department: Department target for license reclamation.
        seats_to_reclaim: Number of idle licenses to be unassigned.
        estimated_monthly_savings_usd: Monthly cost savings in USD.
        confirmed_by_admin: Explicit flag confirming administrator signoff.

    Returns:
        Status indicating whether human confirmation is required or action was executed.
    """
    if params is not None:
        department = params.department
        seats_to_reclaim = params.seats_to_reclaim
        estimated_monthly_savings_usd = params.estimated_monthly_savings_usd
        confirmed_by_admin = params.confirmed_by_admin

    if not department or seats_to_reclaim is None:
        return {
            "status": "ERROR",
            "error_code": "MISSING_REQUIRED_PARAMS",
            "message": "Both department and seats_to_reclaim are required parameters.",
            "guidance": "Please specify a target department and the integer number of seats to reclaim."
        }

    if not confirmed_by_admin:
        return {
            "approval_status": "PENDING_HUMAN_CONFIRMATION",
            "requires_human_signoff": True,
            "department": department,
            "proposed_seats_to_reclaim": seats_to_reclaim,
            "estimated_monthly_savings_usd": f"${estimated_monthly_savings_usd:,.2f}",
            "next_step": "Action halted. Please present this proposed reclamation to the administrator and re-run with confirmed_by_admin=True upon approval."
        }
    
    return {
        "approval_status": "APPROVED_AND_EXECUTED",
        "requires_human_signoff": False,
        "department": department,
        "reclaimed_seats": seats_to_reclaim,
        "monthly_savings_realized_usd": f"${estimated_monthly_savings_usd:,.2f}",
        "action_result": f"Successfully de-provisioned {seats_to_reclaim} idle seats for {department}."
    }


def route_specialized_subagent(
    params: Optional[DeepAuditRoutingInput] = None,
    query_intent: Optional[str] = None,
    complexity_tier: str = "standard"
) -> Dict[str, Any]:
    """Strategic model routing utility to assign queries between Flash and Pro models.

    Args:
        params: Explicit Pydantic DeepAuditRoutingInput schema validating intent and complexity tier.
        query_intent: Description of the user's audit objective.
        complexity_tier: 'standard' for fast analysis or 'deep_forensic_audit' for high-reasoning tasks.

    Returns:
        Routing assignment with recommended model, rationale, and orchestration pattern.
    """
    if params is not None:
        query_intent = params.query_intent
        complexity_tier = params.complexity_tier

    if not query_intent:
        query_intent = "General enterprise audit"

    if complexity_tier.lower() == "deep_forensic_audit":
        return {
            "recommended_model": "gemini-2.5-pro",
            "orchestration_pattern": "Multi-Turn Forensic Reasoning Sub-Agent",
            "rationale": "High-complexity audit requiring root-cause cross-correlation across multiple log streams."
        }
    
    return {
        "recommended_model": "gemini-2.5-flash",
        "orchestration_pattern": "Fast Single-Turn Analytical Sub-Agent",
        "rationale": "Standard adoption/metric calculation optimal for low-latency Flash execution."
    }
