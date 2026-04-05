"""
Motor management service for Motor Monitoring System.
Handles motor CRUD operations and status management.
"""

import sqlite3
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from config import now_iso
from models.database import db_manager
from utils.validators import Validator
from utils.errors import (
    ValidationError, NotFoundError, ConflictError,
    DatabaseError
)


logger = logging.getLogger(__name__)


class MotorService:
    """Manages motor operations."""
    
    @staticmethod
    def create_motor(motor_id: str, motor_type: str,
                    installation_date: Optional[str] = None,
                    location: Optional[str] = None) -> Dict:
        """Create a new motor."""
        try:
            # Validate inputs
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor_id format")
            if not motor_type:
                raise ValidationError("motor_type is required")
            
            if not installation_date:
                installation_date = datetime.now().strftime('%Y-%m-%d')
            
            # Create motor
            query = """
                INSERT INTO motors (motor_id, motor_type, installation_date, location, latest_status, active)
                VALUES (?, ?, ?, ?, 'Optimal', 1)
            """
            db_manager.execute_update(query, (motor_id, motor_type, installation_date, location))
            
            logger.info(f"Motor {motor_id} created successfully")
            
            return {
                'motor_id': motor_id,
                'motor_type': motor_type,
                'installation_date': installation_date,
                'location': location,
                'status': 'Optimal',
                'active': 1
            }
        
        except ValidationError:
            raise
        except sqlite3.IntegrityError:
            raise ConflictError("Motor already exists")
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error creating motor: {e}")
            raise DatabaseError(f"Failed to create motor: {str(e)}")
    
    @staticmethod
    def get_motor_status(motor_id: str) -> str:
        """Get current status of a motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            query = "SELECT latest_status FROM motors WHERE motor_id = ?"
            result = db_manager.execute_query(query, (motor_id,), fetch_one=True)
            
            return result[0] if result and result[0] else 'Optimal'
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get motor status: {str(e)}")
    
    @staticmethod
    def get_multiple_motor_statuses(motor_ids: List[str]) -> Dict[str, str]:
        """Get statuses for multiple motors."""
        if not motor_ids:
            return {}
        
        try:
            placeholders = ','.join(['?' for _ in motor_ids])
            query = f"SELECT motor_id, latest_status FROM motors WHERE motor_id IN ({placeholders})"
            
            results = db_manager.execute_query(query, tuple(motor_ids))
            
            # Return dictionary with default 'Optimal' for missing motors
            status_dict = {motor_id: 'Optimal' for motor_id in motor_ids}
            for motor_id, status in results:
                if status:
                    status_dict[motor_id] = status
            
            return status_dict
        
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get motor statuses: {str(e)}")
    
    @staticmethod
    def update_motor_status(motor_id: str, new_status: str) -> bool:
        """Update status of a motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            if not Validator.validate_motor_status(new_status):
                raise ValidationError(f"Invalid motor status: {new_status}")
            
            query = "UPDATE motors SET latest_status = ? WHERE motor_id = ?"
            rowcount = db_manager.execute_update(query, (new_status, motor_id))
            
            return rowcount > 0
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error updating motor status: {e}")
            raise DatabaseError(f"Failed to update motor status: {str(e)}")
    
    @staticmethod
    def batch_update_motor_statuses(motor_status_updates: List[Tuple[str, str]]) -> int:
        """Batch update motor statuses."""
        if not motor_status_updates:
            return 0
        
        try:
            # Validate all updates
            for motor_id, status in motor_status_updates:
                if not Validator.validate_motor_id(motor_id):
                    raise ValidationError(f"Invalid motor ID: {motor_id}")
                if not Validator.validate_motor_status(status):
                    raise ValidationError(f"Invalid status: {status}")
            
            query = "UPDATE motors SET latest_status = ? WHERE motor_id = ?"
            params = [(status, motor_id) for motor_id, status in motor_status_updates]
            
            db_manager.execute_many(query, params)
            
            logger.info(f"Batch updated {len(motor_status_updates)} motor statuses")
            return len(motor_status_updates)
        
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error batch updating motor statuses: {e}")
            raise DatabaseError(f"Failed to batch update motor statuses: {str(e)}")
    
    @staticmethod
    def delete_motor(motor_id: str, hard_delete: bool = False) -> str:
        """Delete or deactivate a motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            # Check if motor exists
            motor = db_manager.get_motor(motor_id)
            if not motor:
                raise NotFoundError("Motor not found")
            
            if hard_delete:
                query = "DELETE FROM motors WHERE motor_id = ?"
                db_manager.execute_update(query, (motor_id,))
                action = 'hard_deleted'
            else:
                query = "UPDATE motors SET active = 0 WHERE motor_id = ?"
                db_manager.execute_update(query, (motor_id,))
                action = 'deactivated'
            
            logger.info(f"Motor {motor_id} {action}")
            return action
        
        except (ValidationError, NotFoundError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error deleting motor: {e}")
            raise DatabaseError(f"Failed to delete motor: {str(e)}")
    
    @staticmethod
    def reactivate_motor(motor_id: str) -> bool:
        """Reactivate a deactivated motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            query = "UPDATE motors SET active = 1 WHERE motor_id = ?"
            rowcount = db_manager.execute_update(query, (motor_id,))
            
            if rowcount == 0:
                raise NotFoundError("Motor not found")
            
            logger.info(f"Motor {motor_id} reactivated")
            return True
        
        except (ValidationError, NotFoundError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error reactivating motor: {e}")
            raise DatabaseError(f"Failed to reactivate motor: {str(e)}")
    
    @staticmethod
    def get_all_active_motors() -> List[str]:
        """Get list of all active motors."""
        try:
            return db_manager.get_active_motors()
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error fetching active motors: {e}")
            raise DatabaseError(f"Failed to fetch active motors: {str(e)}")

    @staticmethod
    def get_motors(include_inactive: bool = False) -> List[Dict]:
        """Get motors with current status and active flag."""
        try:
            if include_inactive:
                query = """
                    SELECT motor_id, motor_type, installation_date, location, latest_status, active
                    FROM motors
                    ORDER BY motor_id ASC
                """
                rows = db_manager.execute_query(query)
            else:
                query = """
                    SELECT motor_id, motor_type, installation_date, location, latest_status, active
                    FROM motors
                    WHERE active = 1
                    ORDER BY motor_id ASC
                """
                rows = db_manager.execute_query(query)

            result = []
            for motor_id, motor_type, installation_date, location, latest_status, active in rows:
                status = 'Inactive' if int(active or 0) == 0 else (latest_status or 'Optimal')
                result.append({
                    'motor_id': motor_id,
                    'motor_type': motor_type,
                    'installation_date': installation_date,
                    'location': location,
                    'latest_status': latest_status,
                    'status': status,
                    'active': int(active or 0),
                })

            return result
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error fetching motors: {e}")
            raise DatabaseError(f"Failed to fetch motors: {str(e)}")


# Global motor service instance
motor_service = MotorService()
