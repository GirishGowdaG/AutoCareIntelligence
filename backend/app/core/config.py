"""Configuration and Secret Governance for AutoCare Intelligence FastAPI Backend.

Enforces zero hard-coded fallback secrets. All credentials must be loaded
from explicitly defined environment variables.
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ml.config import PG_CONFIG


class APIAuthConfig(BaseModel):
    """API Authentication Credentials loaded from environment."""
    admin_key: str = Field(..., description="Secret key for Admin role")
    dealer_key: str = Field(..., description="Secret key for DealerServiceManager role")
    analyst_key: str = Field(..., description="Secret key for FleetAnalyst role")

    @classmethod
    def load_from_env(cls) -> "APIAuthConfig":
        """Load API keys strictly from environment.
        
        Raises RuntimeError if any required credential is missing.
        """
        admin_key = os.getenv("AUTOCARE_ADMIN_KEY")
        dealer_key = os.getenv("AUTOCARE_DEALER_KEY")
        analyst_key = os.getenv("AUTOCARE_ANALYST_KEY")

        missing = []
        if not admin_key:
            missing.append("AUTOCARE_ADMIN_KEY")
        if not dealer_key:
            missing.append("AUTOCARE_DEALER_KEY")
        if not analyst_key:
            missing.append("AUTOCARE_ANALYST_KEY")

        if missing:
            raise RuntimeError(
                f"API Authentication Configuration Failure: Missing required environment variables: {', '.join(missing)}. "
                "Application startup halted. Do not use hardcoded secret fallbacks."
            )

        return cls(admin_key=admin_key, dealer_key=dealer_key, analyst_key=analyst_key)


class AppSettings(BaseModel):
    """Application-level runtime settings."""
    app_name: str = "AutoCare Intelligence REST API"
    app_version: str = "1.0.0"
    pg_config: Dict[str, Any] = PG_CONFIG
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_telemetry: str = "vehicle-telemetry"
    kafka_consumer_group_sse: str = "autocare-sse-bridge"


def get_auth_config() -> APIAuthConfig:
    """Retrieve verified authentication configuration."""
    return APIAuthConfig.load_from_env()


def get_app_settings() -> AppSettings:
    """Retrieve application settings."""
    return AppSettings()
