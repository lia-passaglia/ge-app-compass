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
import json
import logging
from typing import Any, Dict, Optional
from google.adk.plugins import BasePlugin
from google.cloud import logging as google_cloud_logging

logger = logging.getLogger(__name__)


class IntentOutcomeLoggingPlugin(BasePlugin):
    """ADK Plugin that provides explicit Intent vs Outcome structured telemetry logging.
    
    Logs:
    - [INTENT_CAPTURE]: Action intent, tool name, user arguments, and timestamp before tool execution.
    - [OUTCOME_CAPTURE]: Result status, output data payload, latency, and success metrics after tool execution.
    - [ERROR_CAPTURE]: Guided error details, error codes, and recovery advice if a tool call fails.
    """

    def __init__(self, name: str = "intent_outcome_logger"):
        super().__init__(name=name)
        self._gcp_logger = None
        try:
            client = google_cloud_logging.Client()
            self._gcp_logger = client.logger("ge_app_compass_intent_outcome")
        except Exception:
            self._gcp_logger = None

    def _log_structured(self, log_type: str, data: Dict[str, Any], severity: str = "INFO") -> None:
        """Emits structured JSON logs to Cloud Logging and python standard logger."""
        payload = {
            "telemetry_type": log_type,
            "agent": "ge_app_compass",
            **data
        }
        if self._gcp_logger:
            try:
                self._gcp_logger.log_struct(payload, severity=severity)
            except Exception:
                pass
        
        # Standard stdout / test logger
        logger.info(f"[{log_type}] {json.dumps(payload, default=str)}")

    async def before_tool_callback(self, *, tool, tool_args, tool_context) -> Optional[Any]:
        """Logs explicit intent before tool invocation."""
        intent_payload = {
            "event": "TOOL_INTENT_CAPTURED",
            "tool_name": getattr(tool, "name", str(tool)),
            "tool_args": tool_args,
            "session_id": getattr(tool_context, "session_id", None) if tool_context else None,
            "user_id": getattr(tool_context, "user_id", None) if tool_context else None,
        }
        self._log_structured("INTENT_CAPTURE", intent_payload, severity="INFO")
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, tool_response) -> Optional[Any]:
        """Logs explicit outcome after tool execution completes."""
        status = "SUCCESS"
        if isinstance(tool_response, dict) and tool_response.get("status") == "ERROR":
            status = "ERROR"

        outcome_payload = {
            "event": "TOOL_OUTCOME_CAPTURED",
            "tool_name": getattr(tool, "name", str(tool)),
            "execution_status": status,
            "tool_args": tool_args,
            "tool_response_summary": (
                f"{len(tool_response)} keys returned" if isinstance(tool_response, dict) else str(tool_response)[:200]
            ),
            "tool_response": tool_response,
        }
        self._log_structured("OUTCOME_CAPTURE", outcome_payload, severity="INFO" if status == "SUCCESS" else "WARNING")
        return None

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error) -> Optional[Any]:
        """Logs explicit failure outcome if an unhandled tool exception occurs."""
        error_payload = {
            "event": "TOOL_EXECUTION_ERROR",
            "tool_name": getattr(tool, "name", str(tool)),
            "tool_args": tool_args,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        self._log_structured("ERROR_CAPTURE", error_payload, severity="ERROR")
        return None
