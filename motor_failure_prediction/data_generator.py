import sqlite3
import random
import time
import math
import os
from datetime import datetime
import sys
import logging
from typing import Dict, List, Tuple, Optional

# Configuration constants
DB_FILE = "motors.db"
SLEEP_INTERVAL = 5  # seconds between readings
BATCH_SIZE = 10  # number of readings to batch before commit
REPAIR_THRESHOLD = 50  # time steps before auto-repair
MAX_CONSECUTIVE_ERRORS = 10
HEALTH_THRESHOLDS = {'CRITICAL': 30, 'DEGRADING': 70}
MOTOR_SYNC_EVERY_CYCLES = 3
APP_ENV = os.getenv('APP_ENV', 'development').strip().lower()
ENFORCE_STATUS_FLOOR = os.getenv('ENFORCE_STATUS_FLOOR', 'true' if APP_ENV == 'production' else 'false').strip().lower() == 'true'
STATUS_FLOOR_CRITICAL = int(os.getenv('STATUS_FLOOR_CRITICAL', '2'))
STATUS_FLOOR_DEGRADING = int(os.getenv('STATUS_FLOOR_DEGRADING', '3'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('motor_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MotorState:
    """Enum-like class for motor states."""
    HEALTHY = 'Optimal'
    DEGRADING = 'Degrading'
    CRITICAL = 'Critical'

class MotorSimulator:
    """Manages the cyclical state and data generation for a single motor."""
    
    # Define sensor parameter order to ensure consistency
    SENSOR_PARAMS = [
        'setting1', 'setting2', 'setting3',
        's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
        's10', 's11', 's12', 's13', 's14', 's15', 's16', 's17',
        's18', 's19', 's20', 's21'
    ]
    
    def __init__(self, motor_id: str, initial_status: Optional[str] = None):
        self.motor_id = motor_id
        self.state = self._normalize_status(initial_status)
        self.health = self._initial_health_for_state(self.state)
        self.time_step = 0
        self.time_in_critical = 0
        self.repair_count = 0
        self.last_state_change = datetime.now()
        
        # Initialize base readings
        self.base_readings = self._get_initial_state()
        
        logger.info(f"Initialized simulator for motor {motor_id} with state={self.state} health={self.health:.1f}")

    @staticmethod
    def _normalize_status(status: Optional[str]) -> str:
        raw = str(status or '').strip().lower()
        if raw in {'critical'}:
            return MotorState.CRITICAL
        if raw in {'degrading', 'warning'}:
            return MotorState.DEGRADING
        return MotorState.HEALTHY

    @staticmethod
    def _initial_health_for_state(state: str) -> float:
        if state == MotorState.CRITICAL:
            return random.uniform(18.0, 28.0)
        if state == MotorState.DEGRADING:
            return random.uniform(42.0, 62.0)
        return random.uniform(82.0, 98.0)

    def _get_initial_state(self) -> Dict[str, float]:
        """Returns a baseline healthy reading with proper parameter names."""
        return {
            'setting1': 0.45, 'setting2': 0.6, 'setting3': 0.5,
            's1': 0.2, 's2': 0.3, 's3': 0.4, 's4': 0.25, 's5': 0.1,
            's6': 0.15, 's7': 0.35, 's8': 0.5, 's9': 0.6, 's10': 0.1,
            's11': 0.2, 's12': 0.4, 's13': 0.55, 's14': 0.7, 's15': 0.3,
            's16': 0.1, 's17': 0.4, 's18': 0.1, 's19': 0.1, 's20': 0.3,
            's21': 0.3
        }

    def _update_state(self) -> bool:
        """Update the state based on current health. Returns True if state changed."""
        old_state = self.state
        
        if self.health < HEALTH_THRESHOLDS['CRITICAL']:
            if self.state != MotorState.CRITICAL:
                self.time_in_critical = 0  # Reset timer when entering critical
                self.last_state_change = datetime.now()
            self.state = MotorState.CRITICAL
        elif self.health < HEALTH_THRESHOLDS['DEGRADING']:
            if self.state != MotorState.DEGRADING:
                self.last_state_change = datetime.now()
            self.state = MotorState.DEGRADING
            self.time_in_critical = 0
        else:
            if self.state != MotorState.HEALTHY:
                self.last_state_change = datetime.now()
            self.state = MotorState.HEALTHY
            self.time_in_critical = 0
        
        state_changed = old_state != self.state
        if state_changed:
            logger.info(f"Motor {self.motor_id} state changed: {old_state} → {self.state} (Health: {self.health:.1f}%)")
        
        return state_changed

    def _simulate_repair(self) -> None:
        """Simulate motor repair and reset to healthy state."""
        logger.warning(f"🔧 Simulating repair for {self.motor_id} (repair #{self.repair_count + 1})")
        self.health = random.uniform(85.0, 100.0)  # Don't always repair to 100%
        self.time_in_critical = 0
        self.repair_count += 1
        self.last_state_change = datetime.now()
        self._update_state()

    def force_state(self, target_state: str) -> bool:
        """Force simulator to a target health band to maintain baseline status mix."""
        previous = self.state
        if target_state == MotorState.CRITICAL:
            self.health = random.uniform(18.0, 28.0)
        elif target_state == MotorState.DEGRADING:
            self.health = random.uniform(42.0, 62.0)
        else:
            self.health = random.uniform(82.0, 98.0)
        self._update_state()
        return self.state != previous

    def advance_time_step(self) -> None:
        """Advance the simulation by one time step."""
        self.time_step += 1
        
        # Handle critical state repairs
        if self.state == MotorState.CRITICAL:
            self.time_in_critical += 1
            if self.time_in_critical > REPAIR_THRESHOLD:
                self._simulate_repair()
                return
        
        # Degrade health over time with some randomness
        if self.state == MotorState.HEALTHY:
            degradation = random.uniform(0.02, 0.08)
        elif self.state == MotorState.DEGRADING:
            degradation = random.uniform(0.08, 0.15)
        else:  # CRITICAL
            degradation = random.uniform(0.1, 0.2)
        
        # Add occasional random failures
        if random.random() < 0.001:  # 0.1% chance of sudden degradation
            degradation *= random.uniform(5, 10)
            logger.warning(f"Sudden degradation event for motor {self.motor_id}")
        
        self.health = max(0, self.health - degradation)
        self._update_state()

    def generate_reading(self) -> List[float]:
        """Generate a new sensor reading based on the current health and state."""
        # Create a fresh copy of base readings
        reading = self.base_readings.copy()
        health_factor = (100 - self.health) / 100.0

        # Determine noise and drift based on state
        if self.state == MotorState.HEALTHY:
            noise_level = 0.005
            drift_factor = 0.05
        elif self.state == MotorState.DEGRADING:
            noise_level = 0.02
            drift_factor = 0.2
        else:  # CRITICAL
            noise_level = 0.05
            drift_factor = 0.4

        # Apply cyclical patterns to key sensors
        cycle_time = self.time_step * 0.1
        reading['s4'] += health_factor * drift_factor + math.sin(cycle_time) * 0.01
        reading['s11'] += health_factor * drift_factor + math.cos(cycle_time * 0.7) * 0.008
        reading['s14'] += health_factor * drift_factor * 0.5 + math.sin(cycle_time * 1.3) * 0.005
        
        # Add temperature-like drift to some sensors
        if self.state != MotorState.HEALTHY:
            temp_drift = health_factor * 0.3
            reading['s7'] += temp_drift
            reading['s13'] += temp_drift * 0.8

        # Apply noise and ensure values stay within bounds [0, 1]
        for key in reading:
            jitter = random.uniform(-noise_level, noise_level)
            reading[key] = max(0.0, min(1.0, reading[key] + jitter))

        # Return values in consistent order
        return [reading[param] for param in self.SENSOR_PARAMS]

    def get_status_summary(self) -> Dict[str, any]:
        """Get a summary of the motor's current status."""
        return {
            'motor_id': self.motor_id,
            'health': round(self.health, 1),
            'state': self.state,
            'time_step': self.time_step,
            'time_in_critical': self.time_in_critical,
            'repair_count': self.repair_count,
            'last_state_change': self.last_state_change.isoformat()
        }

class DatabaseManager:
    """Handles database operations with batching and error recovery."""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.pending_readings = []
        
    def get_active_motors(self) -> List[Tuple[str, str]]:
        """Retrieve active motor IDs and their latest statuses from the database."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT motor_id, latest_status FROM motors WHERE active = 1 ORDER BY motor_id")
                return [(row[0], row[1] or 'Optimal') for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving active motors: {e}")
            return []

    def add_reading(self, motor_id: str, reading: List[float]) -> None:
        """Add a reading to the pending batch."""
        timestamp = datetime.now().isoformat()
        values = (motor_id, timestamp) + tuple(reading)
        self.pending_readings.append(values)

    def commit_batch(self) -> bool:
        """Commit all pending readings to the database."""
        if not self.pending_readings:
            return True
            
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO sensor_readings
                    (motor_id, timestamp, setting1, setting2, setting3, s1, s2, s3, s4, s5, s6, s7, s8, s9,
                     s10, s11, s12, s13, s14, s15, s16, s17, s18, s19, s20, s21)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.executemany(sql, self.pending_readings)
                conn.commit()
                
                readings_count = len(self.pending_readings)
                logger.debug(f"Successfully committed {readings_count} readings to database")
                self.pending_readings.clear()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error committing batch to database: {e}")
            return False

    def update_motor_status(self, motor_id: str, status: str) -> bool:
        """Update the latest status of a motor."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE motors SET latest_status = ? WHERE motor_id = ?",
                    (status, motor_id)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating motor status: {e}")
            return False

    def create_alert(self, motor_id: str, severity: str, message: str, acknowledged: int = 0) -> bool:
        """Insert alert row for motor transitions."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (motor_id, datetime.now().isoformat(), severity, message, int(bool(acknowledged))),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting alert for motor {motor_id}: {e}")
            return False

def main():
    """Main loop to run the motor simulators and insert data."""
    try:
        # Initialize database manager
        db_manager = DatabaseManager(DB_FILE)
        motors = db_manager.get_active_motors()
        motor_ids = [motor_id for motor_id, _ in motors]
        
        if not motor_ids:
            logger.error("No motors found. Please run database_setup.py first.")
            return

        # Initialize simulators
        simulators = {motor_id: MotorSimulator(motor_id, status) for motor_id, status in motors}
        
        logger.info(f"Starting motor simulation with {len(motor_ids)} motors")
        logger.info(f"Batch size: {BATCH_SIZE}, Sleep interval: {SLEEP_INTERVAL}s")
        logger.info(
            "Status floor enforcement: enabled=%s critical=%s degrading=%s",
            ENFORCE_STATUS_FLOOR,
            STATUS_FLOOR_CRITICAL,
            STATUS_FLOOR_DEGRADING,
        )
        print(f"🚀 Monitoring {len(motor_ids)} motors. Press CTRL+C to stop.\n")
        
        consecutive_errors = 0
        cycle_count = 0
        
        while True:
            cycle_count += 1
            batch_success = True
            status_updates = []

            # Sync simulator set with active motors so add/delete is picked up live.
            if cycle_count % MOTOR_SYNC_EVERY_CYCLES == 1:
                current_motor_status = {motor_id: status for motor_id, status in db_manager.get_active_motors()}
                current_motor_ids = set(current_motor_status.keys())
                sim_motor_ids = set(simulators.keys())

                added_motors = current_motor_ids - sim_motor_ids
                removed_motors = sim_motor_ids - current_motor_ids

                for motor_id in sorted(added_motors):
                    simulators[motor_id] = MotorSimulator(motor_id, current_motor_status.get(motor_id))
                    logger.info(f"➕ Added simulator for new motor: {motor_id}")

                for motor_id in sorted(removed_motors):
                    simulators.pop(motor_id, None)
                    logger.info(f"➖ Removed simulator for inactive/deleted motor: {motor_id}")

                if not simulators:
                    logger.warning("No active motors available. Waiting for new motors...")
                    time.sleep(SLEEP_INTERVAL)
                    continue

            if ENFORCE_STATUS_FLOOR and simulators:
                sorted_ids = sorted(simulators.keys())
                critical_count = max(0, min(STATUS_FLOOR_CRITICAL, len(sorted_ids)))
                degrading_count = max(0, min(STATUS_FLOOR_DEGRADING, len(sorted_ids) - critical_count))

                critical_ids = sorted_ids[:critical_count]
                degrading_ids = sorted_ids[critical_count:critical_count + degrading_count]

                for motor_id in critical_ids:
                    changed = simulators[motor_id].force_state(MotorState.CRITICAL)
                    if changed:
                        db_manager.create_alert(
                            motor_id,
                            'Critical',
                            'Critical floor enforced to preserve operational risk visibility.',
                            0,
                        )

                for motor_id in degrading_ids:
                    changed = simulators[motor_id].force_state(MotorState.DEGRADING)
                    if changed:
                        db_manager.create_alert(
                            motor_id,
                            'Degrading',
                            'Degrading floor enforced to preserve maintenance visibility.',
                            0,
                        )
            
            # Generate readings for all motors
            for motor_id, simulator in list(simulators.items()):
                try:
                    previous_state = simulator.state

                    # Advance simulation state
                    simulator.advance_time_step()
                    
                    # Generate and store reading
                    reading = simulator.generate_reading()
                    db_manager.add_reading(motor_id, reading)
                    
                    # Track status changes
                    status_updates.append((motor_id, simulator.state))

                    if simulator.state != previous_state:
                        if simulator.state == MotorState.CRITICAL:
                            db_manager.create_alert(
                                motor_id,
                                'Critical',
                                'Critical transition detected by simulator. Immediate inspection recommended.',
                                0,
                            )
                        elif simulator.state == MotorState.DEGRADING:
                            db_manager.create_alert(
                                motor_id,
                                'Degrading',
                                'Degrading transition detected by simulator. Schedule maintenance window.',
                                0,
                            )
                        else:
                            db_manager.create_alert(
                                motor_id,
                                'Optimal',
                                'Info: motor recovered to optimal operating range.',
                                1,
                            )
                    
                except Exception as e:
                    logger.error(f"Error processing motor {motor_id}: {e}")
                    batch_success = False
            
            # Commit batch to database
            if len(db_manager.pending_readings) >= BATCH_SIZE or cycle_count % 10 == 0:
                if not db_manager.commit_batch():
                    batch_success = False
            
            # Update motor statuses
            for motor_id, status in status_updates:
                db_manager.update_motor_status(motor_id, status)
            
            # Display current status
            if cycle_count % 5 == 0:  # Show status every 5 cycles
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Cycle {cycle_count}")
                for motor_id, sim in simulators.items():
                    status_icon = {
                        MotorState.HEALTHY: "✅",
                        MotorState.DEGRADING: "⚠️",
                        MotorState.CRITICAL: "🚨"
                    }[sim.state]
                    print(f"  {status_icon} {motor_id}: {sim.health:.1f}% ({sim.state})")
            
            # Handle consecutive errors
            if not batch_success:
                consecutive_errors += 1
                logger.warning(f"Batch failed (consecutive errors: {consecutive_errors})")
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping generator.")
                    break
            else:
                consecutive_errors = 0
            
            time.sleep(SLEEP_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("🛑 Data generator stopped by user")
        print("\n🛑 Stopping simulator...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Final commit of any pending readings
        if 'db_manager' in locals():
            db_manager.commit_batch()
        logger.info("Motor simulator shutdown complete")

if __name__ == '__main__':
    main()