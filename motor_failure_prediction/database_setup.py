import sqlite3
from datetime import datetime

DB_FILE = 'motors.db'


def ensure_column_exists(cursor, table_name, column_name, column_definition):
    """Add a column only when missing to keep upgrades idempotent."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        print(f"Added '{column_name}' column to {table_name} table.")

def create_database():
    """Create the motors database with proper tables and sample data."""
    conn = None
    try:
        # Connect to (or create) the database file
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("Creating database tables...")
        
        # --- Create the 'motors' table to store static info ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motors (
                motor_id TEXT PRIMARY KEY,
                motor_type TEXT NOT NULL,
                installation_date TEXT NOT NULL,
                location TEXT,
                latest_status TEXT DEFAULT 'Optimal',
                active INTEGER DEFAULT 1 
            )
        ''')

        # Ensure backward compatibility for old databases.
        ensure_column_exists(cursor, 'motors', 'location', 'TEXT')
        ensure_column_exists(cursor, 'motors', 'latest_status', "TEXT DEFAULT 'Optimal'")
        ensure_column_exists(cursor, 'motors', 'active', 'INTEGER DEFAULT 1')
        
        # --- Create the 'sensor_readings' table for the live feed ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motor_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                setting1 REAL, setting2 REAL, setting3 REAL,
                s1 REAL, s2 REAL, s3 REAL, s4 REAL, s5 REAL, s6 REAL,
                s7 REAL, s8 REAL, s9 REAL, s10 REAL, s11 REAL, s12 REAL,
                s13 REAL, s14 REAL, s15 REAL, s16 REAL, s17 REAL, s18 REAL,
                s19 REAL, s20 REAL, s21 REAL,
                FOREIGN KEY (motor_id) REFERENCES motors (motor_id) ON DELETE CASCADE
            )
        ''')
        
        # --- Create the 'alerts' table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                motor_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL CHECK (severity IN ('Optimal','Degrading', 'Critical', 'Warning')),
                message TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0 CHECK (acknowledged IN (0, 1)),
                FOREIGN KEY (motor_id) REFERENCES motors (motor_id) ON DELETE CASCADE
            )
        ''')

        # --- Create the 'users' table for authentication and alert preferences ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'operator',
                email_notifications INTEGER DEFAULT 1 CHECK (email_notifications IN (0, 1)),
                is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
                failed_otp_attempts INTEGER DEFAULT 0,
                otp_locked_until TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        ensure_column_exists(cursor, 'users', 'failed_otp_attempts', 'INTEGER DEFAULT 0')
        ensure_column_exists(cursor, 'users', 'otp_locked_until', 'TEXT')

        # --- Create the 'otp_codes' table for OTP login ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otp_codes (
                otp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp_code TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'login',
                expires_at TEXT NOT NULL,
                consumed INTEGER DEFAULT 0 CHECK (consumed IN (0, 1)),
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # --- Create the 'auth_sessions' table for bearer-token sessions ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                revoked INTEGER DEFAULT 0 CHECK (revoked IN (0, 1)),
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # --- Create the 'password_reset_tokens' table for password reset flow ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0 CHECK (used IN (0, 1)),
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        
        # --- Add sample motors to the database ---
        sample_motors = [
            ('Motor-PLT-01', 'AC Induction', '2025-12-15', 'Plant A - Line 1'),
            ('Motor-PLT-02', 'DC Brushless', '2025-12-18', 'Plant A - Line 2'),
            ('Motor-PLT-03', 'Servo Motor', '2025-12-22', 'Plant B - Packaging'),
            ('Motor-PLT-04', 'Stepper Motor', '2026-01-05', 'Plant B - Conveyor'),
            ('Motor-PLT-05', 'AC Induction', '2026-01-12', 'Plant C - Utilities'),
            ('Motor-PLT-06', 'DC Brushless', '2026-01-20', 'Plant C - Cooling'),
            ('Motor-PLT-07', 'Servo Motor', '2026-02-01', 'Plant D - Robotics'),
            ('Motor-PLT-08', 'Stepper Motor', '2026-02-14', 'Plant D - Assembly'),
            ('Motor-PLT-09', 'AC Induction', '2026-03-01', 'Plant E - Warehouse'),
        ]
        
        cursor.executemany(
            'INSERT OR IGNORE INTO motors (motor_id, motor_type, installation_date, location) VALUES (?, ?, ?, ?)', 
            sample_motors
        )
        
        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sensor_readings_motor_timestamp 
            ON sensor_readings (motor_id, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_motor_timestamp 
            ON alerts (motor_id, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_severity 
            ON alerts (severity, acknowledged)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_motors_active
            ON motors (active, motor_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_email_username
            ON users (email, username)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_otp_user_expiry
            ON otp_codes (user_id, purpose, expires_at, consumed)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_token_expiry
            ON auth_sessions (token, expires_at, revoked)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_password_reset_token_expiry
            ON password_reset_tokens (user_id, token, expires_at, used)
        ''')
        
        conn.commit()
        
        # Verification steps...
        cursor.execute("SELECT COUNT(*) FROM motors")
        motor_count = cursor.fetchone()[0]
        
        print(f"✅ Database '{DB_FILE}' updated/verified successfully!")
        print("✅ Tables ready: 'motors', 'sensor_readings', 'alerts', 'users', 'otp_codes', 'auth_sessions', and 'password_reset_tokens'")
        print(f"✅ {motor_count} sample motors present")
        print(f"✅ Foreign key constraints enabled")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating/updating database: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def verify_database():
    """Verify database structure and compatibility with Flask app."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("\n🔍 Verifying database compatibility...")
        
        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['motors', 'sensor_readings', 'alerts', 'users', 'otp_codes', 'auth_sessions']
        all_tables_exist = True
        for table in required_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing")
                all_tables_exist = False

        if not all_tables_exist: 
            return False
        
        # Check motors table structure
        cursor.execute("PRAGMA table_info(motors)")
        motor_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_motor_columns = {
            'motor_id': 'TEXT',
            'motor_type': 'TEXT',
            'installation_date': 'TEXT',
            'latest_status': 'TEXT',
            'active': 'INTEGER'
        }
        
        for col_name, col_type in required_motor_columns.items():
            if col_name in motor_columns:
                print(f"✅ Column '{col_name}' exists in motors table")
            else:
                print(f"❌ Column '{col_name}' missing from motors table")
                return False
        
        # Check alerts table structure
        cursor.execute("PRAGMA table_info(alerts)")
        alert_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_alert_columns = {
            'alert_id': 'INTEGER',
            'motor_id': 'TEXT',
            'timestamp': 'TEXT',
            'severity': 'TEXT',
            'message': 'TEXT',
            'acknowledged': 'INTEGER'
        }
        
        for col_name, col_type in required_alert_columns.items():
            if col_name in alert_columns:
                print(f"✅ Column '{col_name}' exists in alerts table")
            else:
                print(f"❌ Column '{col_name}' missing from alerts table")
                return False

        # Check users table structure
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1]: row[2] for row in cursor.fetchall()}
        required_user_columns = {
            'user_id': 'INTEGER',
            'username': 'TEXT',
            'email': 'TEXT',
            'password_hash': 'TEXT',
            'role': 'TEXT',
            'email_notifications': 'INTEGER',
            'is_active': 'INTEGER',
            'failed_otp_attempts': 'INTEGER',
            'otp_locked_until': 'TEXT'
        }

        for col_name in required_user_columns:
            if col_name in user_columns:
                print(f"✅ Column '{col_name}' exists in users table")
            else:
                print(f"❌ Column '{col_name}' missing from users table")
                return False
        
        # Check foreign key constraints are enabled
        cursor.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        if fk_enabled:
            print("✅ Foreign key constraints are enabled")
        else:
            print("⚠️  Foreign key constraints are disabled")

        print(f"\n✅ Database is compatible and ready for the alerting system!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database verification error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during verification: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def clear_sensor_data():
    """Clear all sensor readings and alerts (keeping motors table intact)."""
    conn = None
    try:
        # Add confirmation prompt for safety
        confirmation = input("⚠️  This will delete ALL sensor readings and alerts. Continue? (yes/no): ")
        if confirmation.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return False
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        cursor.execute("DELETE FROM sensor_readings")
        deleted_readings = cursor.rowcount
        
        cursor.execute("DELETE FROM alerts")
        deleted_alerts = cursor.rowcount
        
        # Reset motor status to Optimal
        cursor.execute("UPDATE motors SET latest_status = 'Optimal'")
        updated_motors = cursor.rowcount
        
        conn.commit()
        
        print(f"✅ Cleared {deleted_readings} sensor readings and {deleted_alerts} alerts.")
        print(f"✅ Reset status for {updated_motors} motors to 'Optimal'.")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error clearing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error clearing data: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def backup_database(backup_path=None):
    """Create a backup of the database."""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"motors_backup_{timestamp}.db"
    
    conn = None
    backup_conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        backup_conn = sqlite3.connect(backup_path)
        
        conn.backup(backup_conn)
        print(f"✅ Database backed up to: {backup_path}")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Backup error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during backup: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
        if backup_conn:
            backup_conn.close()

def main():
    """Main function to set up the database."""
    print("🚀 Setting up motors database...")
    
    if create_database():
        verify_database()
        print(f"\n🎉 Setup complete!")
    else:
        print("❌ Database setup failed.")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clear':
            clear_sensor_data()
        elif sys.argv[1] == '--verify':
            verify_database()
        elif sys.argv[1] == '--backup':
            backup_path = sys.argv[2] if len(sys.argv) > 2 else None
            backup_database(backup_path)
        else:
            print("Usage: python database_setup.py [--clear|--verify|--backup [path]]")
    else:
        main()