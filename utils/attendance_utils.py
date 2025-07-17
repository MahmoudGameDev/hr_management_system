# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\attendance_utils.py
import logging
import sqlite3 # Added import for sqlite3
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List

from data import database as db_schema
from data import queries as db_queries # Assuming db_queries has general DB interaction helpers
import config # For default fallbacks if settings are not in DB yet
from utils.localization import _

logger = logging.getLogger(__name__)


def _is_today_a_workday(date_obj: datetime, employee_id: Optional[str] = None) -> bool:
    """
    Placeholder function to determine if a given date is a workday.
    Currently assumes Mon-Fri are workdays.
    TODO: Integrate with company holidays and employee-specific schedules.
    """
    # 0 = Monday, 6 = Sunday
    if date_obj.weekday() >= 5:  # Saturday or Sunday
        return False

    # Example: Check against a list of public holidays
    # public_holidays = db_queries.get_public_holidays_for_date(date_obj.strftime("%Y-%m-%d"))
    # if date_obj.strftime("%Y-%m-%d") in public_holidays:
    #     return False
    return True

def get_employee_attendance_status_today(employee_id: str) -> Dict[str, Any]:
    """
    Determines the attendance status of an employee for the current day.
    Includes clock-in/out times, lateness information.
    """
    today_date_str = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()

    status_info = {
        "employee_id": employee_id,
        "checked_in": False,
        "checked_out": False,
        "clock_in_time_obj": None,
        "clock_out_time_obj": None,
        "is_late": None,  # True, False, or None if not applicable/determinable
        "lateness_minutes": None,
        "scheduled_start_time_today": None,
        "on_leave_today": False,
        "is_workday_today": _is_today_a_workday(now, employee_id),
        "status_message": "" # A human-readable summary
    }

    # Check if employee is on approved leave today
    # TODO: Implement db_queries.is_employee_on_approved_leave_today(employee_id, today_date_str)
    # For now, assuming a function exists or defaulting to False
    try:
        if hasattr(db_queries, 'is_employee_on_approved_leave_today'):
            status_info["on_leave_today"] = db_queries.is_employee_on_approved_leave_today(employee_id, today_date_str)
        else: # Fallback if function not yet implemented in db_queries
            logger.warning("db_queries.is_employee_on_approved_leave_today not found, defaulting on_leave_today to False.")
            status_info["on_leave_today"] = False
    except Exception as e:
        logger.error(f"Error checking leave status for {employee_id}: {e}")
        status_info["on_leave_today"] = False # Default to not on leave on error

    # 1. Get employee's clock-in/out logs for today
    logs_today = []
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn: # Use sqlite3.connect
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT {db_schema.COL_ATT_CLOCK_IN}, {db_schema.COL_ATT_CLOCK_OUT}
                FROM {db_schema.TABLE_ATTENDANCE_LOG}
                WHERE {db_schema.COL_ATT_EMP_ID} = ? AND DATE({db_schema.COL_ATT_CLOCK_IN}) = ?
                ORDER BY {db_schema.COL_ATT_CLOCK_IN} ASC
            """, (employee_id, today_date_str))
            logs_today = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching attendance logs for {employee_id} today: {e}")
        status_info["status_message"] = _("error_fetching_logs_message") # Needs localization key
        return status_info

    if logs_today:
        first_log = logs_today[0]
        if first_log[0]: # COL_ATT_CLOCK_IN is the first selected column (index 0)
            status_info["clock_in_time_obj"] = datetime.fromisoformat(first_log[0])
            status_info["checked_in"] = True

        # Find the last clock-out time if multiple check-ins/outs occurred
        last_checkout_val = None
        for log_row in reversed(logs_today):
            if log_row[1]: # COL_ATT_CLOCK_OUT is the second selected column (index 1)
                last_checkout_val = log_row[1]
                break
        if last_checkout_val:
            status_info["clock_out_time_obj"] = datetime.fromisoformat(last_checkout_val)
            status_info["checked_out"] = True

    # 2. Determine if late (only if checked in and feature enabled)
    # Ensure SETTING_ keys exist in db_schema and config.DEFAULT_CONFIG
    default_enable_lateness_display = config.DEFAULT_CONFIG.get(db_schema.SETTING_ENABLE_INSTANT_LATENESS_DISPLAY, "True")
    enable_lateness_check_str = db_schema.get_app_setting_db(
        db_schema.SETTING_ENABLE_INSTANT_LATENESS_DISPLAY, # This key should exist in db_schema.py
        default_enable_lateness_display
    )
    enable_lateness_check = enable_lateness_check_str.lower() == "true"

    if status_info["checked_in"] and enable_lateness_check and status_info["is_workday_today"] and not status_info["on_leave_today"]:
        # Get scheduled start time from app settings, with a fallback to config.py's default structure
        default_start_time_val = config.DEFAULT_CONFIG["WorkSchedule"].get("standard_start_time", "09:00:00")
        default_start_time_str = db_schema.get_app_setting_db(
            db_schema.SETTING_STANDARD_START_TIME, # Corrected constant
            default_start_time_val
        )
        default_grace_period_val = config.DEFAULT_CONFIG.get(db_schema.SETTING_LATE_ARRIVAL_ALLOWED_MINUTES, "15")
        grace_period_minutes_str = db_schema.get_app_setting_db(
            db_schema.SETTING_LATE_ARRIVAL_ALLOWED_MINUTES,
            default_grace_period_val
        )
        try:
            scheduled_start_time_obj = time.fromisoformat(default_start_time_str)
            scheduled_start_datetime = datetime.combine(now.date(), scheduled_start_time_obj)
            status_info["scheduled_start_time_today"] = scheduled_start_datetime

            grace_period_minutes = int(grace_period_minutes_str)
            
            # Effective allowed arrival time is scheduled start + grace period
            # Lateness is calculated from the scheduled start time itself for reporting minutes.
            allowed_arrival_datetime_for_check = scheduled_start_datetime + timedelta(minutes=grace_period_minutes)

            if status_info["clock_in_time_obj"] > allowed_arrival_datetime_for_check:
                status_info["is_late"] = True
                # Calculate lateness from the actual scheduled start time
                lateness_delta = status_info["clock_in_time_obj"] - scheduled_start_datetime
                status_info["lateness_minutes"] = max(0, round(lateness_delta.total_seconds() / 60)) # Ensure non-negative
            else:
                status_info["is_late"] = False
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid format for work schedule time settings or grace period: {e}. Start: '{default_start_time_str}', Grace: '{grace_period_minutes_str}'")
            status_info["is_late"] = None # Cannot determine

    # 3. Construct status_info["status_message"]
    status_parts = []
    if status_info["on_leave_today"]:
        status_parts.append(_("status_on_leave")) # Needs localization key
    elif not status_info["is_workday_today"]:
        status_parts.append(_("status_non_workday")) # Needs localization key
    elif status_info["checked_in"]:
        status_parts.append(_("status_checked_in"))
        if status_info["is_late"] is True:
            lateness_msg = _("status_lateness_detail", minutes=status_info["lateness_minutes"])
            status_parts.append(f"{_('status_late')} ({lateness_msg})")
        elif status_info["is_late"] is False:
            status_parts.append(_("status_on_time"))
        
        if status_info["checked_out"]:
            status_parts.append(_("status_checked_out"))
    else: # Not checked in, is a workday, and not on leave
        status_parts.append(_("status_absent"))
    status_info["status_message"] = " | ".join(filter(None, status_parts))

    return status_info