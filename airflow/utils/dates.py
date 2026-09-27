"""Airflow date and time utilities."""

from datetime import datetime, timedelta, timezone


def days_ago(n: int, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> datetime:
    """Return a datetime n days ago."""
    today = datetime.now(timezone.utc).replace(
        hour=hour, minute=minute, second=second, microsecond=microsecond
    )
    return today - timedelta(days=n)
