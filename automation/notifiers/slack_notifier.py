"""Slack Incoming Webhook Dispatcher with Block Kit formatting.

Provides structured multi-block notifications for vehicle failure risk,
critical telemetry sensor anomalies, and service demand surges.
Falls back to deterministic mock logging if SLACK_WEBHOOK_URL is unset.
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional
import urllib.request
import urllib.error

from automation.config import (
    SLACK_WEBHOOK_URL,
    SLACK_CHANNEL,
    DISPATCH_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Dispatches Block Kit formatted messages to Slack incoming webhooks."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url if webhook_url is not None else SLACK_WEBHOOK_URL

    def build_failure_risk_block(
        self,
        vehicle_id: str,
        risk_score: float,
        threshold: float,
        top_features: Dict[str, float],
        action_id: str,
    ) -> Dict[str, Any]:
        """Build Slack Block Kit payload for Rule 1: High Vehicle Failure Risk."""
        features_str = ", ".join([f"{k}: {v:.2f}" for k, v in list(top_features.items())[:3]])
        return {
            "channel": SLACK_CHANNEL,
            "text": f"🚨 High Failure Risk Alert: Vehicle {vehicle_id} (P={risk_score:.2f})",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 High Vehicle Failure Risk Alert: {vehicle_id}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Vehicle ID:*\n`{vehicle_id}`"},
                        {"type": "mrkdwn", "text": f"*Predicted Risk:*\n`{risk_score * 100:.1f}%` (Threshold: {threshold * 100:.0f}%)"},
                        {"type": "mrkdwn", "text": f"*Top Drivers:*\n{features_str or 'N/A'}"},
                        {"type": "mrkdwn", "text": f"*Action Taken:*\nInspection Work-Order Drafted"},
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Action ID: `{action_id}` | Model: `vehicle_failure_risk_rf:v1.0.0`"},
                    ],
                },
            ],
        }

    def build_sensor_anomaly_block(
        self,
        vehicle_id: str,
        anomaly_score: float,
        threshold: float,
        telemetry_values: Dict[str, float],
        consecutive_count: int,
        action_id: str,
        dtc_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build Slack Block Kit payload for Rule 2: Critical Sensor Anomaly."""
        trigger_reason = f"DTC Fault Trigger: `{dtc_code}`" if dtc_code else f"{consecutive_count} Consecutive Anomalous Pings"
        return {
            "channel": SLACK_CHANNEL,
            "text": f"⚠️ Critical Telemetry Anomaly: Vehicle {vehicle_id} (Score={anomaly_score:.4f})",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⚠️ Critical Sensor Telemetry Alert: {vehicle_id}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Vehicle ID:*\n`{vehicle_id}`"},
                        {"type": "mrkdwn", "text": f"*Normalized Score:*\n`{anomaly_score:.4f}` (Frozen Thresh: `{threshold:.4f}`)"},
                        {"type": "mrkdwn", "text": f"*Trigger Cause:*\n{trigger_reason}"},
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"*Telemetry:* RPM={telemetry_values.get('rpm', 0):.0f}, "
                                f"Temp={telemetry_values.get('temperature', 0):.1f}°C, "
                                f"Vib={telemetry_values.get('vibration', 0):.2f}g"
                            ),
                        },
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Action ID: `{action_id}` | Governed Model: `sensor_anomaly_iforest:v1.0.0`"},
                    ],
                },
            ],
        }

    def build_demand_surge_block(
        self,
        dealer_id: str,
        forecasted_volume: float,
        baseline_capacity: float,
        surge_pct: float,
        threshold_pct: float,
        action_id: str,
    ) -> Dict[str, Any]:
        """Build Slack Block Kit payload for Rule 3: Service Demand Surge."""
        return {
            "channel": SLACK_CHANNEL,
            "text": f"📈 Service Demand Surge Warning: Dealer {dealer_id} (+{surge_pct * 100:.1f}%)",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📈 Dealer Service Demand Surge Warning: {dealer_id}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Dealer ID:*\n`{dealer_id}`"},
                        {"type": "mrkdwn", "text": f"*Demand Surge:*\n`+{surge_pct * 100:.1f}%` (Trigger > {threshold_pct * 100:.0f}%)"},
                        {"type": "mrkdwn", "text": f"*Forecast (14-day):*\n`{forecasted_volume:.1f}` visits"},
                        {"type": "mrkdwn", "text": f"*Baseline Capacity:*\n`{baseline_capacity:.1f}` visits"},
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Action ID: `{action_id}` | Recommendation: Stage replacement components & schedule technician overtime"},
                    ],
                },
            ],
        }

    def dispatch(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        """Dispatch JSON payload to Slack webhook.
        
        Returns:
            Tuple[delivery_status, status_detail]:
                - ('DELIVERED', response_info) if webhook returned 200
                - ('MOCK_LOGGED', detail) if no webhook URL is configured
                - ('FAILED', error_detail) if HTTP or network error occurred
        """
        if not self.webhook_url or not self.webhook_url.startswith("http"):
            summary = payload.get("text", "Slack Notification")
            logger.info(f"[MOCK_SLACK_DISPATCH] Channel: {payload.get('channel')} | Summary: {summary}")
            return "MOCK_LOGGED", "Mock Slack notification logged (SLACK_WEBHOOK_URL unset)"

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=req_data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=DISPATCH_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    return "DELIVERED", "HTTP 200 OK from Slack Webhook"
                return "FAILED", f"Unexpected HTTP status from Slack: {resp.status}"
        except urllib.error.HTTPError as e:
            err_msg = f"Slack HTTPError {e.code}: {e.reason}"
            logger.warning(err_msg)
            return "FAILED", err_msg
        except urllib.error.URLError as e:
            err_msg = f"Slack URLError: {e.reason}"
            logger.warning(err_msg)
            return "FAILED", err_msg
        except Exception as e:
            err_msg = f"Slack dispatch exception: {str(e)}"
            logger.error(err_msg)
            return "FAILED", err_msg
