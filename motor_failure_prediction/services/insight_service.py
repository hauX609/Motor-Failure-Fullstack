"""
Insights and analytics service for Motor Monitoring System.
Provides data for visualizations and dashboards.
"""

import logging
import numpy as np
import sqlite3
from typing import Dict, List

from config import now_iso
from models.database import db_manager
from utils.validators import Validator
from utils.errors import ValidationError, DatabaseError, NotFoundError


logger = logging.getLogger(__name__)


class InsightService:
    """Generates analytics and insights for dashboards."""
    
    @staticmethod
    def get_status_distribution() -> Dict[str, int]:
        """Get distribution of motor statuses."""
        try:
            query = """
                SELECT latest_status AS status, COUNT(*) AS count
                FROM motors
                WHERE active = 1
                GROUP BY latest_status
            """
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                rows = [dict(r) for r in cursor.fetchall()]
            
            # Ensure all categories present and normalize status labels from
            # multiple producers (e.g. HEALTHY/DEGRADING/CRITICAL).
            counts = {'Optimal': 0, 'Degrading': 0, 'Critical': 0}
            for row in rows:
                raw = str(row.get('status') or '').strip().lower()
                amount = int(row.get('count', 0))
                if raw in {'optimal', 'healthy'}:
                    counts['Optimal'] += amount
                elif raw in {'degrading', 'warning'}:
                    counts['Degrading'] += amount
                elif raw == 'critical':
                    counts['Critical'] += amount
            
            return counts
        
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting status distribution: {e}")
            raise DatabaseError(f"Failed to get status distribution: {str(e)}")
    
    @staticmethod
    def get_alerts_trend(days: int = 7) -> List[Dict]:
        """Get daily alerts trend by severity."""
        try:
            if not Validator.validate_days(days):
                raise ValidationError("days must be between 1 and 365")
            
            query = """
                SELECT substr(timestamp, 1, 10) AS day,
                       severity,
                       COUNT(*) AS count
                FROM alerts
                WHERE timestamp >= datetime('now', ?)
                GROUP BY day, severity
                ORDER BY day ASC
            """
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (f'-{days} days',))
                rows = [dict(r) for r in cursor.fetchall()]
            
            return rows
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting alerts trend: {e}")
            raise DatabaseError(f"Failed to get alerts trend: {str(e)}")
    
    @staticmethod
    def get_sensor_trend(motor_id: str, sensor: str = 's11', limit: int = 200) -> Dict:
        """Get time series data for a specific sensor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            # Validate sensor
            allowed_sensors = {f's{i}' for i in range(1, 22)} | {'setting1', 'setting2', 'setting3'}
            if sensor not in allowed_sensors:
                raise ValidationError("Invalid sensor field")
            
            if not Validator.validate_limit(limit, max_limit=2000, min_limit=1):
                raise ValidationError("limit must be between 1 and 2000")
            
            query = f"""
                SELECT timestamp, {sensor} AS value 
                FROM sensor_readings 
                WHERE motor_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (motor_id, limit))
                rows = [dict(r) for r in cursor.fetchall()]
            
            # Reverse for chronological order
            rows.reverse()
            
            values = [float(r['value']) for r in rows if r['value'] is not None]
            if not values:
                raise NotFoundError("No sensor data found")
            
            return {
                'motor_id': motor_id,
                'sensor': sensor,
                'points': rows,
                'summary': {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'avg': float(np.mean(values)),
                    'count': len(values)
                }
            }
        
        except (ValidationError, NotFoundError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting sensor trend: {e}")
            raise DatabaseError(f"Failed to get sensor trend: {str(e)}")
    
    @staticmethod
    def get_fleet_overview() -> Dict:
        """Get KPI counters for fleet dashboard."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM motors WHERE active = 1")
                active_motors = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
                open_alerts = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sensor_readings")
                readings_total = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cursor.fetchone()[0]
            
            return {
                'active_motors': active_motors,
                'open_alerts': open_alerts,
                'total_sensor_readings': readings_total,
                'active_users': active_users
            }
        
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting fleet overview: {e}")
            raise DatabaseError(f"Failed to get fleet overview: {str(e)}")
    
    @staticmethod
    def get_latest_readings() -> List[Dict]:
        """Get latest sensor readings for all motors."""
        try:
            query = """
            SELECT r.* FROM sensor_readings r
            INNER JOIN (
                SELECT motor_id, MAX(timestamp) as max_ts
                FROM sensor_readings
                GROUP BY motor_id
            ) latest ON r.motor_id = latest.motor_id AND r.timestamp = latest.max_ts
            """
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                readings = [dict(row) for row in cursor.fetchall()]
            
            return readings
        
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting latest readings: {e}")
            raise DatabaseError(f"Failed to get latest readings: {str(e)}")
    
    @staticmethod
    def get_motor_readings_history(motor_id: str, limit: int = 200) -> List[Dict]:
        """Get historical readings for a specific motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            if not Validator.validate_limit(limit, max_limit=1000):
                raise ValidationError("Limit too high. Maximum: 1000")
            
            query = """
                SELECT * FROM sensor_readings 
                WHERE motor_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (motor_id, limit))
                readings = [dict(row) for row in cursor.fetchall()]
            
            # Return in chronological order
            return list(reversed(readings))
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting motor readings: {e}")
            raise DatabaseError(f"Failed to get motor readings: {str(e)}")


# Global insight service instance
insight_service = InsightService()
