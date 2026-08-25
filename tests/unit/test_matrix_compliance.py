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

import pytest
from pydantic import ValidationError
from app.tools import (
    SeatAdoptionInput,
    UseCaseClusterInput,
    DislikeHotspotsInput,
    RoiCalculationInput,
    HumanConfirmationInput,
    DeepAuditRoutingInput,
    get_seat_adoption_metrics,
    analyze_use_case_clusters,
    inspect_dislike_hotspots,
    calculate_roi_and_time_saved,
    request_human_license_reclamation_approval,
    route_specialized_subagent,
    hash_email,
    redact_and_hash_pii,
)


def test_schema_validations():
    """Verifies strict Pydantic JSON schema constraints on all tool inputs."""
    # Valid input passes
    valid_seat = SeatAdoptionInput(target_department="Sales", min_utilization_threshold_pct=0.4)
    assert valid_seat.target_department == "Sales"

    # Invalid utilization threshold (> 1.0) raises ValidationError
    with pytest.raises(ValidationError):
        SeatAdoptionInput(min_utilization_threshold_pct=1.5)

    # Valid use case input
    valid_cluster = UseCaseClusterInput(top_k_clusters=5, date_range_days=60)
    assert valid_cluster.top_k_clusters == 5

    # Invalid top_k (< 1)
    with pytest.raises(ValidationError):
        UseCaseClusterInput(top_k_clusters=0)

    # Valid human confirmation
    valid_human = HumanConfirmationInput(
        department="Legal",
        action="reclaim_idle_seats",
        seats_to_reclaim=10,
        confirmed_by_admin=True,
    )
    assert valid_human.seats_to_reclaim == 10

    # Negative seats raises ValidationError
    with pytest.raises(ValidationError):
        HumanConfirmationInput(
            department="Legal",
            action="reclaim_idle_seats",
            seats_to_reclaim=-5,
            confirmed_by_admin=True,
        )


def test_guided_error_recovery():
    """Verifies that tools return actionable error guidance instead of crashing on invalid input."""
    # Test error recovery for negative threshold
    res = get_seat_adoption_metrics(min_utilization_threshold_pct=-0.5)
    assert res["status"] == "ERROR"
    assert "guidance" in res
    assert "decimal value" in res["guidance"]

    # Test error recovery for negative date range
    res_uc = analyze_use_case_clusters(date_range_days=-10)
    assert res_uc["status"] == "ERROR"
    assert "guidance" in res_uc

    # Test error recovery for invalid dislike threshold
    res_dislike = inspect_dislike_hotspots(min_dislike_rate_pct=150.0)
    assert res_dislike["status"] == "ERROR"
    assert "guidance" in res_dislike


def test_human_in_the_loop_approval():
    """Verifies that high-stakes actions halt and require human confirmation."""
    # Unconfirmed action stops execution and requests human admin signoff
    unconfirmed = request_human_license_reclamation_approval(
        department="Legal",
        seats_to_reclaim=45,
        estimated_monthly_savings_usd=1350.0,
        confirmed_by_admin=False,
    )
    assert unconfirmed["approval_status"] == "PENDING_HUMAN_CONFIRMATION"
    assert unconfirmed["requires_human_signoff"] is True
    assert "action_blocked" in unconfirmed["next_step"].lower() or "halted" in unconfirmed["next_step"].lower()

    # Confirmed action executes successfully
    confirmed = request_human_license_reclamation_approval(
        department="Legal",
        seats_to_reclaim=45,
        estimated_monthly_savings_usd=1350.0,
        confirmed_by_admin=True,
    )
    assert confirmed["approval_status"] == "APPROVED_AND_EXECUTED"
    assert confirmed["reclaimed_seats"] == 45


def test_strategic_model_routing():
    """Verifies dynamic model routing between Gemini Flash and Gemini Pro based on complexity."""
    # Fast query routes to gemini-2.5-flash
    fast_route = route_specialized_subagent(
        query_intent="Quick seat summary for Engineering",
        complexity_tier="standard",
    )
    assert fast_route["recommended_model"] == "gemini-2.5-flash"

    # Deep audit routes to gemini-2.5-pro
    deep_route = route_specialized_subagent(
        query_intent="Complex forensic analysis of dislike causes across contracts and multi-year ROI modeling",
        complexity_tier="deep_forensic_audit",
    )
    assert deep_route["recommended_model"] == "gemini-2.5-pro"
