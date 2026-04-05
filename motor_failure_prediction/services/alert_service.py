"""
Alert management service for Motor Monitoring System.
Handles alert creation, retrieval, and notification.
"""

import sqlite3
import logging
from typing import List, Dict
from datetime import datetime

from config import ALERT_EMAIL_ENABLED, now_iso
from models.database import db_manager
from services.email_service import email_service
from services.auth_service import auth_service
from utils.validators import Validator
from utils.errors import ValidationError, DatabaseError, NotFoundError


logger = logging.getLogger(__name__)


class AlertService:
    """Manages motor alerts."""
    
    @staticmethod
    def create_alert(motor_id: str, severity: str, message: str) -> bool:
        """Create a new alert."""
        try:
            # Validate inputs
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            db_severity = Validator.get_alert_severity_for_status(severity)
            if not Validator.validate_severity(db_severity):
                raise ValidationError(f"Invalid severity: {severity}")
            
            if not message or len(message.strip()) == 0:
                raise ValidationError("Alert message cannot be empty")
            
            # Create alert
            query = """
                INSERT INTO alerts (motor_id, timestamp, severity, message)
                VALUES (?, ?, ?, ?)
            """
            db_manager.execute_update(
                query,
                (motor_id, now_iso(), db_severity, message.strip())
            )
            
            logger.info(f"🚨 Alert created for {motor_id}: {message}")
            
            # Send email if enabled
            if ALERT_EMAIL_ENABLED:
                recipients = auth_service.get_alert_email_recipients()
                if recipients:
                    sent, reason = email_service.send_alert_email(
                        motor_id, db_severity, message.strip(), recipients
                    )
                    if sent:
                        logger.info(f"📧 Alert email sent for {motor_id}")
                    else:
                        logger.warning(f"Alert email not sent: {reason}")
            
            return True
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise DatabaseError(f"Failed to create alert: {str(e)}")
    
    @staticmethod
    def batch_create_alerts(alerts_data: List[Dict]) -> int:
        """Batch create alerts."""
        if not alerts_data:
            return 0
        
        try:
            # Validate and convert all alerts
            processed_alerts = []
            for alert in alerts_data:
                if not all(key in alert for key in ['motor_id', 'severity', 'message']):
                    raise ValidationError("Invalid alert data structure")
                
                if not Validator.validate_motor_id(alert['motor_id']):
                    raise ValidationError(f"Invalid motor ID: {alert['motor_id']}")
                
                db_severity = Validator.get_alert_severity_for_status(alert['severity'])
                if not Validator.validate_severity(db_severity):
                    raise ValidationError(f"Invalid alert severity: {alert['severity']}")
                
                processed_alerts.append({
                    'motor_id': alert['motor_id'],
                    'severity': db_severity,
                    'message': alert['message'].strip()
                })
            
            # Batch insert
            query = """
                INSERT INTO alerts (motor_id, timestamp, severity, message)
                VALUES (?, ?, ?, ?)
            """
            params = [
                (a['motor_id'], now_iso(), a['severity'], a['message'])
                for a in processed_alerts
            ]
            
            db_manager.execute_many(query, params)
            
            # Log alerts
            for alert in processed_alerts:
                logger.info(f"🚨 Alert created for {alert['motor_id']}: {alert['message']}")
            
            # Send batch email if enabled
            if ALERT_EMAIL_ENABLED and processed_alerts:
                recipients = auth_service.get_alert_email_recipients()
                if recipients:
                    sent, reason = email_service.send_batch_alert_email(
                        processed_alerts, recipients
                    )
                    if sent:
                        logger.info("📧 Batch alert email sent")
                    else:
                        logger.warning(f"Batch alert email not sent: {reason}")
            
            return len(processed_alerts)
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error batch creating alerts: {e}")
            raise DatabaseError(f"Failed to batch create alerts: {str(e)}")
    
    @staticmethod
    def get_alerts(motor_id: str = None, severity: str = None,
                  acknowledged: bool = None, limit: int = 100) -> List[Dict]:
        """Get alerts with optional filtering."""
        try:
            # Validate parameters
            if motor_id and not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            if severity and not Validator.validate_severity(severity):
                raise ValidationError("Invalid severity")
            
            if not Validator.validate_limit(limit, max_limit=1000):
                raise ValidationError("Limit too high. Maximum: 1000")
            
            # Build query
            query = "SELECT * FROM alerts WHERE 1=1"
            params = []
            
            if motor_id:
                query += " AND motor_id = ?"
                params.append(motor_id)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if acknowledged is not None:
                query += f" AND acknowledged = {1 if acknowledged else 0}"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                alerts = [dict(row) for row in cursor.fetchall()]
            
            return alerts
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            raise DatabaseError(f"Failed to fetch alerts: {str(e)}")
    
    @staticmethod
    def acknowledge_alert(alert_id: int) -> bool:
        """Mark alert as acknowledged."""
        try:
            if alert_id <= 0:
                raise ValidationError("Invalid alert ID")
            
            query = "UPDATE alerts SET acknowledged = 1 WHERE alert_id = ?"
            rowcount = db_manager.execute_update(query, (alert_id,))
            
            if rowcount == 0:
                raise NotFoundError("Alert not found")
            
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            raise DatabaseError(f"Failed to acknowledge alert: {str(e)}")
    
    @staticmethod
    def batch_acknowledge_alerts(alert_ids: List[int]) -> int:
        """Batch acknowledge alerts."""
        if not alert_ids:
            return 0
        
        try:
            # Validate alert IDs
            if not all(isinstance(aid, int) and aid > 0 for aid in alert_ids):
                raise ValidationError("All alert IDs must be positive integers")
            
            if len(alert_ids) > 100:
                raise ValidationError("Too many alert IDs. Maximum: 100")
            
            placeholders = ','.join(['?' for _ in alert_ids])
            query = f"UPDATE alerts SET acknowledged = 1 WHERE alert_id IN ({placeholders})"
            
            rowcount = 0
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, alert_ids)
                rowcount = cursor.rowcount
                conn.commit()
            
            logger.info(f"Batch acknowledged {rowcount} alerts")
            return rowcount
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error batch acknowledging alerts: {e}")
            raise DatabaseError(f"Failed to batch acknowledge alerts: {str(e)}")


# Global alert service instance
alert_service = AlertService()
