# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\zkteco_utils.py
import sqlite3
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import queue # For type hinting if q_comm is used

from zk import ZK, const # For ZKTeco device communication (from pyzk library)

import config
from data import database as db_schema
from data import queries as db_queries # For _get_employee_open_clock_in

logger = logging.getLogger(__name__)

zk_conn_instance: Optional[ZK] = None # Global or class-based connection instance

def connect_to_zkteco_device(ip: str, port: int, timeout: int = config.ZKTECO_TIMEOUT) -> Optional[ZK]:
    """Establishes a connection to the ZKTeco device."""
    global zk_conn_instance
    if zk_conn_instance: # If already connected, try to ensure it's live
        try:
            zk_conn_instance.get_time() # A simple command to check liveness
            logger.info("Already connected to ZKTeco device.")
            return zk_conn_instance
        except Exception:
            logger.warning("Existing ZKTeco connection seems dead, attempting to reconnect.")
            zk_conn_instance = None # Force reconnect
    
    conn = ZK(ip, port=port, timeout=timeout, password=0, force_udp=False, ommit_ping=False)
    try:
        logger.info(f"Attempting to connect to ZKTeco device at {ip}:{port}...")
        conn.connect()
        conn.disable_device() # Recommended before extensive operations
        logger.info("Successfully connected to ZKTeco device and disabled it for operations.")
        zk_conn_instance = conn
        return conn # Return the connection object
    except ConnectionRefusedError as cre:
        logger.error(f"Connection refused by ZKTeco device at {ip}:{port}: {cre}")
        raise ConnectionRefusedError(f"Connection refused by device at {ip}:{port}. Ensure device is on and accessible.")
    except TimeoutError as te:
        logger.error(f"Connection to ZKTeco device at {ip}:{port} timed out: {te}")
        raise TimeoutError(f"Connection to device at {ip}:{port} timed out. Check network or increase timeout.")
    except Exception as e:
        logger.error(f"Failed to connect to ZKTeco device at {ip}:{port}. Error: {type(e).__name__} - {e}")
        if conn and hasattr(conn, 'disconnect'):
            conn.disconnect()
        zk_conn_instance = None
        # Re-raise a more generic error or the original one if specific handling is done by caller
        raise ConnectionError(f"Failed to connect to ZKTeco device: {e}")

def disconnect_from_zkteco_device(conn: Optional[ZK]):
    """Enables and disconnects from the ZKTeco device."""
    global zk_conn_instance
    if conn:
        try:
            if conn.is_connect:
                conn.enable_device()
                logger.info("ZKTeco device enabled.")
                conn.disconnect()
                logger.info("Disconnected from ZKTeco device.")
        except Exception as e:
            logger.error(f"Error during ZKTeco disconnect/enable: {e}")
    zk_conn_instance = None

def get_employee_device_id_map_db() -> Dict[str, str]:
    """Fetches a map of device_user_id to system_employee_id."""
    mapping = {}
    with sqlite3.connect(config.DATABASE_NAME) as conn_db:
        cursor = conn_db.cursor()
        cursor.execute(f"SELECT {db_schema.COL_EMP_ID}, {db_schema.COL_EMP_DEVICE_USER_ID} FROM {db_schema.TABLE_EMPLOYEES} WHERE {db_schema.COL_EMP_DEVICE_USER_ID} IS NOT NULL AND {db_schema.COL_EMP_DEVICE_USER_ID} != ''")
        for row in cursor.fetchall():
            mapping[str(row[1])] = str(row[0]) # device_user_id : system_emp_id
    return mapping

def sync_attendance_from_zkteco(device_ip: str, device_port: int, q_comm: Optional[queue.Queue] = None) -> Dict[str, int]:
    """
    Connects to ZKTeco device, downloads attendance logs, and processes them.
    """
    logger.info(f"Starting attendance sync from ZKTeco device at {device_ip}:{device_port}")
    conn = connect_to_zkteco_device(device_ip, device_port)
    # connect_to_zkteco_device will raise an error if connection fails, so conn should be valid here.

    summary = {"processed_device_logs": 0, "db_clock_ins": 0, "db_clock_outs": 0, "errors": 0, "unknown_user_id": 0, "skipped_duplicates": 0, "skipped_no_open_in": 0, "skipped_already_out":0}
    db_connection = None
    total_device_logs = 0

    try:
        db_connection = sqlite3.connect(config.DATABASE_NAME)
        db_connection.row_factory = sqlite3.Row
        db_cursor = db_connection.cursor()

        employee_device_map = get_employee_device_id_map_db()

        attendance_records = conn.get_attendance()
        logger.info(f"Retrieved {len(attendance_records)} logs from device.")
        total_device_logs = len(attendance_records)
        summary["processed_device_logs"] = total_device_logs

        if not attendance_records:
            return summary

        attendance_records.sort(key=lambda x: x.timestamp)
        processed_count_for_progress = 0

        if q_comm:
            q_comm.put({"type": "progress_init", "total": total_device_logs})

        for rec_idx, rec in enumerate(attendance_records):
            device_user_id = str(rec.user_id)
            system_emp_id = employee_device_map.get(device_user_id)

            if not system_emp_id:
                logger.warning(f"Device Log {rec_idx+1}: Unknown device user ID '{device_user_id}'. Skipping.")
                summary["unknown_user_id"] += 1
                continue
            
            processed_count_for_progress += 1
            if q_comm and processed_count_for_progress % 10 == 0:
                q_comm.put({"type": "progress_update", "current": processed_count_for_progress, "total": total_device_logs})

            log_datetime_obj = rec.timestamp
            # ... (rest of the sync logic from hr_management_system.py) ...
            # This includes checking for duplicates, open clock-ins, and inserting/updating logs.
            # Ensure to use db_queries._get_employee_open_clock_in and other necessary db_queries functions.

        db_connection.commit()
        logger.info("ZKTeco attendance sync database operations committed.")

    except Exception as e:
        if db_connection:
            db_connection.rollback()
        if q_comm:
            q_comm.put({"type": "error", "data": e})
            return summary 
        raise db_queries.DatabaseOperationError(f"ZKTeco sync failed due to an internal error: {e}")
    finally:
        disconnect_from_zkteco_device(conn)
        if db_connection:
            db_connection.close()
    logger.info(f"ZKTeco sync finished. Summary: {summary}")
    return summary