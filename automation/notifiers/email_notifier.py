"""SMTP / MIME Email Dispatcher with HTML Work-Order Formatting.

Generates structured multipart MIME messages (text/plain and text/html)
for vehicle inspection work-orders and dealer capacity warnings.
Dispatches via smtplib with TLS, falling back to mock logging if unconfigured.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Dict, Any, Tuple, Optional

from automation.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    SMTP_TO_SERVICE_MANAGER,
    SMTP_USE_TLS,
    DISPATCH_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Formats and dispatches MIME/HTML email notifications for automated maintenance actions."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_email: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or SMTP_HOST
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user or SMTP_USER
        self.smtp_password = smtp_password or SMTP_PASSWORD
        self.sender_email = sender_email or SMTP_FROM

    def build_failure_risk_email(
        self,
        vehicle_id: str,
        risk_score: float,
        threshold: float,
        top_features: Dict[str, float],
        action_id: str,
        to_email: Optional[str] = None,
    ) -> MIMEMultipart:
        """Construct multipart MIME email for Rule 1: High Vehicle Failure Risk."""
        recipient = to_email or SMTP_TO_SERVICE_MANAGER
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[AutoCare Alert] High Vehicle Failure Risk - {vehicle_id} ({risk_score*100:.1f}%)"
        msg["From"] = self.sender_email
        msg["To"] = recipient

        features_rows = "".join([
            f"<tr><td style='padding:6px; border:1px solid #ddd;'><b>{k}</b></td>"
            f"<td style='padding:6px; border:1px solid #ddd;'>{v:.2f}</td></tr>"
            for k, v in top_features.items()
        ])

        text_content = (
            f"AUTOCARE INTELLIGENCE - HIGH FAILURE RISK NOTIFICATION\n"
            f"=======================================================\n"
            f"Vehicle ID: {vehicle_id}\n"
            f"Failure Probability: {risk_score*100:.1f}% (Threshold: {threshold*100:.0f}%)\n"
            f"Action Taken: Pre-emptive inspection scheduled. Work-order drafted.\n"
            f"Action ID: {action_id}\n"
            f"Top Features:\n"
            + "\n".join([f"  - {k}: {v:.2f}" for k, v in top_features.items()])
        )

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #d32f2f; color: white; padding: 16px 20px;">
                    <h2 style="margin: 0; font-size: 20px;">🚨 High Vehicle Failure Risk Alert</h2>
                </div>
                <div style="padding: 20px;">
                    <p>An automated maintenance rule has flagged vehicle <b>{vehicle_id}</b> for pre-emptive service.</p>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr><td style="padding: 8px; background: #f9f9f9; width: 40%;"><b>Vehicle ID</b></td><td style="padding: 8px;"><code>{vehicle_id}</code></td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Failure Risk Score</b></td><td style="padding: 8px;"><b style="color: #d32f2f;">{risk_score*100:.1f}%</b> (Threshold: {threshold*100:.0f}%)</td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Recommended Action</b></td><td style="padding: 8px;">Multi-point mechanical inspection & sensor check</td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Action Audit ID</b></td><td style="padding: 8px;"><code>{action_id}</code></td></tr>
                    </table>
                    <h4 style="margin-bottom: 8px;">Key Risk Telemetry & Service Drivers:</h4>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #f0f0f0;">
                                <th style="padding: 6px; border: 1px solid #ddd; text-align: left;">Feature Metric</th>
                                <th style="padding: 6px; border: 1px solid #ddd; text-align: left;">Observed Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {features_rows}
                        </tbody>
                    </table>
                </div>
                <div style="background-color: #f5f5f5; padding: 12px 20px; font-size: 12px; color: #777;">
                    AutoCare Intelligence Platform — Decision Automation Engine v1.0.0
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        return msg

    def build_demand_surge_email(
        self,
        dealer_id: str,
        forecasted_volume: float,
        baseline_capacity: float,
        surge_pct: float,
        threshold_pct: float,
        action_id: str,
        to_email: Optional[str] = None,
    ) -> MIMEMultipart:
        """Construct multipart MIME email for Rule 3: Service Demand Surge."""
        recipient = to_email or SMTP_TO_SERVICE_MANAGER
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[AutoCare Ops] Service Demand Surge Warning - Dealer {dealer_id} (+{surge_pct*100:.1f}%)"
        msg["From"] = self.sender_email
        msg["To"] = recipient

        text_content = (
            f"AUTOCARE INTELLIGENCE - DEALER SERVICE CAPACITY WARNING\n"
            f"=======================================================\n"
            f"Dealer ID: {dealer_id}\n"
            f"Forecasted Volume (14-Day): {forecasted_volume:.1f} visits\n"
            f"Baseline Capacity: {baseline_capacity:.1f} visits\n"
            f"Demand Surge: +{surge_pct*100:.1f}% (Threshold: >{threshold_pct*100:.0f}%)\n"
            f"Action Taken: Capacity warning logged. Recommended parts replenishment.\n"
            f"Action ID: {action_id}\n"
        )

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #f57c00; color: white; padding: 16px 20px;">
                    <h2 style="margin: 0; font-size: 20px;">📈 Service Demand Surge Warning</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Forecasted 14-day service demand for dealership <b>{dealer_id}</b> exceeds operational capacity limits.</p>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr><td style="padding: 8px; background: #f9f9f9; width: 40%;"><b>Dealer ID</b></td><td style="padding: 8px;"><code>{dealer_id}</code></td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Surge Percentage</b></td><td style="padding: 8px;"><b style="color: #f57c00;">+{surge_pct*100:.1f}%</b> (Trigger: >{threshold_pct*100:.0f}%)</td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>14-Day Forecast</b></td><td style="padding: 8px;"><b>{forecasted_volume:.1f}</b> visits</td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Baseline Capacity</b></td><td style="padding: 8px;">{baseline_capacity:.1f} visits</td></tr>
                        <tr><td style="padding: 8px; background: #f9f9f9;"><b>Action Audit ID</b></td><td style="padding: 8px;"><code>{action_id}</code></td></tr>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        return msg

    def dispatch(self, msg: MIMEMultipart, to_email: Optional[str] = None) -> Tuple[str, str]:
        """Dispatch MIME message via SMTP with mock fallback on connection failure.
        
        Returns:
            Tuple[delivery_status, status_detail]:
                - ('DELIVERED', detail) if SMTP transmission succeeded
                - ('MOCK_LOGGED', detail) if SMTP server is unavailable or unconfigured
                - ('FAILED', detail) if fatal authentication/protocol error occurred
        """
        recipient = to_email or msg["To"]
        subject = msg["Subject"]

        # If no user or host is configured for live SMTP, use mock fallback
        if not self.smtp_user and (self.smtp_host in ("localhost", "127.0.0.1")):
            logger.info(f"[MOCK_EMAIL_DISPATCH] To: {recipient} | Subject: {subject}")
            return "MOCK_LOGGED", f"Mock email logged (SMTP credentials not configured for {recipient})"

        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=DISPATCH_TIMEOUT_SECONDS)
            if SMTP_USE_TLS:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.sender_email, [recipient], msg.as_string())
            server.quit()
            logger.info(f"Email dispatched successfully to {recipient}")
            return "DELIVERED", f"SMTP delivery succeeded to {recipient}"
        except (smtplib.SMTPConnectError, ConnectionRefusedError, TimeoutError, OSError) as e:
            logger.info(f"[MOCK_EMAIL_DISPATCH] (SMTP connection unavailable: {str(e)}) To: {recipient} | Subject: {subject}")
            return "MOCK_LOGGED", f"Mock email logged (SMTP server unavailable: {str(e)})"
        except smtplib.SMTPAuthenticationError as e:
            err_msg = f"SMTP Authentication failed: {str(e)}"
            logger.warning(err_msg)
            return "FAILED", err_msg
        except Exception as e:
            err_msg = f"SMTP transmission error: {str(e)}"
            logger.error(err_msg)
            return "FAILED", err_msg
