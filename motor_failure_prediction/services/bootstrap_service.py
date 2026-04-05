"""
Baseline data bootstrap service.
Ensures dashboards/alerts are not empty in production-like demo environments.
"""

import sqlite3
import logging
from datetime import datetime, timedelta

from config import (
    now_iso,
    BASELINE_DATA_ENABLED,
    BASELINE_MIN_MOTORS,
    BASELINE_CRITICAL_TARGET,
    BASELINE_DEGRADING_TARGET,
    BASELINE_INFO_ALERTS_TARGET,
)
from models.database import db_manager


logger = logging.getLogger(__name__)


def _safe_int(value: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(value))
    except Exception:
        return minimum


def ensure_baseline_operational_data() -> None:
    """Seed/shape baseline status + alert mix so UI is meaningfully populated."""
    if not BASELINE_DATA_ENABLED:
        logger.info("Baseline data bootstrap disabled")
        return

    min_motors = _safe_int(BASELINE_MIN_MOTORS, 1)
    critical_target = _safe_int(BASELINE_CRITICAL_TARGET, 0)
    degrading_target = _safe_int(BASELINE_DEGRADING_TARGET, 0)
    info_target = _safe_int(BASELINE_INFO_ALERTS_TARGET, 0)

    # Keep targets within motor count.
    if critical_target + degrading_target > min_motors:
        degrading_target = max(0, min_motors - critical_target)

    try:
        with db_manager.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT motor_id, latest_status FROM motors WHERE active = 1 ORDER BY motor_id"
            )
            rows = cursor.fetchall()
            active_motors = [dict(r) for r in rows]

            missing = max(0, min_motors - len(active_motors))
            for idx in range(missing):
                motor_id = f"Motor-AUTO-{idx + 1:02d}"
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO motors (motor_id, motor_type, installation_date, latest_status, active)
                    VALUES (?, ?, ?, 'Optimal', 1)
                    """,
                    (motor_id, 'Auto Baseline', now_iso()),
                )

            cursor.execute(
                "SELECT motor_id FROM motors WHERE active = 1 ORDER BY motor_id LIMIT ?",
                (min_motors,),
            )
            motor_ids = [r[0] for r in cursor.fetchall()]

            critical_ids = motor_ids[:critical_target]
            degrading_ids = motor_ids[critical_target:critical_target + degrading_target]
            optimal_ids = motor_ids[critical_target + degrading_target:]

            if critical_ids:
                placeholders = ",".join(["?"] * len(critical_ids))
                cursor.execute(
                    f"UPDATE motors SET latest_status = 'Critical' WHERE motor_id IN ({placeholders})",
                    critical_ids,
                )

            if degrading_ids:
                placeholders = ",".join(["?"] * len(degrading_ids))
                cursor.execute(
                    f"UPDATE motors SET latest_status = 'Degrading' WHERE motor_id IN ({placeholders})",
                    degrading_ids,
                )

            if optimal_ids:
                placeholders = ",".join(["?"] * len(optimal_ids))
                cursor.execute(
                    f"UPDATE motors SET latest_status = 'Optimal' WHERE motor_id IN ({placeholders})",
                    optimal_ids,
                )

            # Insert minimal sensor snapshots for each selected motor if readings are absent.
            for motor_id in motor_ids:
                cursor.execute(
                    "SELECT COUNT(*) FROM sensor_readings WHERE motor_id = ?",
                    (motor_id,),
                )
                count = int(cursor.fetchone()[0])
                if count > 0:
                    continue

                cursor.execute(
                    "SELECT latest_status FROM motors WHERE motor_id = ?",
                    (motor_id,),
                )
                status = str(cursor.fetchone()[0])
                base = 1.0 if status == 'Optimal' else (1.6 if status == 'Degrading' else 2.2)

                for k in range(8):
                    ts = (datetime.utcnow() - timedelta(minutes=(8 - k) * 5)).isoformat()
                    cursor.execute(
                        """
                        INSERT INTO sensor_readings (motor_id, timestamp, setting1, setting2, setting3, s11)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (motor_id, ts, 0.0, 0.0, 100.0, base + ((k % 5) * 0.02)),
                    )

            # Add alerts if recent ones are missing, ensuring critical/degrading/info-like coverage.
            def recent_exists(mid: str, severity: str, msg: str) -> bool:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM alerts
                    WHERE motor_id = ? AND severity = ? AND message = ?
                      AND timestamp >= datetime('now', '-6 hours')
                    """,
                    (mid, severity, msg),
                )
                return int(cursor.fetchone()[0]) > 0

            for mid in critical_ids:
                msg = "Critical baseline alert: immediate inspection required."
                if not recent_exists(mid, 'Critical', msg):
                    cursor.execute(
                        """
                        INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                        VALUES (?, ?, 'Critical', ?, 0)
                        """,
                        (mid, now_iso(), msg),
                    )

            for mid in degrading_ids:
                msg = "Degrading baseline alert: monitor and schedule maintenance."
                if not recent_exists(mid, 'Degrading', msg):
                    cursor.execute(
                        """
                        INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                        VALUES (?, ?, 'Degrading', ?, 0)
                        """,
                        (mid, now_iso(), msg),
                    )

            info_ids = (optimal_ids or motor_ids)[:max(1, info_target)]
            for mid in info_ids:
                msg = "Baseline info: motor operating within expected range."
                if not recent_exists(mid, 'Optimal', msg):
                    cursor.execute(
                        """
                        INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                        VALUES (?, ?, 'Optimal', ?, 1)
                        """,
                        (mid, now_iso(), msg),
                    )

            conn.commit()

            logger.info(
                "Baseline data ensured: motors=%s critical=%s degrading=%s info_alerts_target=%s",
                len(motor_ids),
                len(critical_ids),
                len(degrading_ids),
                info_target,
            )
    except Exception as exc:
        logger.warning("Baseline data bootstrap skipped due to error: %s", exc)
