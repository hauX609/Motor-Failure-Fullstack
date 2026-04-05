"""
Database connection and management for Motor Monitoring System.
Handles all database operations with proper error handling.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple
import pandas as pd

from config import DB_FILE, DB_TIMEOUT, now_iso
from utils.errors import DatabaseError, NotFoundError


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_file: str = DB_FILE, timeout: int = DB_TIMEOUT):
        """Initialize database manager."""
        self.db_file = db_file
        self.timeout = timeout
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file, timeout=self.timeout)
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(str(e))
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(str(e))
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False) -> Optional[tuple]:
        """Execute a SELECT query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise DatabaseError(f"Query failed: {str(e)}")
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Update execution error: {e}")
            raise DatabaseError(f"Update failed: {str(e)}")
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute batch INSERT/UPDATE/DELETE operations."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return len(params_list)
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            raise DatabaseError(f"Batch operation failed: {str(e)}")
    
    def execute_pandas_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute query and return pandas DataFrame."""
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Pandas query error: {e}")
            raise DatabaseError(f"Pandas query failed: {str(e)}")
    
    def get_user(self, identifier: str) -> Optional[Dict]:
        """Get user by username or email."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, username, email, password_hash, role, 
                           email_notifications, is_active, created_at
                    FROM users
                    WHERE (username = ? OR email = ?) AND is_active = 1
                    """,
                    (identifier, identifier.lower())
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get user: {str(e)}")
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, email, is_active FROM users WHERE email = ?",
                    (email.lower(),)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get user by email: {str(e)}")
    
    def get_motor(self, motor_id: str) -> Optional[Dict]:
        """Get motor by ID."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM motors WHERE motor_id = ?",
                    (motor_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get motor: {str(e)}")
    
    def get_active_motors(self) -> List[str]:
        """Get list of all active motors."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT DISTINCT motor_id FROM motors WHERE motor_id IS NOT NULL AND active = 1")
                    motor_ids = [row[0] for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    cursor.execute("SELECT DISTINCT motor_id FROM sensor_readings WHERE motor_id IS NOT NULL")
                    motor_ids = [row[0] for row in cursor.fetchall()]
            return motor_ids
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get active motors: {str(e)}")
    
    def cleanup_expired_data(self, table: str, timestamp_col: str, current_time: str) -> int:
        """Clean up expired data from auth tables."""
        try:
            query = f"DELETE FROM {table} WHERE {timestamp_col} < ? OR (consumed = 1 AND {timestamp_col} < ?)"
            return self.execute_update(query, (current_time, current_time))
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup data: {str(e)}")


# Global database manager instance
db_manager = DatabaseManager()
