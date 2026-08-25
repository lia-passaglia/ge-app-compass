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

from app.tools import (
    hash_email,
    redact_and_hash_pii,
    get_seat_adoption_metrics,
    analyze_use_case_clusters,
    inspect_dislike_hotspots,
    calculate_roi_and_time_saved,
)

def test_hash_email():
    """Verifies that emails are hashed consistently and properly anonymized."""
    email1 = "test@example.com"
    email2 = " TEST@example.com "
    
    hash1 = hash_email(email1)
    hash2 = hash_email(email2)
    
    assert hash1.startswith("hashed_email_")
    assert len(hash1) == len("hashed_email_") + 16
    assert hash1 == hash2  # Case insensitivity & stripping
    assert email1 not in hash1


def test_redact_and_hash_pii():
    """Verifies that sensitive data patterns are redacted and emails are hashed in text."""
    # Test SSN redaction
    text_ssn = "My SSN is 123-45-6789 and my colleague's is 987-65-4321."
    clean_ssn = redact_and_hash_pii(text_ssn)
    assert "[REDACTED_SSN]" in clean_ssn
    assert "123-45-6789" not in clean_ssn
    assert "987-65-4321" not in clean_ssn
    
    # Test Credit Card redaction
    text_cc = "The credit card number is 4111 1111 1111 1111 or 1234-5678-1234-5678."
    clean_cc = redact_and_hash_pii(text_cc)
    assert "[REDACTED_CREDIT_CARD]" in clean_cc
    assert "4111" not in clean_cc
    
    # Test Email Hashing in text
    text_email = "Contact help@company.com or sales@domain.com."
    clean_email = redact_and_hash_pii(text_email)
    assert "help@company.com" not in clean_email
    assert "sales@domain.com" not in clean_email
    assert "hashed_email_" in clean_email


def test_get_seat_adoption_metrics():
    """Verifies seat utilization metrics and department filtering."""
    # Test all departments
    all_metrics = get_seat_adoption_metrics()
    assert all_metrics["query_status"] == "SUCCESS"
    assert "Engineering" in all_metrics["departments"]
    assert "Legal" in all_metrics["departments"]
    
    # Test specific target department filtering
    eng_metrics = get_seat_adoption_metrics(target_department="Engineering")
    assert eng_metrics["record_count"] == 1
    assert "Engineering" in eng_metrics["departments"]
    assert "Legal" not in eng_metrics["departments"]
    
    # Test minimum utilization threshold filtering
    low_util = get_seat_adoption_metrics(min_utilization_threshold_pct=0.30)
    # Legal has 10% utilization (< 30%), Sales has 25% (< 30%). Engineering has 82% (> 30%).
    assert "Legal" in low_util["departments"]
    assert "Sales" in low_util["departments"]
    assert "Engineering" not in low_util["departments"]


def test_analyze_use_case_clusters():
    """Verifies semantic use-case clustering and PII clean-up in output."""
    clusters_report = analyze_use_case_clusters(top_k_clusters=2)
    assert clusters_report["query_status"] == "SUCCESS"
    assert len(clusters_report["clusters"]) <= 2
    
    # Ensure that any sample prompts returned are fully cleaned up of SSNs & raw emails
    for cluster in clusters_report["clusters"]:
        for prompt in cluster["sample_prompts_anonymized"]:
            assert "000-12-3456" not in prompt
            assert "legal@google.com" not in prompt
            if "NDA" in prompt:
                assert "[REDACTED_SSN]" in prompt or "hashed_email_" in prompt


def test_inspect_dislike_hotspots():
    """Verifies identifying negative feedback hotspots and corresponding integrations."""
    hotspots = inspect_dislike_hotspots(min_dislike_rate_pct=25.0)
    assert hotspots["query_status"] == "SUCCESS"
    assert hotspots["hotspots_detected"] > 0
    
    # Legal and Sales should appear since they have high dislike counts / rates
    departments_with_hotspots = [h["department"] for h in hotspots["data"]]
    assert "Legal" in departments_with_hotspots or "Sales" in departments_with_hotspots


def test_calculate_roi_and_time_saved():
    """Verifies that ROI is calculated properly using default and custom rates."""
    # Test with default rates
    roi_default = calculate_roi_and_time_saved()
    assert roi_default["query_status"] == "SUCCESS"
    assert roi_default["summary"]["total_estimated_hours_saved"] > 0
    
    # Test with custom hourly rates
    custom_rates = {"Engineering": 100.0, "Legal": 200.0}
    roi_custom = calculate_roi_and_time_saved(department_hourly_rates=custom_rates)
    
    assert roi_custom["breakdown"]["Engineering"]["hourly_rate_usd"] == "$100.00"
    assert roi_custom["breakdown"]["Legal"]["hourly_rate_usd"] == "$200.00"
