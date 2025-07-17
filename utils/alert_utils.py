# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\alert_utils.py
import logging
from datetime import datetime, time
from typing import Dict, Any, List

from data import database as db_schema
from data import queries as db_queries
from utils.localization import _ # If any messages constructed here need translation
from utils.attendance_utils import _is_today_a_workday # Import helper from attendance_utils
import sqlite3 # For direct DB connection if needed, or use db_schema.create_connection
import config # For DATABASE_NAME

logger = logging.getLogger(__name__)

def get_absent_employees_for_alert(cutoff_time_str: str) -> List[Dict[str, Any]]:
    """
    Identifies active employees who are expected to work today,
    have not clocked in by the cutoff time, and are not on approved leave.

    Args:
        cutoff_time_str (str): The cutoff time in "HH:MM:SS" format.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing details
                                  of an absent employee (e.g., id, name, manager_id).
    """
    absent_employees = []
    today_date_str = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().time()
    
    try:
        cutoff_time_obj = time.fromisoformat(cutoff_time_str)
    except ValueError:
        logger.error(f"Invalid cutoff time format for absence alert: {cutoff_time_str}. Aborting check.")
        return []

    # Only proceed if current time is past the cutoff time
    if now_time < cutoff_time_obj:
        logger.info(f"Absence check skipped: Current time {now_time.strftime('%H:%M:%S')} is before cutoff {cutoff_time_str}.")
        return []

    active_employees = db_queries.get_all_employees_db(include_archived=False, status_filter=db_schema.STATUS_ACTIVE)

    for emp in active_employees:
        emp_id = emp[db_schema.COL_EMP_ID]
        
        if not _is_today_a_workday(datetime.now(), emp_id):
            continue

        if db_queries.is_employee_on_approved_leave_today(emp_id, today_date_str):
            continue

        try:
            with sqlite3.connect(config.DATABASE_NAME) as conn: # Use direct connection
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT 1 FROM {db_schema.TABLE_ATTENDANCE_LOG}
                    WHERE {db_schema.COL_ATT_EMP_ID} = ? AND DATE({db_schema.COL_ATT_CLOCK_IN}) = ?
                    LIMIT 1
                """, (emp_id, today_date_str))
                clocked_in_today = cursor.fetchone() is not None
        except Exception as e_att_check:
            logger.error(f"Error checking clock-in status for {emp_id} during absence alert: {e_att_check}")
            continue 

        if not clocked_in_today:
            absent_employees.append({
                "id": emp_id,
                "name": emp.get(db_schema.COL_EMP_NAME, "N/A"),
                "manager_id": emp.get(db_schema.COL_EMP_MANAGER_ID),
                "department_name": emp.get("department_name", "N/A") # Assuming 'department_name' is available from get_all_employees_db join
            })
            logger.info(f"Employee {emp_id} ({emp.get(db_schema.COL_EMP_NAME, 'N/A')}) identified as absent for alert.")
    
    return absent_employees