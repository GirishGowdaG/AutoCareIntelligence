"""Action Audit Logger with Idempotency Protection for AutoCare Intelligence.

Guarantees exactly-once action creation and notification dispatching
across at-least-once distributed Kafka delivery streams.
Persists immutable records to `ml_inference.action_logs`.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from ml.config import PG_CONFIG

logger = logging.getLogger(__name__)


def generate_idempotency_key(
    rule_id: str,
    entity_id: str,
    event_timestamp: str,
    trigger_value: float,
) -> str:
    """Generate deterministic SHA-256 idempotency key from source event attributes."""
    raw = f"{rule_id.strip()}:{entity_id.strip()}:{str(event_timestamp).strip()}:{trigger_value:.4f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


class ActionLogger:
    """Manages transactional persistence of automated actions to PostgreSQL with duplicate detection."""

    def __init__(self, pg_config: Optional[Dict[str, Any]] = None):
        self.pg_config = pg_config or PG_CONFIG

    def check_is_duplicate(self, idempotency_key: str) -> Tuple[bool, Optional[str]]:
        """Check if an action with this idempotency key has already been recorded.
        
        Returns:
            Tuple[is_duplicate, existing_action_id]
        """
        sql = "SELECT action_id FROM ml_inference.action_logs WHERE idempotency_key = %s LIMIT 1;"
        try:
            with psycopg2.connect(**self.pg_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (idempotency_key,))
                    row = cur.fetchone()
                    if row:
                        return True, str(row[0])
            return False, None
        except Exception as e:
            logger.warning(f"Idempotency check query failed: {e}. Assuming not duplicate.")
            return False, None

    def log_action(
        self,
        rule_id: str,
        entity_type: str,
        entity_id: str,
        trigger_timestamp: datetime,
        trigger_value: float,
        threshold_applied: float,
        action_taken: str,
        channel_dispatched: str,
        delivery_status: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        action_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Record an automated action in ml_inference.action_logs with idempotency enforcement.
        
        Returns:
            Tuple[is_new_action, action_id]:
                - (True, action_id) if the action was newly recorded
                - (False, existing_action_id) if duplicate was suppressed
        """
        act_id = action_id or str(uuid.uuid4())
        ts_str = trigger_timestamp.isoformat() if isinstance(trigger_timestamp, datetime) else str(trigger_timestamp)
        key = idempotency_key or generate_idempotency_key(rule_id, entity_id, ts_str, trigger_value)

        # Idempotency guard: prevent duplicate action creation
        is_dup, existing_id = self.check_is_duplicate(key)
        if is_dup:
            logger.info(f"Duplicate action suppressed for key {key} (Existing action_id: {existing_id})")
            return False, existing_id

        sql = """
        INSERT INTO ml_inference.action_logs (
            action_id,
            rule_id,
            entity_type,
            entity_id,
            trigger_timestamp,
            trigger_value,
            threshold_applied,
            action_taken,
            channel_dispatched,
            delivery_status,
            idempotency_key,
            payload,
            created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING action_id;
        """
        try:
            with psycopg2.connect(**self.pg_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            act_id,
                            rule_id,
                            entity_type,
                            entity_id,
                            trigger_timestamp,
                            trigger_value,
                            threshold_applied,
                            action_taken,
                            channel_dispatched,
                            delivery_status,
                            key,
                            json.dumps(payload),
                            datetime.now(timezone.utc),
                        ),
                    )
                    res = cur.fetchone()
                    if res:
                        conn.commit()
                        logger.info(f"Action logged: {rule_id} on {entity_id} -> action_id: {act_id} ({delivery_status})")
                        return True, act_id
                    else:
                        # Race condition handled by ON CONFLICT
                        conn.rollback()
                        _, existing_id = self.check_is_duplicate(key)
                        return False, existing_id or act_id
        except Exception as e:
            logger.error(f"Failed to persist action log to database: {e}")
            raise

    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent action logs from ml_inference.action_logs."""
        sql = """
        SELECT action_id, rule_id, entity_type, entity_id, trigger_timestamp,
               trigger_value, threshold_applied, action_taken, channel_dispatched,
               delivery_status, idempotency_key, payload, created_at
        FROM ml_inference.action_logs
        ORDER BY trigger_timestamp DESC
        LIMIT %s;
        """
        try:
            with psycopg2.connect(**self.pg_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (limit,))
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching recent actions: {e}")
            return []
