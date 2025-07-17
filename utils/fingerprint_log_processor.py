# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\fingerprint_log_processor.py
import csv
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta # Added timedelta
from utils.localization import _ # For translating event types

logger = logging.getLogger(__name__)

# Event Codes as per user's request
EVENT_CODE_CHECK_IN = 0
EVENT_CODE_CHECK_OUT = 1
EVENT_CODE_BREAK_OUT = 2
EVENT_CODE_BREAK_IN = 3

# Define expected CSV headers as a module-level constant
EXPECTED_CSV_HEADERS = ['employeeid', 'timestamp', 'eventcode']

# Mapping for event codes to their translation keys
EVENT_TYPE_TRANSLATION_MAP = {
    EVENT_CODE_CHECK_IN: "fp_event_check_in",
    EVENT_CODE_CHECK_OUT: "fp_event_check_out",
    EVENT_CODE_BREAK_OUT: "fp_event_break_out",
    EVENT_CODE_BREAK_IN: "fp_event_break_in",
}

def get_event_type_display(event_code: int) -> str:
    """Translates event code to a display string."""
    translation_key = EVENT_TYPE_TRANSLATION_MAP.get(event_code, "fp_event_unknown")
    return _(translation_key)

def parse_fingerprint_csv(filepath: str) -> List[Dict[str, Any]]: # Kept Any for broader compatibility, specific types below
    """
    Parses a fingerprint log CSV file.
    Assumes CSV columns: EmployeeID, Timestamp (YYYY-MM-DD HH:MM:SS), EventCode, DeviceID (optional)
    """
    parsed_logs = []
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as csvfile: # utf-8-sig for BOM
            reader = csv.DictReader(csvfile)
            # Normalize header names (case-insensitive, remove spaces)
            reader.fieldnames = [name.lower().replace(' ', '') for name in reader.fieldnames or []]
            
            found_headers_set = set(reader.fieldnames or [])
            missing_headers = [h for h in EXPECTED_CSV_HEADERS if h not in found_headers_set]
            if missing_headers:
                error_msg = f"CSV file is missing required headers: {', '.join(missing_headers)}. Found: {reader.fieldnames or 'None'}."
                logger.error(error_msg)
                raise ValueError(error_msg)

            for row_num, row in enumerate(reader, 1):
                try:
                    emp_id = row.get('employeeid', '').strip()
                    timestamp_str = row.get('timestamp', '').strip()
                    event_code_str = row.get('eventcode', '').strip()
                    device_id = row.get('deviceid', '').strip() # Optional

                    if not all([emp_id, timestamp_str, event_code_str]):
                        logger.warning(f"Skipping row {row_num} due to missing essential data: {row}")
                        continue

                    # Validate and convert data types
                    timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    event_code = int(event_code_str)

                    parsed_logs.append({
                        "employee_id": emp_id,
                        "timestamp_obj": timestamp_dt,
                        "timestamp_str": timestamp_dt.strftime('%Y-%m-%d %H:%M:%S'), # Store formatted string too
                        "event_code": event_code,
                        "event_type_display": get_event_type_display(event_code),
                        "device_id": device_id if device_id else "N/A"
                    })
                except ValueError as ve:
                    logger.warning(f"Skipping row {row_num} due to data conversion error: {ve}. Row: {row}")
                except Exception as e_row:
                    logger.warning(f"Skipping row {row_num} due to unexpected error: {e_row}. Row: {row}")
    except Exception as e:
        logger.error(f"Error parsing fingerprint CSV file '{filepath}': {e}", exc_info=True)
        raise # Re-raise to be caught by UI
    return parsed_logs

def calculate_daily_event_summary(parsed_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates daily summaries from parsed fingerprint logs.
    Groups by employee and date, finds first check-in, last check-out,
    and calculates total work and break durations.

    Args:
        parsed_logs: A list of dictionaries as returned by parse_fingerprint_csv.

    Returns:
        A list of dictionaries, each representing a daily summary for an employee.
    """
    daily_summaries = {} # Key: (employee_id, date_str), Value: summary_dict

    # Sort logs by employee, then by timestamp to process events chronologically
    sorted_logs = sorted(parsed_logs, key=lambda x: (x["employee_id"], x["timestamp_obj"]))

    for log in sorted_logs:
        emp_id = log["employee_id"]
        timestamp: datetime = log["timestamp_obj"]
        date_str = timestamp.strftime("%Y-%m-%d")
        event_code = log["event_code"]

        summary_key = (emp_id, date_str)
        if summary_key not in daily_summaries:
            daily_summaries[summary_key] = {
                "employee_id": emp_id,
                "date": date_str,
                "first_check_in": None,
                "last_check_out": None,
                "work_intervals": [], # List of (check_in_time, check_out_time)
                "break_intervals": [], # List of (break_out_time, break_in_time)
                "last_event_time": None,
                "last_event_type": None, # To track open sessions
                "raw_events_count": 0
            }
        
        current_summary = daily_summaries[summary_key]
        current_summary["raw_events_count"] += 1

        if event_code == EVENT_CODE_CHECK_IN:
            if current_summary["first_check_in"] is None:
                current_summary["first_check_in"] = timestamp
            if current_summary["last_event_type"] == EVENT_CODE_BREAK_IN or current_summary["last_event_type"] is None: # Starting work or returning from break
                current_summary["last_event_time"] = timestamp
                current_summary["last_event_type"] = EVENT_CODE_CHECK_IN

        elif event_code == EVENT_CODE_CHECK_OUT:
            if current_summary["last_event_type"] == EVENT_CODE_CHECK_IN and current_summary["last_event_time"]:
                current_summary["work_intervals"].append((current_summary["last_event_time"], timestamp))
            current_summary["last_check_out"] = timestamp
            current_summary["last_event_type"] = EVENT_CODE_CHECK_OUT # Mark session as ended

        elif event_code == EVENT_CODE_BREAK_OUT:
            if current_summary["last_event_type"] == EVENT_CODE_CHECK_IN and current_summary["last_event_time"]: # Started break while checked in
                current_summary["work_intervals"].append((current_summary["last_event_time"], timestamp)) # End current work interval
            current_summary["last_event_time"] = timestamp
            current_summary["last_event_type"] = EVENT_CODE_BREAK_OUT

        elif event_code == EVENT_CODE_BREAK_IN:
            if current_summary["last_event_type"] == EVENT_CODE_BREAK_OUT and current_summary["last_event_time"]:
                current_summary["break_intervals"].append((current_summary["last_event_time"], timestamp))
            current_summary["last_event_time"] = timestamp # Time of returning from break, potential start of new work interval
            current_summary["last_event_type"] = EVENT_CODE_BREAK_IN

    # Calculate durations
    result_list = []
    for summary in daily_summaries.values():
        total_work_duration = timedelta()
        for start, end in summary["work_intervals"]:
            total_work_duration += (end - start)
        
        total_break_duration = timedelta()
        for start, end in summary["break_intervals"]:
            total_break_duration += (end - start)

        summary["total_work_duration_seconds"] = total_work_duration.total_seconds()
        summary["total_break_duration_seconds"] = total_break_duration.total_seconds()
        summary["total_work_duration_str"] = str(total_work_duration).split('.')[0] # HH:MM:SS
        summary["total_break_duration_str"] = str(total_break_duration).split('.')[0] # HH:MM:SS
        summary["first_check_in_str"] = summary["first_check_in"].strftime('%H:%M:%S') if summary["first_check_in"] else "N/A"
        summary["last_check_out_str"] = summary["last_check_out"].strftime('%H:%M:%S') if summary["last_check_out"] else "N/A"
        
        # Remove intermediate calculation fields if not needed for final output
        del summary["work_intervals"]; del summary["break_intervals"]; del summary["last_event_time"]; del summary["last_event_type"]
        result_list.append(summary)
        
    return result_list