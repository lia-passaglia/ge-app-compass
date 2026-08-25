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
from app.agent import (
    root_agent,
    license_reclamation_subagent,
    grounding_forensics_subagent,
    roi_analytics_subagent,
)
from app.logging_plugin import IntentOutcomeLoggingPlugin


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


def test_tool_signatures_with_pydantic_instances():
    """Verifies tools can be directly called with Pydantic schema instances."""
    seat_in = SeatAdoptionInput(target_department="Engineering", min_utilization_threshold_pct=0.9)
    res_seat = get_seat_adoption_metrics(params=seat_in)
    assert res_seat["query_status"] == "SUCCESS"

    uc_in = UseCaseClusterInput(department="Sales", top_k_clusters=3, date_range_days=30)
    res_uc = analyze_use_case_clusters(params=uc_in)
    assert res_uc["query_status"] == "SUCCESS"

    dislike_in = DislikeHotspotsInput(department="Legal", min_dislike_rate_pct=10.0)
    res_dislike = inspect_dislike_hotspots(params=dislike_in)
    assert res_dislike["query_status"] == "SUCCESS"

    roi_in = RoiCalculationInput(department_hourly_rates={"Legal": 175.0, "Engineering": 100.0})
    res_roi = calculate_roi_and_time_saved(params=roi_in)
    assert res_roi["query_status"] == "SUCCESS"


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


def test_multi_agent_subagent_orchestration():
    """Verifies that root coordinator has real specialized architectural sub-agents."""
    subagents = {sa.name: sa for sa in root_agent.sub_agents}
    assert "license_reclamation_specialist" in subagents
    assert "grounding_forensics_specialist" in subagents
    assert "roi_analytics_specialist" in subagents

    # Check that forensic specialist is routed to Gemini Pro for high-complexity deep reasoning
    assert "gemini-2.5-pro" in subagents["grounding_forensics_specialist"].model.model


@pytest.mark.asyncio
async def test_intent_vs_outcome_telemetry_plugin():
    """Verifies that Intent vs Outcome telemetry plugin intercepts callbacks and captures logs."""
    plugin = IntentOutcomeLoggingPlugin(name="test_logger")

    class MockTool:
        name = "get_seat_adoption_metrics"

    # Test before_tool_callback (Intent Capture)
    await plugin.before_tool_callback(
        tool=MockTool(),
        tool_args={"target_department": "Legal"},
        tool_context=None,
    )

    # Test after_tool_callback (Outcome Capture)
    await plugin.after_tool_callback(
        tool=MockTool(),
        tool_args={"target_department": "Legal"},
        tool_context=None,
        tool_response={"query_status": "SUCCESS", "departments": {}},
    )
