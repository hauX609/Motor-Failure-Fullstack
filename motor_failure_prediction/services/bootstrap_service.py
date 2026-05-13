"""
Baseline data bootstrap service.
Ensures dashboards/alerts are not empty in production-like demo environments.
"""

import sqlite3
import logging
import math
from datetime import datetime, timedelta
from typing import Dict

from config import (
    now_iso,
    BASELINE_DATA_ENABLED,
    BASELINE_MIN_MOTORS,
    BASELINE_CRITICAL_TARGET,
    BASELINE_DEGRADING_TARGET,
    BASELINE_INFO_ALERTS_TARGET,
    REQUIRED_SEQUENCE_LENGTH,
)
from models.database import db_manager
from services.auth_service import auth_service


logger = logging.getLogger(__name__)


SENSOR_COLUMNS = [
    'setting1', 'setting2', 'setting3',
    's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
    's10', 's11', 's12', 's13', 's14', 's15', 's16', 's17',
    's18', 's19', 's20', 's21'
]

BASE_SENSOR_PROFILE = {
    'setting1': 0.45,
    'setting2': 0.60,
    'setting3': 0.50,
    's1': 0.20,
    's2': 0.30,
    's3': 0.40,
    's4': 0.25,
    's5': 0.10,
    's6': 0.15,
    's7': 0.35,
    's8': 0.50,
    's9': 0.60,
    's10': 0.10,
    's11': 0.20,
    's12': 0.40,
    's13': 0.55,
    's14': 0.70,
    's15': 0.30,
    's16': 0.10,
    's17': 0.40,
    's18': 0.10,
    's19': 0.10,
    's20': 0.30,
    's21': 0.30,
}

KEY_SENSOR_WEIGHTS = {
    's4': 0.9,
    's7': 0.7,
    's11': 1.0,
    's13': 0.6,
    's14': 0.8,
}


def _build_demo_sensor_snapshot(status: str, step: int, total_steps: int) -> Dict[str, float]:
    """Build a deterministic sensor snapshot for showcase data."""
    progress = 0.0 if total_steps <= 1 else step / float(total_steps - 1)
    status_scale = {
        'Optimal': 0.0,
        'Degrading': 0.22,
        'Critical': 0.45,
    }.get(status, 0.0)

    snapshot: Dict[str, float] = {}
    for idx, column in enumerate(SENSOR_COLUMNS):
        base = BASE_SENSOR_PROFILE[column]
        wave = math.sin((step + idx) * 0.32) * 0.01
        drift_scale = KEY_SENSOR_WEIGHTS.get(column, 0.15)

        if column.startswith('s'):
            drift = progress * status_scale * drift_scale
        else:
            drift = progress * status_scale * 0.04

        value = max(0.0, min(1.0, base + drift + wave))
        snapshot[column] = round(value, 6)

    return snapshot


def _ensure_demo_users(cursor) -> int:
    """Create a small set of demo users if the database is empty."""
    cursor.execute("SELECT COUNT(*) FROM users")
    existing_users = int(cursor.fetchone()[0])
    if existing_users > 0:
        return 0

    created_at = now_iso()
    demo_users = [
        ('demo_admin', 'demo.admin@motorpredict.io', 'DemoAdmin123!', 'admin'),
        ('demo_operator', 'demo.operator@motorpredict.io', 'DemoOperator123!', 'operator'),
    ]

    inserted = 0
    for username, email, password, role in demo_users:
        cursor.execute(
            """
            INSERT INTO users (
                username, email, password_hash, role,
                email_notifications, is_active, failed_otp_attempts,
                otp_locked_until, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, 1, 0, NULL, ?, ?)
            """,
            (username, email, auth_service.hash_password(password), role, created_at, created_at),
        )
        inserted += 1

    return inserted


def seed_demo_showcase_data() -> Dict[str, int]:
    """Seed a full demo dataset for dashboards, alerts, auth, and predictions."""
    summary = {
        'users_inserted': 0,
        'motors_updated': 0,
        'sensor_readings_inserted': 0,
        'alerts_inserted': 0,
    }

    min_motors = _safe_int(BASELINE_MIN_MOTORS, 1)
    critical_target = _safe_int(BASELINE_CRITICAL_TARGET, 0)
    degrading_target = _safe_int(BASELINE_DEGRADING_TARGET, 0)
    info_target = _safe_int(BASELINE_INFO_ALERTS_TARGET, 0)
    target_sequence_length = max(REQUIRED_SEQUENCE_LENGTH, 50)

    if critical_target + degrading_target > min_motors:
        degrading_target = max(0, min_motors - critical_target)

    with db_manager.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT motor_id, latest_status FROM motors WHERE active = 1 ORDER BY motor_id"
        )
        active_motors = [dict(row) for row in cursor.fetchall()]

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
        motor_ids = [row[0] for row in cursor.fetchall()]

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

        summary['users_inserted'] = _ensure_demo_users(cursor)

        # Ensure each showcase motor has enough history for charts and predictions.
        for motor_id in motor_ids:
            cursor.execute(
                "SELECT COUNT(*) FROM sensor_readings WHERE motor_id = ?",
                (motor_id,),
            )
            current_count = int(cursor.fetchone()[0])
            if current_count >= target_sequence_length:
                continue

            cursor.execute(
                "SELECT latest_status FROM motors WHERE motor_id = ?",
                (motor_id,),
            )
            status = str(cursor.fetchone()[0] or 'Optimal')
            missing_rows = target_sequence_length - current_count
            start_time = datetime.utcnow() - timedelta(minutes=5 * (missing_rows - 1))

            for idx in range(missing_rows):
                step = current_count + idx
                ts = (start_time + timedelta(minutes=idx * 5)).isoformat()
                snapshot = _build_demo_sensor_snapshot(status, step, target_sequence_length)
                cursor.execute(
                    """
                    INSERT INTO sensor_readings (
                        motor_id, timestamp, setting1, setting2, setting3,
                        s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11,
                        s12, s13, s14, s15, s16, s17, s18, s19, s20, s21
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        motor_id,
                        ts,
                        snapshot['setting1'], snapshot['setting2'], snapshot['setting3'],
                        snapshot['s1'], snapshot['s2'], snapshot['s3'], snapshot['s4'], snapshot['s5'],
                        snapshot['s6'], snapshot['s7'], snapshot['s8'], snapshot['s9'], snapshot['s10'],
                        snapshot['s11'], snapshot['s12'], snapshot['s13'], snapshot['s14'], snapshot['s15'],
                        snapshot['s16'], snapshot['s17'], snapshot['s18'], snapshot['s19'], snapshot['s20'],
                        snapshot['s21'],
                    ),
                )
                summary['sensor_readings_inserted'] += 1

        # Ensure one alert of each severity exists in the current demo set.
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

        alert_templates = [
            (critical_ids[:1], 'Critical', 'Critical baseline alert: immediate inspection required.'),
            (degrading_ids[:1], 'Degrading', 'Degrading baseline alert: monitor and schedule maintenance.'),
            ((optimal_ids or motor_ids)[:max(1, info_target)], 'Warning', 'Baseline warning: motor operating within expected range.'),
        ]

        for ids, severity, message in alert_templates:
            for motor_id in ids:
                if recent_exists(motor_id, severity, message):
                    continue
                cursor.execute(
                    """
                    INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (motor_id, now_iso(), severity, message, 1 if severity == 'Warning' else 0),
                )
                summary['alerts_inserted'] += 1

        conn.commit()

    summary['motors_updated'] = len(motor_ids)
    return summary


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

    try:
        summary = seed_demo_showcase_data()
        logger.info(
            "Baseline data ensured: motors=%s users=%s readings=%s alerts=%s",
            summary['motors_updated'],
            summary['users_inserted'],
            summary['sensor_readings_inserted'],
            summary['alerts_inserted'],
        )
    except Exception as exc:
        logger.warning("Baseline data bootstrap skipped due to error: %s", exc)
