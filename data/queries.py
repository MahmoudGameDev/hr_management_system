# hr_dashboard_project/data/queries.py
import sqlite3
from typing import Optional, List, Dict, Union, Any, Tuple
from datetime import datetime, timedelta, date as dt_date
import os
import hashlib # Added missing import for password hashing
# Add project root to sys.path to allow importing 'config'
import sys
import logging # Added logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config # Now this should work
from . import database # To import constants from database.py in the same directory
from utils.localization import _
from utils.exceptions import UserNotFoundError, EmployeeNotFoundError, DatabaseOperationError, InvalidInputError, AlreadyClockedInError, NotClockedInError

# Remove this selective import to avoid confusion and rely solely on the 'database' alias


logger = logging.getLogger(__name__)

# ... other existing functions ...
def update_employee_details_db(emp_id: str, new_details: Dict[str, Union[str, float, None]]) -> bool: # Allow None for values
    """Updates details of an existing employee.
    Raises:
        EmployeeNotFoundError: If the employee to update is not found.
        DatabaseOperationError: If a database error occurs during update.
    Returns:
        bool: True if update was successful.
    """
    employee_to_update = _find_employee_by_id(emp_id)

    if not employee_to_update:
        logger.warning(f"Attempted to update non-existent employee ID: {emp_id}")
        raise EmployeeNotFoundError(f"Employee with ID '{emp_id}' not found for update.")

    set_clauses = []
    params = []

    # Get actual column names from the employees table to be safe
    actual_employee_table_columns = []
    with sqlite3.connect(config.DATABASE_NAME) as conn_schema_check:
        cursor_schema = conn_schema_check.cursor()
        actual_employee_table_columns = [info[1] for info in cursor_schema.execute(f"PRAGMA table_info({TABLE_EMPLOYEES})")]

    for key, value in new_details.items():
        # Only attempt to update actual columns that exist in the TABLE_EMPLOYEES
        if key in actual_employee_table_columns:
            if key == COL_EMP_START_DATE and value: # Validate start_date format if provided and not empty
                try:
                    datetime.strptime(str(value), '%Y-%m-%d') # Ensure value is string for strptime
                except ValueError:
                    raise InvalidInputError(_("invalid_date_format_yyyy_mm_dd_error", field="Start Date"))
            if key == "exclude_vacation_policy": # Validate boolean-like integer
                 if value not in [0, 1]:
                     raise InvalidInputError(f"Invalid value for exclude_vacation_policy: {value}. Must be 0 or 1.")
            # Validate status if it's being updated directly (though terminate_employee_db is preferred for termination) # Corrected: Use database.VALID_EMPLOYEE_STATUSES
            if key == database.COL_EMP_STATUS and value not in database.VALID_EMPLOYEE_STATUSES: # Corrected
                raise InvalidInputError(f"Invalid status: '{value}'. Valid statuses are: {', '.join(database.VALID_EMPLOYEE_STATUSES)}")

            # value can be str, float, int, or None (for fields that allow NULL)
            set_clauses.append(f"{key} = ?")
            params.append(value)
        elif key == COL_EMP_DEPARTMENT: # This key might be in new_details if old code passed it
            logger.warning(f"Skipping update for derived field '{database.COL_EMP_DEPARTMENT}'. Update '{database.COL_EMP_DEPARTMENT_ID}' instead.")
        # else: # Optional: log if a key from new_details is entirely unexpected
            # logger.debug(f"Skipping update for key '{key}' as it's not an actual column in {TABLE_EMPLOYEES}.")

    if not set_clauses:
        logger.info(f"No new details provided to update for employee ID: {emp_id}.")
        return True # Or False, depending on desired behavior for no changes

    params.append(emp_id.upper()) # For the WHERE clause, ensure emp_id is uppercase
    sql_query = f"UPDATE {database.TABLE_EMPLOYEES} SET {', '.join(set_clauses)} WHERE UPPER({database.COL_EMP_ID}) = ?"

    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query, tuple(params))
            conn.commit()
        logger.info(f"Employee (ID: {emp_id}) details updated successfully in database. {cursor.rowcount} row(s) affected.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error during update for employee ID {emp_id}: {e}\nQuery: {sql_query}\nParams: {params}")
        raise DatabaseOperationError(f"Failed to update employee {emp_id}: {e}")

def search_employees(search_term: str, search_field: str, include_archived: bool = False) -> List[Dict[str, Union[str, float]]]:
    query = "" # Initialize query to avoid UnboundLocalError
    params = []
    # Build the base query
    query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} AS "{database.COL_EMP_DEPARTMENT}"
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
         
    """
    base_where_clauses = []
    if not include_archived:
        base_where_clauses.append(f"(e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)")

    # This was missed, should be database.COL_EMP_IS_ARCHIVED
    if search_field == database.COL_EMP_ID: # Ensure COL_EMP_ID is prefixed

        base_where_clauses.append(f"UPPER(e.{database.COL_EMP_ID}) = UPPER(?)")
        params.append(search_term)
    elif search_field == database.COL_EMP_DEPARTMENT: # Ensure COL_EMP_DEPARTMENT is prefixed
        def get_department_summary_report() -> List[Dict[str, Union[str, int, float]]]:
            pass
        
def list_departments_db() -> List[Dict]:
    """Lists all departments."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT {database.COL_DEPT_ID}, {database.COL_DEPT_NAME}, {database.COL_DEPT_DESCRIPTION} FROM {database.TABLE_DEPARTMENTS} ORDER BY {database.COL_DEPT_NAME}")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error listing departments: {e}")
        raise DatabaseOperationError(f"Failed to list departments: {e}")

logger = logging.getLogger(__name__)

# --- Password Hashing Utilities ---
# These are used by user management queries.
# Ideally, these might move to a utils.auth module later.
def hash_password(password: str) -> str:
    """Hashes a password using SHA256 and a salt."""
    salt = os.urandom(16)  # Generate a random 16-byte salt
    salted_password = salt + password.encode('utf-8')
    hashed_password = hashlib.sha256(salted_password).hexdigest()
    return f"{salt.hex()}${hashed_password}" # Store salt with hash

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verifies a provided password against a stored salted hash."""
    try:
        salt_hex, hashed_password = stored_password_hash.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        salted_provided_password = salt + provided_password.encode('utf-8')
        hashed_provided_password = hashlib.sha256(salted_provided_password).hexdigest()
        return hashed_provided_password == hashed_password
    except (ValueError, TypeError): # Handles cases where stored_password_hash is not in expected format
        return False
logger = logging.getLogger(__name__)
# --- Employee Queries ---

def get_next_employee_id_db() -> str:
    """
    Retrieves the next available employee ID from the app_counters table.
    Increments the counter after retrieval.
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN EXCLUSIVE TRANSACTION") # Lock for atomicity
            cursor.execute(f"SELECT {database.COL_COUNTER_VALUE} FROM {database.TABLE_APP_COUNTERS} WHERE {database.COL_COUNTER_NAME} = ?", # Corrected
                           (database.COUNTER_NEXT_EMPLOYEE_ID,))
            row = cursor.fetchone()
            if row: # Corrected indentation
                next_id_num = row[0] # Example: 1
                next_id_str = f"{config.EMPLOYEE_ID_PREFIX}{next_id_num:04d}" # Uses prefix from config
                cursor.execute(f"UPDATE {database.TABLE_APP_COUNTERS} SET {database.COL_COUNTER_VALUE} = ? WHERE {database.COL_COUNTER_NAME} = ?",
                               (next_id_num + 1, database.COUNTER_NEXT_EMPLOYEE_ID))
                conn.commit()
                return next_id_str
            else:
                # This case should ideally not happen if init_db correctly initializes the counter
                logger.error(f"Counter '{database.COUNTER_NEXT_EMPLOYEE_ID}' not found in {database.TABLE_APP_COUNTERS}.")
                conn.rollback() # Rollback if counter not found
                raise database.DatabaseOperationError(f"Counter '{database.COUNTER_NEXT_EMPLOYEE_ID}' not found.")
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error getting next employee ID: {e}")
            raise database.DatabaseOperationError(f"Failed to get next employee ID: {e}")


def add_employee_db(emp_id: str, name: str, department_id: Optional[int], position: str, salary: float,
                    vacation_days: int, status: str = database.STATUS_ACTIVE, phone: Optional[str] = None,
                    email: Optional[str] = None, photo_path: Optional[str] = None,
                    gender: Optional[str] = None, start_date: Optional[str] = None,
                    marital_status: Optional[str] = None, education: Optional[str] = None,
                    employment_history: Optional[str] = None, manager_id: Optional[str] = None,
                    device_user_id: Optional[str] = None, exclude_vacation_policy: bool = False,
                    current_shift: str = "Morning") -> None:
    """Adds a new employee to the database."""
    query = f"""
        INSERT INTO {database.TABLE_EMPLOYEES} (
            "{database.COL_EMP_ID}", "{database.COL_EMP_NAME}", "{database.COL_EMP_DEPARTMENT_ID}", "{database.COL_EMP_POSITION}",
            "{database.COL_EMP_SALARY}", "{database.COL_EMP_VACATION_DAYS}", "{database.COL_EMP_STATUS}", "{database.COL_EMP_PHONE}",
            "{database.COL_EMP_EMAIL}", "{database.COL_EMP_PHOTO_PATH}", "{database.COL_EMP_GENDER}", "{database.COL_EMP_START_DATE}",
            "{database.COL_EMP_MARITAL_STATUS}", "{database.COL_EMP_EDUCATION}", "{database.COL_EMP_EMPLOYMENT_HISTORY}", "{database.COL_EMP_CURRENT_SHIFT}",
            "{database.COL_EMP_MANAGER_ID}", "{database.COL_EMP_DEVICE_USER_ID}", "{database.COL_EMP_EXCLUDE_VACATION_POLICY}"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    values = (
        emp_id, name, department_id, position, salary, vacation_days, status, phone, email,
        photo_path, gender, start_date, marital_status, education, employment_history, current_shift,
        manager_id, device_user_id, 1 if exclude_vacation_policy else 0
    )
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            logger.info(f"Employee {emp_id} ({name}) added successfully.")
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error adding employee {emp_id}: {e}")
        if "UNIQUE constraint failed: employees.device_user_id" in str(e):
            raise DatabaseOperationError(f"Device User ID '{device_user_id}' is already assigned to another employee.") # Corrected
        elif f"UNIQUE constraint failed: {database.TABLE_EMPLOYEES}.{database.COL_EMP_ID}" in str(e): # Should not happen if ID generation is correct
            raise DatabaseOperationError(f"Employee ID '{emp_id}' already exists.")
        else:
            raise DatabaseOperationError(f"Failed to add employee due to a data conflict: {e}")
    except sqlite3.Error as e:
        logger.error(f"Database error adding employee {emp_id}: {e}")
        raise DatabaseOperationError(f"Failed to add employee: {e}")

def get_employee_by_id_db(emp_id: str, include_archived: bool = False) -> Optional[Dict]:
    """Retrieves an employee by their ID."""
    archived_clause = "" if include_archived else f"AND (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)"
    # Use 'department_name' as the alias for the joined department name
    query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} as department_name, m.{database.COL_EMP_NAME} as manager_name
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        LEFT JOIN {database.TABLE_EMPLOYEES} m ON e.{database.COL_EMP_MANAGER_ID} = m.{database.COL_EMP_ID}
        WHERE e."{database.COL_EMP_ID}" = ? {archived_clause}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (emp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Interview Scheduling Backend Functions ---
def check_interviewer_availability_db(interviewer_emp_id: str, interview_date_str: str,
                                      interview_time_str: str, duration_minutes: int,
                                      exclude_interview_id: Optional[int] = None) -> List[Dict]:
    """
    Checks if an interviewer has conflicting scheduled interviews.
    Returns a list of conflicting interviews.
    """
    try:
        new_interview_start_dt = datetime.strptime(f"{interview_date_str} {interview_time_str}", "%Y-%m-%d %H:%M")
        new_interview_end_dt = new_interview_start_dt + timedelta(minutes=duration_minutes)
    except ValueError:
        raise InvalidInputError("Invalid date or time format for availability check.")

    conflicts = []
    query = f"""
        SELECT {database.COL_INT_ID}, {database.COL_INT_CANDIDATE_NAME}, {database.COL_INT_DATE}, {database.COL_INT_TIME}, {database.COL_INT_DURATION_MINUTES}
        FROM {database.TABLE_INTERVIEWS}
        WHERE {database.COL_INT_INTERVIEWER_EMP_ID} = ? 
          AND {database.COL_INT_STATUS} IN ('Scheduled', 'Rescheduled by Candidate', 'Rescheduled by Company') 
          AND {database.COL_INT_DATE} = ? 
    """
    params_query: List[Any] = [interviewer_emp_id, interview_date_str]
    if exclude_interview_id:
        query += f" AND {database.COL_INT_ID} != ?"
        params_query.append(exclude_interview_id)

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, tuple(params_query))
        
        for row in cursor.fetchall():
            existing_start_dt = datetime.strptime(f"{row[database.COL_INT_DATE]} {row[database.COL_INT_TIME]}", "%Y-%m-%d %H:%M")
            existing_end_dt = existing_start_dt + timedelta(minutes=row[database.COL_INT_DURATION_MINUTES])

            if new_interview_start_dt < existing_end_dt and new_interview_end_dt > existing_start_dt:
                conflicts.append(dict(row))
    return conflicts

def add_interview_db(candidate_name: str, interviewer_emp_id: str, interview_date_str: str,
                     interview_time_str: str, duration_minutes: int, location: Optional[str],
                     notes: Optional[str] = None, status: str = "Scheduled") -> int:
    """Adds a new interview to the database."""
    if not all([candidate_name, interviewer_emp_id, interview_date_str, interview_time_str, duration_minutes]):
        raise InvalidInputError("Candidate name, interviewer, date, time, and duration are required.")
    if not _find_employee_by_id(interviewer_emp_id):
        raise EmployeeNotFoundError(f"Interviewer employee ID '{interviewer_emp_id}' not found.")
    if status not in database.VALID_INTERVIEW_STATUSES:
        raise InvalidInputError(f"Invalid interview status: {status}")
    try:
        datetime.strptime(interview_date_str, '%Y-%m-%d'); datetime.strptime(interview_time_str, '%H:%M') # Corrected # Corrected
        if not isinstance(duration_minutes, int) or duration_minutes <= 0: raise ValueError("Duration must be positive.")
    except ValueError as ve: raise InvalidInputError(f"Invalid date, time, or duration format: {ve}")

    conflicts = check_interviewer_availability_db(interviewer_emp_id, interview_date_str, interview_time_str, duration_minutes)
    if conflicts:
        conflict_details = "\n".join([f"- {c[database.COL_INT_CANDIDATE_NAME]} at {c[database.COL_INT_TIME]}" for c in conflicts])
        raise InvalidInputError(f"Interviewer has a conflicting appointment:\n{conflict_details}")

    now_iso = datetime.now().isoformat()
    query = f"INSERT INTO {database.TABLE_INTERVIEWS} ({database.COL_INT_CANDIDATE_NAME}, {database.COL_INT_INTERVIEWER_EMP_ID}, {database.COL_INT_DATE}, {database.COL_INT_TIME}, {database.COL_INT_DURATION_MINUTES}, {database.COL_INT_LOCATION}, {database.COL_INT_STATUS}, {database.COL_INT_NOTES}, {database.COL_INT_CREATED_AT}, {database.COL_INT_UPDATED_AT}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" # Corrected
    params_insert = (candidate_name, interviewer_emp_id, interview_date_str, interview_time_str, duration_minutes, location, status, notes, now_iso, now_iso)
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor(); cursor.execute(query, params_insert); conn.commit(); interview_id = cursor.lastrowid
            logger.info(f"Interview ID {interview_id} for {candidate_name} scheduled with {interviewer_emp_id}.")
            interviewer_details = _find_employee_by_id(interviewer_emp_id)
            interviewer_name = interviewer_details.get(database.COL_EMP_NAME, interviewer_emp_id) if interviewer_details else interviewer_emp_id
            notif_msg = (f"🗓️ New Interview Scheduled!\nCandidate: *{candidate_name}*\nInterviewer: *{interviewer_name}*\nDate: {interview_date_str} at {interview_time_str}\nDuration: {duration_minutes} mins\nLocation: {location or 'N/A'}")
            from utils import telegram_notifier # Local import to break cycle
            telegram_notifier.send_telegram_notification(notif_msg) # Use telegram_notifier module
            return interview_id
    except sqlite3.Error as e: logger.error(f"DB error scheduling interview for {candidate_name}: {e}"); raise DatabaseOperationError(f"Failed to schedule interview: {e}") # Corrected
    cursor.execute(query, (emp_id,)) # This line seems misplaced
    row = cursor.fetchone() # This line seems misplaced
    return dict(row) if row else None

def get_all_employees_db(include_archived: bool = False, department_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict]:
    """Retrieves all employees, optionally filtered."""
    employees = []
    archived_clause = f"WHERE (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)" if not include_archived else "WHERE 1=1"

    params = []
    if department_filter:
        archived_clause += f" AND d.{database.COL_DEPT_NAME} = ?"
        params.append(department_filter)
    if status_filter:
        archived_clause += f" AND e.{database.COL_EMP_STATUS} = ?"
        params.append(status_filter)

    query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} as department_name, m.{database.COL_EMP_NAME} as manager_name
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        LEFT JOIN {database.TABLE_EMPLOYEES} m ON e.{database.COL_EMP_MANAGER_ID} = m.{database.COL_EMP_ID}
        {archived_clause}
        ORDER BY e.{database.COL_EMP_NAME}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        for row in cursor.fetchall():
            employees.append(dict(row))
    return employees

def get_employees_by_manager_db(manager_id: str, include_archived: bool = False) -> List[Dict]:
    """Retrieves all employees managed by a specific manager_id."""
    if not manager_id:
        return []
    
    employees = []
    archived_clause = "" if include_archived else f"AND (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)"
    
    query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} as department_name
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        WHERE e.{database.COL_EMP_MANAGER_ID} = ? {archived_clause}
        ORDER BY e.{database.COL_EMP_NAME}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (manager_id,))
        for row in cursor.fetchall():
            employees.append(dict(row))
    return employees

def get_all_employees_id_name_list(include_archived: bool = False) -> List[Tuple[str, str]]:
    """
    Retrieves a list of (employee_id, employee_name) tuples for all employees.
    Useful for populating comboboxes.
    Args:
        include_archived (bool): Whether to include archived employees.
    Returns:
        List[Tuple[str, str]]: A list of (id, name) tuples.
    """
    employees_list = []
    archived_clause = "" if include_archived else f"WHERE ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)"
    
    query = f"""
        SELECT {database.COL_EMP_ID}, {database.COL_EMP_NAME}
        FROM {database.TABLE_EMPLOYEES}
        {archived_clause}
        ORDER BY {database.COL_EMP_NAME}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        employees_list = cursor.fetchall() # Returns list of tuples
    return employees_list

def get_employee_status_counts_db() -> Dict[str, int]:
    """Counts employees by their status."""
    counts = {} # Initialize with all valid statuses to ensure they appear even if count is 0
    for status_val in database.VALID_EMPLOYEE_STATUSES:
        counts[status_val] = 0

    query = f"SELECT {database.COL_EMP_STATUS}, COUNT(*) FROM {database.TABLE_EMPLOYEES} GROUP BY {database.COL_EMP_STATUS}"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for status, count in cursor.fetchall():
                if status in counts: # Ensure we only count valid, known statuses # No change needed here, 'counts' is local
                    counts[status] = count
    except sqlite3.Error as e:
        logger.error(f"Database error fetching employee status counts: {e}")
        # Depending on desired behavior, could raise DatabaseOperationError or return empty/error dict
    return counts

def get_employee_gender_counts_db() -> Dict[str, int]:
    """Counts employees by gender. Assumes gender column exists."""
    counts = {} # Will populate with found genders
    # Query to count non-null and non-empty gender values
    query = f"SELECT {database.COL_EMP_GENDER}, COUNT(*) FROM {database.TABLE_EMPLOYEES} WHERE {database.COL_EMP_GENDER} IS NOT NULL AND {database.COL_EMP_GENDER} != '' GROUP BY {database.COL_EMP_GENDER}"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for gender, count in cursor.fetchall():
                # Capitalize gender for consistent display, handle if gender is somehow None despite query (should not happen)
                display_gender = gender.capitalize() if gender else "Unknown"
                counts[display_gender] = count
    except sqlite3.OperationalError as e:
        if "no such column" in str(e).lower() and database.COL_EMP_GENDER in str(e).lower():
            logger.warning(f"'{database.COL_EMP_GENDER}' column not found. Gender statistics will be unavailable. Consider running DB initialization/migration.")
            return {"Error": "Gender column missing"} # Return an error indicator
        raise # Re-raise other operational errors
    return counts

def get_leave_type_counts_db(period_start_str: Optional[str] = None, period_end_str: Optional[str] = None) -> Dict[str, int]:
    """Counts approved leave requests by type, optionally filtered by period."""
    counts = {}
    query = f"SELECT {database.COL_LR_LEAVE_TYPE}, COUNT(*) FROM {database.TABLE_LEAVE_REQUESTS} WHERE {database.COL_LR_STATUS} = 'Approved'"
    params = []
    if period_start_str and period_end_str:
        # Filter for leaves that overlap with the given period
        # A leave overlaps if (LeaveStart <= PeriodEnd) AND (LeaveEnd >= PeriodStart)
        query += f" AND {database.COL_LR_START_DATE} <= ? AND {database.COL_LR_END_DATE} >= ?"
        params.extend([period_end_str, period_start_str])
    
    query += f" GROUP BY {database.COL_LR_LEAVE_TYPE}"
    
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            for leave_type, count in cursor.fetchall():
                counts[leave_type if leave_type else "N/A"] = count
    except sqlite3.Error as e:
        logger.error(f"Database error fetching leave type counts: {e}")
    return counts

def get_active_contracts_count_db() -> int:
    """Counts active contracts based on their lifecycle status."""
    query = f"""
        SELECT COUNT(*) 
        FROM {database.TABLE_CONTRACTS}
        WHERE {database.COL_CONTRACT_LIFECYCLE_STATUS} = 'Active'
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchone()[0] or 0
    except sqlite3.Error as e:
        logger.error(f"Database error fetching active contracts count: {e}")
        return 0 # Return 0 on error

def search_employees_db(search_term: str, search_field: str, gender_filter: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Searches for employees based on a term and field."""
    base_query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} as department_name, m.{database.COL_EMP_NAME} as manager_name
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        LEFT JOIN {database.TABLE_EMPLOYEES} m ON e.{database.COL_EMP_MANAGER_ID} = m.{database.COL_EMP_ID}
    """
    where_clauses = []
    params: List[Any] = []

    if not include_archived:
        where_clauses.append(f"(e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)")

    if not search_field or search_field.lower() == "all":
        like_term = f"%{search_term}%"
        where_clauses.append(f"""(
            e.{database.COL_EMP_ID} LIKE ? OR 
            e.{database.COL_EMP_NAME} LIKE ? OR 
            d.{database.COL_DEPT_NAME} LIKE ? OR 
            e.{database.COL_EMP_POSITION} LIKE ? OR 
            e.{database.COL_EMP_EMAIL} LIKE ? OR 
            e.{database.COL_EMP_PHONE} LIKE ?
        )""")
        params.extend([like_term] * 6)
    elif search_field == database.COL_DEPT_NAME: # Assuming UI might pass "department_name"
        where_clauses.append(f"d.{database.COL_DEPT_NAME} LIKE ?")
        params.append(f"%{search_term}%")
    elif search_field in [database.COL_EMP_ID, database.COL_EMP_NAME, database.COL_EMP_POSITION, database.COL_EMP_EMAIL, database.COL_EMP_PHONE, database.COL_EMP_STATUS]:
        where_clauses.append(f"e.{search_field} LIKE ?")
        params.append(f"%{search_term}%")
    else:
        raise InvalidInputError(f"Invalid search field: {search_field}")

    if gender_filter: # Add gender condition if provided
        where_clauses.append(f"e.{database.COL_EMP_GENDER} = ?") # No change needed here, 'database' is correct
        params.append(gender_filter)
        
    if where_clauses:
        query = base_query + " WHERE " + " AND ".join(where_clauses)
    else: # Should not happen if include_archived is handled, but as a fallback
        query = base_query
    
    query += f" ORDER BY e.{database.COL_EMP_NAME}"

    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error searching employees: {e} (Query: {query}, Params: {params})")
        raise DatabaseOperationError(f"Failed to search employees: {e}")

def update_employee_db(emp_id: str, updates: Dict) -> None:
    """Updates employee details in the database."""
    if not updates:
        logger.warning(f"No updates provided for employee {emp_id}.")
        return

    # Ensure department_name is converted to department_id if present
    # Assuming 'department_name' might be passed if UI sends display name
    if 'department_name' in updates: 
        dept_name = updates.pop('department_name')
        if dept_name: # Only process if a department name was actually provided
            dept_id = get_department_id_by_name_db(dept_name)
            if dept_id is not None:
                updates[database.COL_EMP_DEPARTMENT_ID] = dept_id
            else:
                logger.warning(f"Department '{dept_name}' not found. Department not updated for employee {emp_id}.")
        else: # If dept_name was empty, it might mean unassigning department
            updates[database.COL_EMP_DEPARTMENT_ID] = None


    set_clause = ", ".join([f'"{col}" = ?' for col in updates.keys()])
    values = list(updates.values())
    values.append(emp_id)

    query = f'UPDATE {database.TABLE_EMPLOYEES} SET {set_clause} WHERE "{database.COL_EMP_ID}" = ?'
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No employee found with ID {emp_id} to update.")
                # raise DatabaseOperationError(f"No employee found with ID {emp_id} to update.")
            else:
                logger.info(f"Employee {emp_id} updated successfully with: {list(updates.keys())}")
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error updating employee {emp_id}: {e}")
        if "UNIQUE constraint failed: employees.device_user_id" in str(e) and database.COL_EMP_DEVICE_USER_ID in updates:
            raise DatabaseOperationError(f"Device User ID '{updates[database.COL_EMP_DEVICE_USER_ID]}' is already assigned to another employee.")
        else:
            raise database.DatabaseOperationError(f"Failed to update employee due to a data conflict: {e}")
    except sqlite3.Error as e:
        logger.error(f"Database error updating employee {emp_id}: {e}")
        raise database.DatabaseOperationError(f"Failed to update employee: {e}")

def delete_employee_db(emp_id: str) -> None:
    """Deletes an employee from the database. (Consider archiving instead of hard delete)"""
    # This is a hard delete. For production, soft delete (archiving) is often preferred.
    # The archive_employee_db function handles soft delete.
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Check if employee is a manager to prevent orphaned employees or handle reassignment
            # For simplicity, this check is omitted here but important in a real system.
            cursor.execute(f"DELETE FROM {database.TABLE_EMPLOYEES} WHERE \"{database.COL_EMP_ID}\" = ?", (emp_id,))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No employee found with ID {emp_id} to delete.")
                # raise DatabaseOperationError(f"No employee found with ID {emp_id} to delete.")
            else:
                logger.info(f"Employee {emp_id} deleted successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting employee {emp_id}: {e}")
        raise database.DatabaseOperationError(f"Failed to delete employee: {e}")

def get_total_employee_count_db(include_archived: bool = False) -> int:
    """Counts the total number of employees."""
    archived_clause = "" if include_archived else f"WHERE ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)"
    query = f"SELECT COUNT({database.COL_EMP_ID}) FROM {database.TABLE_EMPLOYEES} {archived_clause}"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0] or 0

# --- Department Queries ---
def add_department_db(name: str, description: Optional[str] = None) -> int:
    """Adds a new department and returns its ID."""
    query = f"INSERT INTO {database.TABLE_DEPARTMENTS} ({database.COL_DEPT_NAME}, {database.COL_DEPT_DESCRIPTION}) VALUES (?, ?)"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (name, description))
            conn.commit()
            logger.info(f"Department '{name}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.error(f"Department '{name}' already exists.")
        raise database.DatabaseOperationError(f"Department '{name}' already exists.")
    except sqlite3.Error as e:
        logger.error(f"Database error adding department '{name}': {e}")
        raise database.DatabaseOperationError(f"Failed to add department: {e}")

def get_all_departments_db() -> List[Dict]:
    """Retrieves all departments."""
    departments = []
    query = f"SELECT * FROM {database.TABLE_DEPARTMENTS} ORDER BY {database.COL_DEPT_NAME}"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            departments.append(dict(row))
    return departments

def get_department_by_id_db(dept_id: int) -> Optional[Dict]:
    """Retrieves a department by its ID."""
    query = f"SELECT * FROM {database.TABLE_DEPARTMENTS} WHERE {database.COL_DEPT_ID} = ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (dept_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_department_id_by_name_db(dept_name: str) -> Optional[int]:
    """Retrieves a department's ID by its name."""
    if not dept_name: return None
    query = f"SELECT {database.COL_DEPT_ID} FROM {database.TABLE_DEPARTMENTS} WHERE {database.COL_DEPT_NAME} = ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (dept_name,))
        row = cursor.fetchone()
        return row[0] if row else None

def update_department_db(dept_id: int, name: Optional[str] = None, description: Optional[str] = None) -> None:
    """Updates department details."""
    updates = {}
    if name is not None:
        updates[database.COL_DEPT_NAME] = name
    if description is not None:
        updates[database.COL_DEPT_DESCRIPTION] = description

    if not updates:
        logger.warning(f"No updates provided for department ID {dept_id}.")
        return

    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    values = list(updates.values())
    values.append(dept_id)

    query = f"UPDATE {database.TABLE_DEPARTMENTS} SET {set_clause} WHERE {database.COL_DEPT_ID} = ?"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No department found with ID {dept_id} to update.")
            else:
                logger.info(f"Department ID {dept_id} updated successfully.")
    except sqlite3.IntegrityError:
        logger.error(f"Update failed for department ID {dept_id}: Name '{name}' might already exist.")
        raise database.DatabaseOperationError(f"Department name '{name}' might already exist.")
    except sqlite3.Error as e:
        logger.error(f"Database error updating department ID {dept_id}: {e}")
        raise database.DatabaseOperationError(f"Failed to update department: {e}")

def delete_department_db(dept_id: int) -> None:
    """Deletes a department. Ensure employees are reassigned or handled."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Check if department is in use by employees
            cursor.execute(f"SELECT COUNT(*) FROM {database.TABLE_EMPLOYEES} WHERE {database.COL_EMP_DEPARTMENT_ID} = ?", (dept_id,))
            if cursor.fetchone()[0] > 0:
                raise database.DatabaseOperationError("Cannot delete department: It is currently assigned to one or more employees. Please reassign employees first.")
            
            cursor.execute(f"DELETE FROM {database.TABLE_DEPARTMENTS} WHERE {database.COL_DEPT_ID} = ?", (dept_id,))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No department found with ID {dept_id} to delete.")
            else:
                logger.info(f"Department ID {dept_id} deleted successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting department ID {dept_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete department: {e}")

def get_employee_count_for_department_db(dept_id: int) -> int:
    """Returns the number of non-archived, active employees assigned to a specific department."""
    if not dept_id: return 0
    query = f"""
        SELECT COUNT({database.COL_EMP_ID}) 
        FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_DEPARTMENT_ID} = ? 
          AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
          AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (dept_id, database.STATUS_ACTIVE, database.STATUS_ON_LEAVE)) # Count active or on leave
        count = cursor.fetchone()[0]
        return count if count else 0
# --- Attendance Helper Functions (Moved from monolithic or newly added) ---
def calculate_worked_duration(clock_in_str: Optional[str], clock_out_str: Optional[str]) -> Optional[float]:
    """Calculates worked duration in hours. Returns None if either time is missing or invalid."""
    if not clock_in_str or not clock_out_str:
        return None
    try:
        clock_in_dt = datetime.strptime(clock_in_str, '%Y-%m-%d %H:%M:%S')
        clock_out_dt = datetime.strptime(clock_out_str, '%Y-%m-%d %H:%M:%S')
        if clock_out_dt <= clock_in_dt: # Clock out must be after clock in
            logger.warning(f"Clock out time {clock_out_str} is not after clock in time {clock_in_str}. Duration calculated as 0.")
            return 0.0
        duration = clock_out_dt - clock_in_dt
        return duration.total_seconds() / 3600  # Convert to hours
    except ValueError:
        logger.error(f"Invalid datetime format for duration calculation: IN='{clock_in_str}', OUT='{clock_out_str}'")
        return None
    
# --- Helper function for public holidays ---
def is_public_holiday(check_date: dt_date) -> bool:
    """Checks if a given date is a public holiday based on app settings."""
    holidays_str = database.get_app_setting_db(database.SETTING_PUBLIC_HOLIDAYS_LIST, "")
    holidays = [h.strip() for h in holidays_str.split(',') if h.strip()]
    return check_date.isoformat() in holidays

# --- New backend function for absences today ---
def get_absences_today_count_db() -> int:
    """
    Counts active employees who are expected to work today,
    have no attendance log, and are not on approved leave.
    """
    today = dt_date.today()
    today_str = today.isoformat()
    absent_count = 0
    active_employees = [emp for emp in get_all_employees_db() if emp.get(database.COL_EMP_STATUS) == database.STATUS_ACTIVE] # Already correct
    work_day_indices = config.DEFAULT_WORK_DAYS_INDICES

    if today.weekday() not in work_day_indices or is_public_holiday(today):
        return 0 # Not an expected workday or it's a public holiday

    for emp in active_employees:
        emp_id = emp[database.COL_EMP_ID]
        # Check if employee is excluded from vacation/attendance policies if such a flag exists
        # For simplicity, assuming all active employees are expected if it's a workday.

        # Did the employee log any attendance today?
        logs_today = get_attendance_logs_for_employee_period(emp_id, today_str, today_str)
        if logs_today:
            continue # Employee was present

        # Is the employee on approved leave today?
        if is_employee_on_approved_leave(emp_id, today): # This is the call
            continue # Employee is on approved leave

        absent_count += 1
    return absent_count

# --- User Queries ---
def add_user_db(username: str, password: str, role: str, employee_id: Optional[str] = None) -> int:
    """Adds a new user."""
    hashed_password = hash_password(password)
    query = f"""INSERT INTO {database.TABLE_USERS}
                ({database.COL_USER_USERNAME}, {database.COL_USER_PASSWORD_HASH}, {database.COL_USER_ROLE}, {database.COL_USER_LINKED_EMP_ID})
                VALUES (?, ?, ?, ?)"""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (username, hashed_password, role, employee_id))
            conn.commit()
            logger.info(f"User '{username}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.error(f"Username '{username}' already exists.")
        raise database.DatabaseOperationError(f"Username '{username}' already exists.")
    except sqlite3.Error as e:
        logger.error(f"Database error adding user '{username}': {e}")
        raise database.DatabaseOperationError(f"Failed to add user: {e}")

def get_user_by_username_db(username: str) -> Optional[Dict]:
    """Retrieves a user by username."""
    query = f"SELECT * FROM {database.TABLE_USERS} WHERE {database.COL_USER_USERNAME} = ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id_db(user_id: int) -> Optional[Dict]:
    """Retrieves a user by user ID."""
    query = f"SELECT * FROM {database.TABLE_USERS} WHERE {database.COL_USER_ID} = ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def log_employee_action(employee_id: str, action_description: str, performed_by_user_id: Optional[int], 
                        existing_conn: Optional[sqlite3.Connection] = None):
    """Logs an action performed on an employee record."""
    timestamp_str = datetime.now().isoformat()
    performed_by_str = str(performed_by_user_id) if performed_by_user_id is not None else "System"

    query = f"INSERT INTO {database.TABLE_EMPLOYEE_ACTION_LOG} ({database.COL_EAL_EMP_ID}, {database.COL_EAL_ACTION_DESC}, {database.COL_EAL_TIMESTAMP}, {database.COL_EAL_PERFORMED_BY_USER_ID}) VALUES (?, ?, ?, ?)"

    params = (employee_id, action_description, performed_by_user_id, timestamp_str)

    conn_to_use = existing_conn if existing_conn else sqlite3.connect(config.DATABASE_NAME)
    try:
        cursor = conn_to_use.cursor()
        cursor.execute(query, params)
        if not existing_conn:
            conn_to_use.commit()
        logger.info(f"Action logged for employee {employee_id}: {action_description} by user ID {performed_by_user_id}")
    except sqlite3.Error as e:
        if not existing_conn and conn_to_use: conn_to_use.rollback()
        logger.error(f"Database error logging action for employee {employee_id}: {e}")
        # Depending on severity, you might want to raise an error or just log it.
        # For audit logs, it's often critical, so raising might be appropriate if not handled.
        # raise DatabaseOperationError(f"Failed to log action: {e}") 
    finally:
        if not existing_conn and conn_to_use:
            conn_to_use.close()
            
def get_all_users_db() -> List[Dict]:
    """Retrieves all users."""
    users = []
    query = f"SELECT {database.COL_USER_ID}, {database.COL_USER_USERNAME}, {database.COL_USER_ROLE}, {database.COL_USER_LINKED_EMP_ID} FROM {database.TABLE_USERS} ORDER BY {database.COL_USER_USERNAME}"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            users.append(dict(row)) # Convert to dict while connection is active
    return users

def get_employee_demographics_report() -> List[Dict[str, Any]]:
    """Generates a report with employee demographic information."""
    query = f"""
        SELECT 
            e.{database.COL_EMP_ID}, 
            e.{database.COL_EMP_NAME}, 
            e.{database.COL_EMP_GENDER}, 
            e.{database.COL_EMP_MARITAL_STATUS},
            d.{database.COL_DEPT_NAME} as department_name
        FROM {database.TABLE_EMPLOYEES} e 
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        WHERE (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)
        ORDER BY e.{database.COL_EMP_NAME};
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

def get_salary_distribution_by_department_report() -> List[Dict[str, Any]]:
    """Generates a report showing salary distribution (min, max, avg) by department."""
    query = f"""
        SELECT 
            d.{database.COL_DEPT_NAME} as department_name,
            MIN(e.{database.COL_EMP_SALARY}) as min_salary,
            MAX(e.{database.COL_EMP_SALARY}) as max_salary,
            AVG(e.{database.COL_EMP_SALARY}) as avg_salary,
            COUNT(e.{database.COL_EMP_ID}) as employee_count

        FROM {database.TABLE_EMPLOYEES} e # Use database constant
        JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID} # Use database constant
        WHERE (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL) AND e.{database.COL_EMP_STATUS} = '{database.STATUS_ACTIVE}'
        GROUP BY d.{database.COL_DEPT_NAME}
        ORDER BY d.{database.COL_DEPT_NAME};
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        # Format avg_salary to 2 decimal places
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            if row_dict.get('avg_salary') is not None:
                row_dict['avg_salary'] = round(row_dict['avg_salary'], 2)
            results.append(row_dict)
        return results

def get_terminated_employees_report(date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generates a report of terminated employees within a given date range."""
    params = []
    where_clauses = [f"e.{database.COL_EMP_STATUS} = '{database.STATUS_TERMINATED}'"]

    if date_from:
        where_clauses.append(f"e.{database.COL_EMP_TERMINATION_DATE} >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append(f"e.{database.COL_EMP_TERMINATION_DATE} <= ?")
        params.append(date_to)
    
    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT 
            e.{database.COL_EMP_ID}, 
            e.{database.COL_EMP_NAME}, 
            e.{database.COL_EMP_POSITION},
            e.{database.COL_EMP_TERMINATION_DATE}
            -- e.{db_schema.COL_EMP_TERMINATION_REASON} -- Add if you have this column
        FROM {database.TABLE_EMPLOYEES} e
        WHERE {where_sql}
        ORDER BY e.{database.COL_EMP_TERMINATION_DATE} DESC;
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

def update_user_db(user_id: int, username: Optional[str] = None, password: Optional[str] = None, role: Optional[str] = None, employee_id: Optional[str] = None, set_emp_id_null: bool = False) -> None:
    """Updates user details."""
    updates = {}
    if username is not None: updates[database.COL_USER_USERNAME] = username
    if password is not None: updates[database.COL_USER_PASSWORD_HASH] = hash_password(password)
    if role is not None: updates[database.COL_USER_ROLE] = role
    if employee_id is not None: updates[database.COL_USER_LINKED_EMP_ID] = employee_id
    if set_emp_id_null: updates[database.COL_USER_LINKED_EMP_ID] = None


    if not updates:
        logger.warning(f"No updates provided for user ID {user_id}.")
        return

    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    values = list(updates.values())
    values.append(user_id)

    query = f"UPDATE {database.TABLE_USERS} SET {set_clause} WHERE {database.COL_USER_ID} = ?"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No user found with ID {user_id} to update.")
            else:
                logger.info(f"User ID {user_id} updated successfully.")
    except sqlite3.IntegrityError:
        logger.error(f"Update failed for user ID {user_id}: Username '{username}' might already exist.")
        raise DatabaseOperationError(f"Username '{username}' might already exist.")
    except sqlite3.Error as e:
        logger.error(f"Database error updating user ID {user_id}: {e}")
        raise database.DatabaseOperationError(f"Failed to update user: {e}")

def delete_user_db(user_id: int) -> None:
    """Deletes a user."""
    query = f"DELETE FROM {database.TABLE_USERS} WHERE {database.COL_USER_ID} = ?"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No user found with ID {user_id} to delete.")
            else:
                logger.info(f"User ID {user_id} deleted successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting user ID {user_id}: {e}")
        raise database.DatabaseOperationError(f"Failed to delete user: {e}")


# --- App Settings Queries ---
def get_app_setting_db(setting_name: str) -> Optional[str]:
    """Retrieves a specific application setting."""
    query = f"SELECT {database.COL_SETTING_VALUE} FROM {database.TABLE_APP_SETTINGS} WHERE {database.COL_SETTING_KEY} = ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (setting_name,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_all_app_settings_db() -> Dict[str, str]:
    """Retrieves all application settings."""
    settings = {}
    query = f"SELECT {database.COL_SETTING_KEY}, {database.COL_SETTING_VALUE} FROM {database.TABLE_APP_SETTINGS}"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            settings[row[0]] = row[1]
    return settings

def update_app_setting_db(setting_name: str, setting_value: str) -> None:
    """Updates or adds an application setting."""
    query = f"INSERT OR REPLACE INTO {database.TABLE_APP_SETTINGS} ({database.COL_SETTING_KEY}, {database.COL_SETTING_VALUE}) VALUES (?, ?)"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (setting_name, setting_value))
            conn.commit()
            logger.info(f"App setting '{setting_name}' updated to '{setting_value}'.")
    except sqlite3.Error as e:
        logger.error(f"Database error updating app setting '{setting_name}': {e}")
        raise DatabaseOperationError(f"Failed to update app setting: {e}")

# ... (Many more _db functions will be moved here) ...

def get_attendance_logs_for_employee_period(employee_id: str, period_start_str: str, period_end_str: str) -> List[Dict]:
    """
    Fetches attendance logs for a specific employee within a given date period.
    """
    query = f"""
        SELECT *
        FROM {database.TABLE_ATTENDANCE_LOG}
        WHERE {database.COL_ATT_EMP_ID} = ? 
          AND {database.COL_ATT_LOG_DATE} BETWEEN ? AND ?
        ORDER BY {database.COL_ATT_CLOCK_IN} ASC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, period_start_str, period_end_str))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching attendance logs for {employee_id} ({period_start_str}-{period_end_str}): {e}")
        raise DatabaseOperationError(f"Failed to fetch attendance logs: {e}")

def calculate_attendance_and_overtime_for_period(
    employee_id: str,
    period_start_str: str,
    period_end_str: str,
    standard_hours_per_day: float,
    work_day_indices: List[int]
) -> Dict[str, float]:
    """
    Calculates total hours worked, regular hours, and overtime hours for an employee in a period.
    
    employee_id: str, 
    period_start_str: str, 
    period_end_str: str,
    standard_hours_per_day: float,
    work_day_indices: List[int]
) -> Dict[str, float]:
    """
    
    logs = get_attendance_logs_for_employee_period(employee_id, period_start_str, period_end_str)
    
    total_hours_worked_on_workdays = 0.0
    total_overtime_hours = 0.0
    actual_workdays_attended = set()
    daily_hours: Dict[str, float] = {} # To store hours worked per day: daily_hours['YYYY-MM-DD'] = hours

    for log_entry in logs: # Renamed log to log_entry to avoid conflict with logging module
        log_date_str = log_entry[database.COL_ATT_LOG_DATE]
        actual_workdays_attended.add(log_date_str)
        
        log_date_obj = dt_date.fromisoformat(log_date_str)
        if log_date_obj.weekday() not in work_day_indices:
            continue

        duration = calculate_worked_duration(log_entry[database.COL_ATT_CLOCK_IN], log_entry.get(database.COL_ATT_CLOCK_OUT))
        if duration is not None:
            daily_hours[log_date_str] = daily_hours.get(log_date_str, 0) + duration

    for day_str, hours_worked_on_day in daily_hours.items():
        total_hours_worked_on_workdays += hours_worked_on_day
        if hours_worked_on_day > standard_hours_per_day:
            total_overtime_hours += (hours_worked_on_day - standard_hours_per_day)
            
    total_regular_hours = total_hours_worked_on_workdays - total_overtime_hours

    return {
        "total_hours_worked_on_workdays": round(total_hours_worked_on_workdays, 2),
        "total_regular_hours": round(total_regular_hours, 2),
        "total_overtime_hours": round(total_overtime_hours, 2),
        "actual_workdays_count": len(actual_workdays_attended)
    }

def is_employee_on_approved_leave(employee_id: str, check_date: dt_date) -> bool:
    """Checks if an employee has an approved leave request covering the check_date."""
    query = f"""
        SELECT 1 FROM {database.TABLE_LEAVE_REQUESTS}
        WHERE {database.COL_LR_EMP_ID} = ?
          AND {database.COL_LR_STATUS} = 'Approved'
          AND ? BETWEEN date({database.COL_LR_START_DATE}) AND date({database.COL_LR_END_DATE}) 
        LIMIT 1 
    """ # Using date() function for SQLite date comparison
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, check_date.isoformat()))
        return cursor.fetchone() is not None
# For example:
# - Attendance queries (add_attendance_log_db, get_attendance_for_employee_db, etc.)
# - Leave queries (add_leave_request_db, get_leave_requests_db, update_leave_request_status_db, etc.)
# - Payroll queries (add_allowance_db, get_payslip_db, generate_payslip_db, etc.)
# - Document queries (add_document_db, get_documents_for_employee_db, etc.)
# - Evaluation queries
# - Contract queries
# - Task queries
# - Interview queries
# - Report generation data queries (get_department_summary_report, etc.)
# - ZKTeco related queries (get_all_device_users_db, etc.)
# - Archiving queries (archive_employee_db, etc.)
# - Backup/Restore related DB interactions (though backup logic might be higher level)

# Example of moving a report data function:
def _calculate_department_stats(dept_id: int, dept_name: str, conn: sqlite3.Connection) -> Dict:
    """Helper to calculate stats for a single department."""
    cursor = conn.cursor()
    # Employee count
    cursor.execute(f"""
        SELECT COUNT(*) FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_DEPARTMENT_ID} = ? AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
        AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
    """, (dept_id, database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
    employee_count = cursor.fetchone()[0] or 0

    # Average salary
    cursor.execute(f"""
        SELECT AVG({database.COL_EMP_SALARY}) FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_DEPARTMENT_ID} = ? AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
        AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
    """, (dept_id, database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
    avg_salary_row = cursor.fetchone()
    average_salary = round(avg_salary_row[0], 2) if avg_salary_row and avg_salary_row[0] is not None else 0.0

    # Total vacation days (for active/on leave employees)
    cursor.execute(f"""
        SELECT SUM({database.COL_EMP_VACATION_DAYS}) FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_DEPARTMENT_ID} = ? AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
        AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
    """, (dept_id, database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
    total_vacation_days_row = cursor.fetchone()
    total_vacation_days = total_vacation_days_row[0] if total_vacation_days_row and total_vacation_days_row[0] is not None else 0
    
    return {
        database.COL_DEPT_ID: dept_id,
        database.COL_EMP_DEPARTMENT: dept_name, # Using the constant for department name key
        'employee_count': employee_count,
        'average_salary': average_salary,
        'total_vacation_days': total_vacation_days
    }

def get_department_summary_report() -> List[Dict]:
    """Generates a summary report for each department."""
    summary_report = []
    departments = get_all_departments_db() # Uses the refactored function
    
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        for dept in departments:
            dept_id = dept[database.COL_DEPT_ID]
            dept_name = dept[database.COL_DEPT_NAME]
            if dept_id is not None and dept_name is not None:
                 stats = _calculate_department_stats(dept_id, dept_name, conn)
                 summary_report.append(stats)
            else:
                logger.warning(f"Skipping department with missing ID or Name in summary: {dept}")

    # Handle employees with no department_id (Unassigned)
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Count unassigned employees
            cursor.execute(f"""
                SELECT COUNT(*) FROM {database.TABLE_EMPLOYEES}
                WHERE {database.COL_EMP_DEPARTMENT_ID} IS NULL AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
                AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
            """, (database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
            unassigned_count = cursor.fetchone()[0] or 0

            if unassigned_count > 0:
                # Avg salary for unassigned
                cursor.execute(f"""
                    SELECT AVG({database.COL_EMP_SALARY}) FROM {database.TABLE_EMPLOYEES}
                    WHERE {database.COL_EMP_DEPARTMENT_ID} IS NULL AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
                    AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
                """, (database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
                avg_salary_unassigned_row = cursor.fetchone()
                avg_salary_unassigned = round(avg_salary_unassigned_row[0], 2) if avg_salary_unassigned_row and avg_salary_unassigned_row[0] is not None else 0.0
                
                # Total vacation for unassigned
                cursor.execute(f"""
                    SELECT SUM({database.COL_EMP_VACATION_DAYS}) FROM {database.TABLE_EMPLOYEES}
                    WHERE {database.COL_EMP_DEPARTMENT_ID} IS NULL AND ({database.COL_EMP_STATUS} = ? OR {database.COL_EMP_STATUS} = ?)
                    AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
                """, (database.STATUS_ACTIVE, database.STATUS_ON_LEAVE))
                total_vac_unassigned_row = cursor.fetchone()
                total_vac_unassigned = total_vac_unassigned_row[0] if total_vac_unassigned_row and total_vac_unassigned_row[0] is not None else 0

                summary_report.append({
                    database.COL_DEPT_ID: None, # Or a special ID for "Unassigned"
                    database.COL_EMP_DEPARTMENT: "Unassigned",
                    'employee_count': unassigned_count,
                    'average_salary': avg_salary_unassigned,
                    'total_vacation_days': total_vac_unassigned
                })
    except sqlite3.Error as e:
        logger.error(f"DB error calculating stats for unassigned employees: {e}")

    return summary_report

def get_salary_distribution_by_department_report_db() -> List[Dict[str, Any]]:
    """Generates a report showing salary distribution (min, max, avg) by department for active employees."""
    query = f"""
        SELECT
            d.{database.COL_DEPT_NAME} as department_name,
            MIN(e.{database.COL_EMP_SALARY}) as min_salary,
            MAX(e.{database.COL_EMP_SALARY}) as max_salary,
            AVG(e.{database.COL_EMP_SALARY}) as avg_salary,
            COUNT(e.{database.COL_EMP_ID}) as employee_count
        FROM {database.TABLE_EMPLOYEES} e
        JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        WHERE (e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL) AND e.{database.COL_EMP_STATUS} = ?
        GROUP BY d.{database.COL_DEPT_NAME}
        ORDER BY d.{database.COL_DEPT_NAME};
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (database.STATUS_ACTIVE,))
        results = [dict(row) for row in cursor.fetchall()]
        return results


def advanced_search_employees_db(criteria: Dict[str, Any], include_archived: bool = False) -> List[Dict[str, Any]]:
    """
    Performs an advanced search for employees based on multiple criteria.
    Args:
        criteria (Dict[str, Any]): A dictionary of search criteria.
        include_archived (bool): Whether to include archived employees.
    Returns:
        List[Dict[str, Any]]: A list of employee records matching the criteria.
    """
    base_query = f"""
        SELECT e.*, d.{database.COL_DEPT_NAME} as department_name, m.{database.COL_EMP_NAME} as manager_name
        FROM {database.TABLE_EMPLOYEES} e
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        LEFT JOIN {database.TABLE_EMPLOYEES} m ON e.{database.COL_EMP_MANAGER_ID} = m.{database.COL_EMP_ID}
    """
    where_clauses: List[str] = []
    params: List[Any] = []

    if not include_archived:
        where_clauses.append(f"(e.{database.COL_EMP_IS_ARCHIVED} = 0 OR e.{database.COL_EMP_IS_ARCHIVED} IS NULL)")

    # Text fields (case-insensitive LIKE) # Corrected: is_archived should be database.COL_EMP_IS_ARCHIVED
    text_field_map = {
        database.COL_EMP_NAME: f"e.{database.COL_EMP_NAME}",
        database.COL_EMP_POSITION: f"e.{database.COL_EMP_POSITION}",
        database.COL_EMP_EMAIL: f"e.{database.COL_EMP_EMAIL}",
        database.COL_EMP_PHONE: f"e.{database.COL_EMP_PHONE}",
        database.COL_EMP_MARITAL_STATUS: f"e.{database.COL_EMP_MARITAL_STATUS}",
        database.COL_EMP_EDUCATION: f"e.{database.COL_EMP_EDUCATION}"
    }
    for key, db_column_expr in text_field_map.items():
        if value := criteria.get(key, "").strip():
            where_clauses.append(f"LOWER({db_column_expr}) LIKE LOWER(?)")
            params.append(f"%{value}%")

    if dept_name_crit := criteria.get("department_name", "").strip():
        dept = get_department_by_name_db(dept_name_crit)
        if dept:
            where_clauses.append(f"e.{database.COL_EMP_DEPARTMENT_ID} = ?")
            params.append(dept[database.COL_DEPT_ID])
        else: # Department name specified but not found, so no results for this criterion
            where_clauses.append("1 = 0") 

    if gender_crit := criteria.get(database.COL_EMP_GENDER, "").strip():
        where_clauses.append(f"e.{database.COL_EMP_GENDER} = ?") # Exact match for gender
        params.append(gender_crit)

    if status_crit := criteria.get(database.COL_EMP_STATUS, "").strip():
        where_clauses.append(f"LOWER(e.{database.COL_EMP_STATUS}) = LOWER(?)")
        params.append(status_crit)

    date_range_fields = ["start_date", "termination_date"]
    for field_prefix in date_range_fields:
        db_col = getattr(database, f"COL_EMP_{field_prefix.upper()}", None) # e.g., database.COL_EMP_START_DATE
        if not db_col: continue

        if date_from := criteria.get(f"{field_prefix}_from", "").strip():
            where_clauses.append(f"e.{db_col} >= ?")
            params.append(date_from)
        if date_to := criteria.get(f"{field_prefix}_to", "").strip():
            where_clauses.append(f"e.{db_col} <= ?")
            params.append(date_to)

    salary_range_fields = ["salary_from", "salary_to"]
    for field_key in salary_range_fields:
        if salary_val_str := criteria.get(field_key, "").strip():
            try:
                salary_val = float(salary_val_str)
                operator = ">=" if "from" in field_key else "<="
                where_clauses.append(f"e.{database.COL_EMP_SALARY} {operator} ?")
                params.append(salary_val)
            except ValueError:
                logger.warning(f"Invalid salary value for {field_key}: {salary_val_str}")
                raise InvalidInputError(f"Invalid number format for {field_key.replace('_', ' ').title()}.")
    
    # The logic for handling "no criteria" is now implicitly handled by the query construction.
    # If where_clauses is empty (except for the archived filter), the query will select all based on include_archived.


    query = base_query + " WHERE " + " AND ".join(where_clauses) + f" ORDER BY e.{database.COL_EMP_NAME}"
    
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            logger.debug(f"Advanced Search Query: {query} | Params: {params}")
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"DB error during advanced search: {e}\nQuery: {query}\nParams: {params}")
        raise DatabaseOperationError(f"Failed during advanced search: {e}")

def archive_terminated_employees_db(cutoff_date_str: str) -> int:
    """
    Archives employees who were terminated on or before the cutoff_date.
    Sets their 'is_archived' flag to 1.
    Args:
        cutoff_date_str (str): The cutoff date in 'YYYY-MM-DD' format.
    Returns:
        int: The number of employees archived.
    """
    if not cutoff_date_str:
        raise InvalidInputError("Cutoff date is required for archiving.")
    try:
        # Validate date format (optional but good practice)
        dt_date.fromisoformat(cutoff_date_str)
    except ValueError:
        raise InvalidInputError(f"Invalid date format for cutoff date: '{cutoff_date_str}'. Use YYYY-MM-DD.")

    query = f"""
        UPDATE {database.TABLE_EMPLOYEES}
        SET {database.COL_EMP_IS_ARCHIVED} = 1, {database.COL_EMP_ARCHIVED_DATE} = ?
        WHERE {database.COL_EMP_STATUS} = ? 
          AND {database.COL_EMP_TERMINATION_DATE} IS NOT NULL 
          AND {database.COL_EMP_TERMINATION_DATE} <= ?
          AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (datetime.now().isoformat(), database.STATUS_TERMINATED, cutoff_date_str))
        conn.commit()
        logger.info(f"Archived {cursor.rowcount} employees terminated on or before {cutoff_date_str}.")
        return cursor.rowcount

def get_leave_balance_report_db() -> List[Dict]:
    """
    Generates a leave balance report for all active employees.
    Focuses on 'Vacation' leave type and uses allocated days from employee record.
    """
    report_data = []
    active_employees = get_all_employees_db(include_archived=False, status_filter=database.STATUS_ACTIVE)

    for emp in active_employees:
        emp_id = emp[database.COL_EMP_ID]
        emp_name = emp[database.COL_EMP_NAME]
        allocated_days = emp.get(database.COL_EMP_VACATION_DAYS, 0)
        is_excluded = emp.get(database.COL_EMP_EXCLUDE_VACATION_POLICY, 0) == 1

        days_taken = 0
        remaining_balance: Union[int, str] = 0 # Can be int or "N/A"

        if is_excluded:
            allocated_days_display = "N/A (Excluded)"
            days_taken_display = "N/A"
            remaining_balance_display = "N/A"
        else:
            allocated_days_display = allocated_days
            # Calculate days taken for 'Vacation'
            query = f"""
                SELECT {database.COL_LR_START_DATE}, {database.COL_LR_END_DATE}
                FROM {database.TABLE_LEAVE_REQUESTS}
                WHERE {database.COL_LR_EMP_ID} = ? AND {database.COL_LR_STATUS} = 'Approved' AND LOWER({database.COL_LR_LEAVE_TYPE}) = LOWER('Vacation')
            """
            with sqlite3.connect(config.DATABASE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (emp_id,))
                for row in cursor.fetchall():
                    start_date = dt_date.fromisoformat(row[0])
                    end_date = dt_date.fromisoformat(row[1])
                    days_taken += (end_date - start_date).days + 1 # Inclusive
            remaining_balance = allocated_days - days_taken
            days_taken_display = days_taken
            remaining_balance_display = remaining_balance

        report_data.append({
            database.COL_LR_EMP_ID: emp_id,
            "employee_name": emp_name,
            database.COL_LR_LEAVE_TYPE: "Annual Vacation", # Assuming this report is for general vacation
            "total_allocated": allocated_days_display,
            "days_taken": days_taken_display,
            "remaining_balance": remaining_balance_display
        })
    return report_data

# Placeholder for other DB functions that need to be moved.
# You will continue this process for all functions that interact with the database.
# Remember to adjust imports and constant references (e.g., TABLE_EMPLOYEES to database.TABLE_EMPLOYEES).
#logger_queries = logging.getLogger(__name__) # Use a logger specific to this module if preferred

def get_attendance_summary_report_db(date_from: str, date_to: str) -> List[Dict]:
    """
    Generates an attendance summary report for all active employees for a given period.
    Includes employee ID, name, total hours worked, and days present.
    """
    summary_report: List[Dict[str, Any]] = []
    # Assuming list_all_employees and STATUS_ACTIVE are available
    active_employees = [emp for emp in get_all_employees_db() if emp.get(database.COL_EMP_STATUS) == database.STATUS_ACTIVE] # Corrected function call
    
    # Fetch config values once
    # Assuming config.DEFAULT_STANDARD_WORK_HOURS_PER_DAY and config.DEFAULT_WORK_DAYS_INDICES are available
    standard_hours_per_day = config.DEFAULT_STANDARD_WORK_HOURS_PER_DAY
    work_day_indices = config.DEFAULT_WORK_DAYS_INDICES

    for emp in active_employees:
        emp_id = emp[database.COL_EMP_ID]
        emp_name = emp[database.COL_EMP_NAME]
        
        try:
            # Assuming calculate_attendance_and_overtime_for_period is available
            attendance_metrics = calculate_attendance_and_overtime_for_period(
                employee_id=emp_id,
                period_start_str=date_from,
                period_end_str=date_to,
                standard_hours_per_day=standard_hours_per_day,
                work_day_indices=work_day_indices
            )
            
            summary_report.append({
                database.COL_ATT_EMP_ID: emp_id, # Use database. directly
                "employee_name": emp_name,
                "total_hours_worked": attendance_metrics["total_hours_worked_on_workdays"],
                "days_present": attendance_metrics["actual_workdays_count"]
            })
        except Exception as e:
            logger.error(f"Error calculating attendance summary for employee {emp_id} ({emp_name}): {e}")
            summary_report.append({
                database.COL_ATT_EMP_ID: emp_id, # Use database. directly
                "employee_name": emp_name,
                "total_hours_worked": "Error",
                "days_present": "Error"
            })
            
    return summary_report
# --- Interview Scheduling Backend Functions ---
def get_interviews_db(start_date_str: Optional[str] = None, end_date_str: Optional[str] = None,
                      interviewer_emp_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """Fetches interviews, optionally filtered."""
    query = f"""
        SELECT i.*, e.{database.COL_EMP_NAME} as interviewer_name
        FROM {database.TABLE_INTERVIEWS} i
        JOIN {database.TABLE_EMPLOYEES} e ON i.{database.COL_INT_INTERVIEWER_EMP_ID} = e.{database.COL_EMP_ID}
    """
    filters = []
    params = []
    if start_date_str:
        filters.append(f"i.{database.COL_INT_DATE} >= ?")
        params.append(start_date_str)
    if end_date_str:
        filters.append(f"i.{database.COL_INT_DATE} <= ?")
        params.append(end_date_str)
    if interviewer_emp_id:
        filters.append(f"i.{database.COL_INT_INTERVIEWER_EMP_ID} = ?")
        params.append(interviewer_emp_id)
    if status:
        filters.append(f"i.{database.COL_INT_STATUS} = ?")
        params.append(status)

    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += f" ORDER BY i.{database.COL_INT_DATE} ASC, i.{database.COL_INT_TIME} ASC"

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

def get_employee_contract_type_counts_db() -> Dict[str, int]:
    """Counts active employees by their active contract type."""
    counts = {}
    query = f"""
        SELECT c.{database.COL_CONTRACT_TYPE}, COUNT(DISTINCT e.{database.COL_EMP_ID}) as employee_count
        FROM {database.TABLE_CONTRACTS} c
        JOIN {database.TABLE_EMPLOYEES} e ON c.{database.COL_CONTRACT_EMP_ID} = e.{database.COL_EMP_ID}
        WHERE e.{database.COL_EMP_STATUS} = ? 
          AND c.{database.COL_CONTRACT_LIFECYCLE_STATUS} = ?
        GROUP BY c.{database.COL_CONTRACT_TYPE}
        HAVING COUNT(DISTINCT e.{database.COL_EMP_ID}) > 0
        ORDER BY employee_count DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (database.STATUS_ACTIVE, "Active")) # Filter for active employees and active contracts
            for row in cursor.fetchall():
                counts[row[0] if row[0] else "N/A"] = row[1] # Contract type, count
    except sqlite3.Error as e:
        logger.error(f"DB error getting contract type counts: {e}")
    return counts

def get_new_employees_this_month_count_db() -> int:
    """Counts active employees whose start_date is within the current calendar month."""
    count = 0
    today = dt_date.today()
    first_day_of_month = today.replace(day=1).isoformat()
    # To get the last day of the current month:
    # Go to the first day of the next month, then subtract one day.
    if today.month == 12:
        first_day_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        first_day_of_next_month = today.replace(month=today.month + 1, day=1)
    last_day_of_month = (first_day_of_next_month - timedelta(days=1)).isoformat()

    query = f"SELECT COUNT({database.COL_EMP_ID}) FROM {database.TABLE_EMPLOYEES} WHERE {database.COL_EMP_STATUS} = ? AND {database.COL_EMP_START_DATE} BETWEEN ? AND ?"
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (database.STATUS_ACTIVE, first_day_of_month, last_day_of_month))
        count = cursor.fetchone()[0] or 0
    return count
    return [dict(row) for row in cursor.fetchall()]

# --- Employee Action Log Backend Functions ---
def get_user_by_employee_id_db(employee_id: str) -> Optional[Dict]:
    """Retrieves a user linked to a specific employee ID."""
    query = f"""
        SELECT {database.COL_USER_ID}, {database.COL_USER_USERNAME}, {database.COL_USER_ROLE}, {database.COL_USER_LINKED_EMP_ID}
        FROM {database.TABLE_USERS}
        WHERE {database.COL_USER_LINKED_EMP_ID} = ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id_db(user_id: int) -> Optional[Dict]:
    """Retrieves a user by their ID."""
    query = f"""
        SELECT {database.COL_USER_ID}, {database.COL_USER_USERNAME}, {database.COL_USER_ROLE}
        FROM {database.TABLE_USERS}
        WHERE {database.COL_USER_ID} = ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (user_id,)) # Fetch the result into the 'row' variable
        row = cursor.fetchone()
        return dict(row) if row else None # Now 'row' is defined
# --- Employee Action Log Backend Functions ---

def get_employee_action_log_db(employee_id: str) -> List[Dict]:
    """Retrieves the action log for a specific employee, joining with user table for username."""
    query = f"""
        
        SELECT eal.{database.COL_EAL_TIMESTAMP}, eal.{database.COL_EAL_ACTION_DESC}, u.{database.COL_USER_USERNAME} AS performed_by_username
        FROM {database.TABLE_EMPLOYEE_ACTION_LOG} eal
        LEFT JOIN {database.TABLE_USERS} u ON eal.{database.COL_EAL_PERFORMED_BY_USER_ID} = u.{database.COL_USER_ID}
        WHERE eal.{database.COL_EAL_EMP_ID} = ?
        ORDER BY eal.{database.COL_EAL_TIMESTAMP} DESC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row



def add_task_db(assigned_to_emp_id: str, assigned_by_user_id: int, monitor_user_id: Optional[int],
                title: str, description: Optional[str], due_date_str: Optional[str],
                priority: str = "Medium", status: str = "To Do", notes: Optional[str] = None) -> int:
    """Adds a new task to the database."""
    if not _find_employee_by_id(assigned_to_emp_id):
        raise EmployeeNotFoundError(f"Employee ID {assigned_to_emp_id} (assignee) not found.")
    if not get_user_by_id_db(assigned_by_user_id): # Assumes get_user_by_id_db exists
        raise UserNotFoundError(f"User ID {assigned_by_user_id} (assigner) not found.")
    if monitor_user_id and not get_user_by_id_db(monitor_user_id):
        raise UserNotFoundError(f"User ID {monitor_user_id} (monitor) not found.")
    if not title:
        raise InvalidInputError("Task title cannot be empty.")
    if due_date_str:
        try:
            datetime.strptime(due_date_str, '%Y-%m-%d')
        except ValueError:
            raise InvalidInputError("Invalid Due Date format. Use YYYY-MM-DD.")
    if status not in VALID_TASK_STATUSES:
        raise InvalidInputError(f"Invalid task status '{status}'. Valid statuses: {VALID_TASK_STATUSES}")
    if priority not in VALID_TASK_PRIORITIES:
        raise InvalidInputError(f"Invalid task priority '{priority}'. Valid priorities: {VALID_TASK_PRIORITIES}")

    creation_date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = f"""
        INSERT INTO {TABLE_EMPLOYEE_TASKS} (
            {COL_TASK_ASSIGNED_TO_EMP_ID}, {COL_TASK_ASSIGNED_BY_USER_ID}, {COL_TASK_MONITOR_USER_ID},
            {COL_TASK_TITLE}, {COL_TASK_DESCRIPTION}, {COL_TASK_CREATION_DATE}, {COL_TASK_DUE_DATE},
            {COL_TASK_STATUS}, {COL_TASK_PRIORITY}, {COL_TASK_NOTES}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (assigned_to_emp_id, assigned_by_user_id, monitor_user_id, title, description,
              creation_date_str, due_date_str, status, priority, notes)
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            task_id = cursor.lastrowid
            logger.info(f"Task '{title}' (ID: {task_id}) added for employee {assigned_to_emp_id}.")
            return task_id
    except sqlite3.Error as e:
        logger.error(f"Database error adding task '{title}': {e}")
        raise DatabaseOperationError(f"Failed to add task: {e}")

def get_tasks_db(assignee_emp_id: Optional[str] = None,
                 assigned_by_user_id: Optional[int] = None,
                 monitor_user_id: Optional[int] = None,
                 status: Optional[str] = None,
                 priority: Optional[str] = None) -> List[Dict]:
    """Fetches tasks based on various filter criteria."""
    base_query = f"""
        SELECT t.*, 
               e_assignee.{database.COL_EMP_NAME} as assignee_name,
               u_assigner.{database.COL_USER_USERNAME} as assigner_username,
               u_monitor.{database.COL_USER_USERNAME} as monitor_username
        FROM {database.TABLE_EMPLOYEE_TASKS} t
        JOIN {database.TABLE_EMPLOYEES} e_assignee ON t.{database.COL_TASK_ASSIGNED_TO_EMP_ID} = e_assignee.{database.COL_EMP_ID}
        JOIN {database.TABLE_USERS} u_assigner ON t.{database.COL_TASK_ASSIGNED_BY_USER_ID} = u_assigner.{database.COL_USER_ID}
        LEFT JOIN {database.TABLE_USERS} u_monitor ON t.{database.COL_TASK_MONITOR_USER_ID} = u_monitor.{database.COL_USER_ID}
    """
    where_clauses = []
    params = []

    if assignee_emp_id:
        where_clauses.append(f"t.{database.COL_TASK_ASSIGNED_TO_EMP_ID} = ?")
        params.append(assignee_emp_id)
    if assigned_by_user_id:
        where_clauses.append(f"t.{database.COL_TASK_ASSIGNED_BY_USER_ID} = ?")
        params.append(assigned_by_user_id)
    if monitor_user_id:
        where_clauses.append(f"t.{database.COL_TASK_MONITOR_USER_ID} = ?")
        params.append(monitor_user_id)
    if status and status != _("task_all_option"): # Assuming "All" is a UI option
        where_clauses.append(f"t.{database.COL_TASK_STATUS} = ?")
        params.append(status)
    if priority and priority != _("task_all_option"):
        where_clauses.append(f"t.{database.COL_TASK_PRIORITY} = ?")
        params.append(priority)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    base_query += f" ORDER BY t.{database.COL_TASK_DUE_DATE} ASC, t.{database.COL_TASK_CREATION_DATE} DESC"

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(base_query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

def update_task_db(task_id: int, updates: Dict[str, Any]) -> bool:
    """Updates an existing task. 'updates' dict contains columns to update and new values."""
    if not updates: return True # No changes

    # Validate fields before constructing query
    if COL_TASK_DUE_DATE in updates and updates[COL_TASK_DUE_DATE]:
        try: datetime.strptime(updates[COL_TASK_DUE_DATE], '%Y-%m-%d')
        except ValueError: raise InvalidInputError("Invalid Due Date format.")
    if COL_TASK_STATUS in updates and updates[COL_TASK_STATUS] not in VALID_TASK_STATUSES:
        raise InvalidInputError(f"Invalid task status '{updates[COL_TASK_STATUS]}'.")
    if COL_TASK_PRIORITY in updates and updates[COL_TASK_PRIORITY] not in VALID_TASK_PRIORITIES:
        raise InvalidInputError(f"Invalid task priority '{updates[COL_TASK_PRIORITY]}'.")
    if COL_TASK_COMPLETION_DATE in updates and updates[COL_TASK_COMPLETION_DATE]:
        try: datetime.strptime(updates[COL_TASK_COMPLETION_DATE], '%Y-%m-%d %H:%M:%S')
        except ValueError: raise InvalidInputError("Invalid Completion Date format.")

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    params = list(updates.values()) + [task_id]
    query = f"UPDATE {TABLE_EMPLOYEE_TASKS} SET {set_clause} WHERE {COL_TASK_ID} = ?"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            if cursor.rowcount == 0:
                raise HRException(f"Task ID {task_id} not found for update.")
            conn.commit()
            logger.info(f"Task ID {task_id} updated.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error updating task {task_id}: {e}")
        raise DatabaseOperationError(f"Failed to update task {task_id}: {e}")

def delete_task_db(task_id: int) -> bool:
    """Deletes a task from the database."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {TABLE_EMPLOYEE_TASKS} WHERE {COL_TASK_ID} = ?", (task_id,))
            if cursor.rowcount == 0:
                raise HRException(f"Task ID {task_id} not found for deletion.")
            conn.commit()
            logger.info(f"Task ID {task_id} deleted.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error deleting task {task_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete task {task_id}: {e}")

def get_employee_attendance_status(employee_id: str) -> Dict[str, Union[bool, Optional[str]]]:
    """
    Checks the current attendance status of an employee.

    Returns:
        A dictionary: {"is_clocked_in": True/False, "clock_in_time": "YYYY-MM-DD HH:MM:SS" or None}
    """
    if not _find_employee_by_id(employee_id): # Ensure employee exists
        raise EmployeeNotFoundError(f"Employee {employee_id} not found.")

    query = f"""
        SELECT {database.COL_ATT_CLOCK_IN}
        FROM {database.TABLE_ATTENDANCE_LOG}
        WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_CLOCK_OUT} IS NULL
        ORDER BY {database.COL_ATT_CLOCK_IN} DESC
        LIMIT 1
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        row = cursor.fetchone()
        return {"is_clocked_in": bool(row), "clock_in_time": row[0] if row else None}

def get_employee_vacation_balance_db(employee_id: str) -> int:
    """Calculates the remaining vacation balance for an employee."""
    emp = _find_employee_by_id(employee_id)
    if not emp:
        raise EmployeeNotFoundError(f"Employee {employee_id} not found.")
     # Check if employee is excluded from vacation policy
    if emp.get("exclude_vacation_policy", 0) == 1:
        logger.info(f"Employee {employee_id} is excluded from vacation policy. Balance is N/A.")
        return "N/A (Excluded)" # Indicate exclusion instead of a number
    
    total_allocated_days = emp.get(database.COL_EMP_VACATION_DAYS, 0)
    vacation_accumulation_policy = database.get_app_setting_db(database.SETTING_VACATION_ACCUMULATION_POLICY, "None") # Corrected
    
    query = f"""
        SELECT {database.COL_LR_START_DATE}, {database.COL_LR_END_DATE}
        FROM {database.TABLE_LEAVE_REQUESTS}
        WHERE {database.COL_LR_EMP_ID} = ? AND {database.COL_LR_STATUS} = 'Approved' AND LOWER({database.COL_LR_LEAVE_TYPE}) = LOWER('Vacation')
    """
    days_taken = 0
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        for row in cursor.fetchall():
            start_date = dt_date.fromisoformat(row[0])
            end_date = dt_date.fromisoformat(row[1])
            days_taken += (end_date - start_date).days + 1
    remaining_balance = total_allocated_days - days_taken

    # Apply accumulation policy if applicable (simplified)
    if vacation_accumulation_policy.lower() == "none":
        # No carry over, balance resets annually (this logic needs annual reset implementation)
        # For now, this policy doesn't change the calculation of days taken vs allocated.
        pass 
    elif vacation_accumulation_policy.lower().startswith("maxdays:"):
        try:
            max_carry_over = int(vacation_accumulation_policy.split(":")[1])
            # This logic is complex - needs to track carry-over from previous years.
            # For now, we'll just return the calculated balance.
        except (IndexError, ValueError): pass # Invalid policy format
    return remaining_balance

def _find_employee_by_id(emp_id: str) -> Optional[Dict[str, Union[str, float]]]:
    """Helper function to find an employee by their ID."""
    row_dict = None
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        # Join with departments table to get department name
        cursor.execute(f"""
            SELECT e.*, d.{database.COL_DEPT_NAME} AS "{database.COL_EMP_DEPARTMENT}"
            FROM {database.TABLE_EMPLOYEES} e
            LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
            WHERE UPPER(e.{database.COL_EMP_ID}) = UPPER(?)
        """, (emp_id.upper(),))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row) # Convert to dict while connection is active
    return row_dict

def generate_hr_alerts_report(period_start_str: str, period_end_str: str,
                              absence_threshold: int, tardy_threshold: int,
                              expected_work_days: List[int], standard_start_time_str: str) -> List[Dict]:
    """
    Generates attendance alerts for all active employees based on thresholds.
    Also includes alerts for new pending leave requests submitted within the period.

    Args:
        period_start_str: The start date of the period to check (YYYY-MM-DD).
        period_end_str: The end date of the period to check (YYYY-MM-DD).
        absence_threshold: Minimum number of potential absences to trigger an alert.
        tardy_threshold: Minimum number of tardy instances to trigger an alert.
        expected_work_days: A list of weekday indices (0=Mon, 6=Sun) considered workdays.
        standard_start_time_str: The standard work start time (HH:MM:SS).

    Returns:
        A list of dictionaries, where each dictionary represents an alert.
    """
    alerts = []
    active_employees = [emp for emp in get_all_employees_db() if emp.get(database.COL_EMP_STATUS) == database.STATUS_ACTIVE]

    try:
        period_start_date = dt_date.fromisoformat(period_start_str)
        period_end_date = dt_date.fromisoformat(period_end_str)
        standard_start_time = datetime.strptime(standard_start_time_str, '%H:%M:%S').time()
    except ValueError:
        raise InvalidInputError("Invalid date or time format for alert generation parameters.")

    for emp in active_employees:
        emp_id = emp[database.COL_EMP_ID]
        emp_name = emp[database.COL_EMP_NAME]

        # Check for absences
        potential_absences = _get_potential_absences_for_employee(emp_id, period_start_date, period_end_date, expected_work_days)
        if len(potential_absences) >= absence_threshold:
            alerts.append({
                'employee_id': emp_id, 'employee_name': emp_name,
                'alert_type': database.ALERT_TYPE_ABSENCE,
                'count': len(potential_absences),
                'details': ", ".join(potential_absences) # Comma-separated dates
            })

        # Check for tardiness
        tardy_instances = _get_tardy_instances_for_employee(emp_id, period_start_date, period_end_date, standard_start_time, expected_work_days)
        if len(tardy_instances) >= tardy_threshold:
            # Format tardy details for display (e.g., just the time or full datetime)
            tardy_details_display = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M') for ts in tardy_instances]
            alerts.append({
                'employee_id': emp_id, 'employee_name': emp_name,
                'alert_type': database.ALERT_TYPE_TARDINESS,
                'count': len(tardy_instances),
                'details': ", ".join(tardy_details_display)
            })
            
    # Check for new (pending) leave requests within the period (based on request_date)
    # This block should be outside the 'for emp in active_employees' loop
    pending_leaves = get_pending_leave_requests_db(period_start_str, period_end_str)
    for leave in pending_leaves:
        alerts.append({
            'employee_id': leave[database.COL_LR_EMP_ID],
            'employee_name': leave[database.COL_EMP_NAME], # Assuming get_pending_leave_requests_db joins and fetches name
            'alert_type': database.ALERT_TYPE_NEW_LEAVE_REQUEST,
            'count': 1, # Each pending request is one alert
            'details': f"Type: {leave[database.COL_LR_LEAVE_TYPE]}, From: {leave[database.COL_LR_START_DATE]} To: {leave[database.COL_LR_END_DATE]}, Req On: {leave[database.COL_LR_REQUEST_DATE]}"
        })

    # Sort alerts, perhaps by employee name then alert type
    alerts.sort(key=lambda x: (x['employee_name'], x['alert_type']))
    return alerts

def _get_potential_absences_for_employee(employee_id: str, period_start_date: dt_date, period_end_date: dt_date,
                                         expected_work_days: List[int]) -> List[str]:
    """
    Identifies potential absence dates for a single employee.
    An absence is a day within the expected_work_days for which no attendance log exists.
    """
    absent_dates = []
    try:
        # Get all unique dates the employee logged attendance within the period
        query = f"""
            SELECT DISTINCT {database.COL_ATT_LOG_DATE}
            FROM {database.TABLE_ATTENDANCE_LOG}
            WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_LOG_DATE} BETWEEN ? AND ?
        """
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, period_start_date.isoformat(), period_end_date.isoformat()))
            logged_dates_strs = {row[0] for row in cursor.fetchall()}

        current_date = period_start_date
        while current_date <= period_end_date:
            if current_date.weekday() in expected_work_days and not is_public_holiday(current_date): # Check if it's an expected workday AND not a public holiday
                if current_date.isoformat() not in logged_dates_strs:
                    absent_dates.append(current_date.isoformat())
            current_date += timedelta(days=1)
    except sqlite3.Error as e:
        logger.error(f"DB error checking absences for {employee_id}: {e}")
        # Decide if to raise or return empty, for batch processing, returning empty might be better
    return absent_dates

def _get_tardy_instances_for_employee(employee_id: str, period_start_date: dt_date, period_end_date: dt_date,
                                      standard_start_time: datetime.time, expected_work_days: List[int]) -> List[str]:
    """
    Identifies tardy instances for a single employee on their expected work days.
    Tardiness is clocking in after the standard_start_time on an expected_work_day.
    Returns a list of clock-in datetime strings for tardy instances.
    """
    tardy_instances = []
    try:
        query = f"""
            SELECT {database.COL_ATT_CLOCK_IN}, {database.COL_ATT_LOG_DATE}
            FROM {database.TABLE_ATTENDANCE_LOG}
            WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_LOG_DATE} BETWEEN ? AND ?
              AND {database.COL_ATT_CLOCK_IN} IS NOT NULL
        """
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, period_start_date.isoformat(), period_end_date.isoformat()))
            logs = cursor.fetchall()

        for clock_in_str, log_date_str in logs:
            log_date_obj = dt_date.fromisoformat(log_date_str) 
            if log_date_obj.weekday() in expected_work_days and not is_public_holiday(log_date_obj): # Only check tardiness on expected workdayss
                clock_in_datetime_obj = datetime.strptime(clock_in_str, '%Y-%m-%d %H:%M:%S')
                clock_in_time_obj = clock_in_datetime_obj.time()
                if clock_in_time_obj > standard_start_time:
                    tardy_instances.append(clock_in_str)
    except (sqlite3.Error, ValueError) as e: # ValueError for strptime
        logger.error(f"Error checking tardiness for {employee_id}: {e}")
    return tardy_instances

def get_pending_leave_requests_db(employee_id: Optional[str] = None, period_start_str: Optional[str] = None, period_end_str: Optional[str] = None) -> List[Dict]:
    """Fetches leave requests with 'Pending Approval' or 'Pending HR Approval' status, optionally filtered by employee_id and request_date. Includes assigned approver's username."""
    base_query = f"""
        SELECT lr.*, e.{database.COL_EMP_NAME}, u_approver.{database.COL_USER_USERNAME} as assigned_approver_username 
        FROM {database.TABLE_LEAVE_REQUESTS} lr 
        JOIN {database.TABLE_EMPLOYEES} e ON lr.{database.COL_LR_EMP_ID} = e.{database.COL_EMP_ID} 
        LEFT JOIN {database.TABLE_USERS} u_approver ON lr.{database.COL_LR_ASSIGNED_APPROVER_USER_ID} = u_approver.{database.COL_USER_ID}
    """
    
    where_clauses = [f"(lr.{database.COL_LR_STATUS} = '{database.STATUS_LEAVE_PENDING_APPROVAL}' OR lr.{database.COL_LR_STATUS} = '{database.STATUS_LEAVE_PENDING_HR_APPROVAL}')"]
    params = []

    if employee_id:
        where_clauses.append(f"lr.{database.COL_LR_EMP_ID} = ?")
        params.append(employee_id)
    
    # Filter by request_date if period is provided
    if period_start_str:
        where_clauses.append(f"lr.{database.COL_LR_REQUEST_DATE} >= ?")
        params.append(period_start_str)
    if period_end_str:
        where_clauses.append(f"lr.{database.COL_LR_REQUEST_DATE} <= ?")
        params.append(period_end_str)
    
    query = base_query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += f" ORDER BY lr.{database.COL_LR_REQUEST_DATE} DESC"
    
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error fetching pending leave requests: {e}\nQuery: {query}\nParams: {params}")
            raise database.DatabaseOperationError(f"Failed to fetch pending leave requests: {e}")

# --- New Approval Workflow Backend Functions ---
def get_pending_leave_approvals_for_user_db(approver_user_id: int) -> List[Dict]:
    """Fetches leave requests pending approval by a specific user."""
    query = f"""
        SELECT lr.*, e.{database.COL_EMP_NAME} as employee_name
        FROM {database.TABLE_LEAVE_REQUESTS} lr
        JOIN {database.TABLE_EMPLOYEES} e ON lr.{database.COL_LR_EMP_ID} = e.{database.COL_EMP_ID}
        WHERE lr.{database.COL_LR_ASSIGNED_APPROVER_USER_ID} = ? AND lr.{database.COL_LR_STATUS} = 'Pending Approval'
        ORDER BY lr.{database.COL_LR_REQUEST_DATE} ASC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (approver_user_id,))
        return [dict(row) for row in cursor.fetchall()]

# --- Dashboard 2.0 Backend Functions ---
def get_absenteeism_rate_by_department_db(period_start_str: str, period_end_str: str, work_day_indices: List[int]) -> Dict[str, float]:
    """Calculates absenteeism rate per department for a given period."""
    absenteeism_rates = {}
    departments = list_departments_db()
    period_start_date = dt_date.fromisoformat(period_start_str)
    period_end_date = dt_date.fromisoformat(period_end_str)

    for dept in departments:
        dept_id = dept[database.COL_DEPT_ID]
        dept_name = dept[database.COL_DEPT_NAME]
        active_employees_in_dept = [emp for emp in get_all_employees_db() if emp.get(COL_EMP_DEPARTMENT_ID) == dept_id and emp.get(COL_EMP_STATUS) == STATUS_ACTIVE]
        
        total_expected_workdays_dept = 0
        total_actual_attended_days_dept = 0

        if not active_employees_in_dept:
            absenteeism_rates[dept_name] = 0.0 # Or handle as N/A
            continue

        for emp in active_employees_in_dept:
            emp_id = emp[database.COL_EMP_ID]
            expected_days_emp = get_expected_workdays_in_period(period_start_date, period_end_date, work_day_indices)
            total_expected_workdays_dept += expected_days_emp
            
            # Count actual attended days (unique log_date)
            query = f"""
                SELECT COUNT(DISTINCT {database.COL_ATT_LOG_DATE})
                FROM {database.TABLE_ATTENDANCE_LOG}
                WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_LOG_DATE} BETWEEN ? AND ?
            """
            with sqlite3.connect(config.DATABASE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (emp_id, period_start_str, period_end_str))
                attended_days_emp = cursor.fetchone()[0] or 0
            total_actual_attended_days_dept += attended_days_emp
        
        if total_expected_workdays_dept > 0:
            absent_days = total_expected_workdays_dept - total_actual_attended_days_dept
            rate = (absent_days / total_expected_workdays_dept) * 100
            absenteeism_rates[dept_name] = round(rate, 2)
        else:
            absenteeism_rates[dept_name] = 0.0
    return absenteeism_rates
def get_department_attendance_adherence_db(period_start_str: str, period_end_str: str, work_day_indices: List[int]) -> Dict[str, float]:
    """Calculates attendance adherence rate per department.""" # Unindented
    adherence_rates = {}
    departments = list_departments_db()
    period_start_date = dt_date.fromisoformat(period_start_str)
    period_end_date = dt_date.fromisoformat(period_end_str)

    for dept in departments:
        dept_id = dept[database.COL_DEPT_ID]
        dept_name = dept[database.COL_DEPT_NAME]
        active_employees_in_dept = [emp for emp in get_all_employees_db() if emp.get(COL_EMP_DEPARTMENT_ID) == dept_id and emp.get(COL_EMP_STATUS) == STATUS_ACTIVE]
        
        total_expected_workdays_dept = 0
        total_actual_attended_days_dept = 0

        if not active_employees_in_dept:
            adherence_rates[dept_name] = 0.0
            continue

        for emp in active_employees_in_dept:
            emp_id = emp[database.COL_EMP_ID]
            expected_days_emp = get_expected_workdays_in_period(period_start_date, period_end_date, work_day_indices)
            total_expected_workdays_dept += expected_days_emp
            
            query = f"SELECT COUNT(DISTINCT {database.COL_ATT_LOG_DATE}) FROM {database.TABLE_ATTENDANCE_LOG} WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_LOG_DATE} BETWEEN ? AND ?"
            with sqlite3.connect(config.DATABASE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (emp_id, period_start_str, period_end_str))
                attended_days_emp = cursor.fetchone()[0] or 0
            total_actual_attended_days_dept += attended_days_emp
            
        if total_expected_workdays_dept > 0:
            rate = (total_actual_attended_days_dept / total_expected_workdays_dept) * 100
            adherence_rates[dept_name] = round(rate, 2)
        else:
            adherence_rates[dept_name] = 0.0
    return adherence_rates

def get_leave_request_status_summary_db(period_start_str: Optional[str] = None, period_end_str: Optional[str] = None) -> Dict[str, int]:
    """Gets counts of leave requests by status for a given period (based on request_date)."""
    query = f"SELECT {database.COL_LR_STATUS}, COUNT(*) FROM {database.TABLE_LEAVE_REQUESTS}"
    params = []
    if period_start_str and period_end_str:
            query += f" WHERE {database.COL_LR_REQUEST_DATE} BETWEEN ? AND ?"
    params.extend([period_start_str, period_end_str])
    query += f" GROUP BY {database.COL_LR_STATUS}"
    
    summary = {}
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            summary[row[0]] = row[1]
    return summary

def get_payslips_generated_by_department_db(period_start_str: str, period_end_str: str) -> Dict[str, int]:
    """Counts payslips generated per department for a given pay period."""
    query = f"""
        SELECT d.{database.COL_DEPT_NAME}, COUNT(p.{database.COL_PAY_ID})
        FROM {database.TABLE_PAYSLIPS} p
        JOIN {database.TABLE_EMPLOYEES} e ON p.{database.COL_PAY_EMP_ID} = e.{database.COL_EMP_ID}
        LEFT JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        WHERE p.{database.COL_PAY_PERIOD_START} = ? AND p.{database.COL_PAY_PERIOD_END} = ?
        GROUP BY d.{database.COL_DEPT_ID}, d.{database.COL_DEPT_NAME}

    """
    summary = {}
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (period_start_str, period_end_str))
        for row in cursor.fetchall():
            dept_name = row[database.COL_DEPT_NAME] if row[database.COL_DEPT_NAME] else "Unassigned"
            summary[dept_name] = row[1] # count
    return summary
# --- Employee Task Management Backend Functions ---
VALID_TASK_STATUSES = ["To Do", "In Progress", "Completed", "Blocked", "Cancelled"]
VALID_TASK_PRIORITIES = ["High", "Medium", "Low"]

# --- Payroll Backend Functions ---

def add_salary_advance_db(employee_id: str, advance_date_str: str, amount: float,
                          repayment_per_period: float, repayment_start_date_str: str) -> int:
    """Adds a new salary advance for an employee."""
    if not _find_employee_by_id(employee_id):
        raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if amount <= 0 or repayment_per_period <= 0:
        raise InvalidInputError("Advance amount and repayment per period must be positive.")
    if repayment_per_period > amount:
        raise InvalidInputError("Repayment per period cannot be greater than the total advance amount.")
    try:
        datetime.strptime(advance_date_str, '%Y-%m-%d')
        datetime.strptime(repayment_start_date_str, '%Y-%m-%d')
    except ValueError:
        raise InvalidInputError("Invalid date format. Use YYYY-MM-DD.")

    query = f"""
        INSERT INTO {database.TABLE_SALARY_ADVANCES} (
            {database.COL_ADV_EMP_ID}, {database.COL_ADV_DATE}, {database.COL_ADV_AMOUNT},
            {database.COL_ADV_REPAY_AMOUNT_PER_PERIOD}, {database.COL_ADV_REPAY_START_DATE},
            {database.COL_ADV_TOTAL_REPAID}, {database.COL_ADV_STATUS}
        ) VALUES (?, ?, ?, ?, ?, 0, 'Active')
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, advance_date_str, amount, repayment_per_period, repayment_start_date_str))
            conn.commit()
            logger.info(f"Salary advance of {amount} added for employee {employee_id}, starting repayment on {repayment_start_date_str}.")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error adding salary advance for {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to add salary advance: {e}")

def get_salary_advances_for_employee_db(employee_id: str) -> List[Dict]:
    """Fetches all salary advances for a specific employee, ordered by date."""
    if not employee_id:
        return []
    query = f"""
        SELECT *
        FROM {database.TABLE_SALARY_ADVANCES}
        WHERE {database.COL_ADV_EMP_ID} = ?
        ORDER BY {database.COL_ADV_DATE} DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (employee_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching salary advances for employee {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to fetch salary advances for employee {employee_id}: {e}")

def add_employee_reward_db(employee_id: str, reward_type: str, amount: float, effective_date_str: str) -> int:
    """Adds a non-recurring reward (allowance) for an employee."""
    if not _find_employee_by_id(employee_id):
        raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if not reward_type or amount <= 0:
        raise InvalidInputError("Reward type and a positive amount are required.")
    try:
        datetime.strptime(effective_date_str, '%Y-%m-%d')
    except ValueError:
        raise InvalidInputError("Invalid effective date format. Use YYYY-MM-DD.")

    query = f"""
        INSERT INTO {database.TABLE_EMP_ALLOWANCES}
            ({database.COL_ALLW_EMP_ID}, {database.COL_ALLW_TYPE}, {database.COL_ALLW_AMOUNT}, {database.COL_ALLW_IS_RECURRING}, {database.COL_ALLW_EFF_DATE}, {database.COL_ALLW_END_DATE})
        VALUES (?, ?, ?, 0, ?, ?)
    """ # is_recurring = 0 for non-recurring, end_date can be same as effective_date
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, reward_type, amount, effective_date_str, effective_date_str))
            conn.commit()
            logger.info(f"Reward '{reward_type}' of {amount} added for employee {employee_id} effective {effective_date_str}.")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error adding reward for {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to add reward: {e}")

def add_employee_penalty_db(employee_id: str, penalty_type: str, amount: float, effective_date_str: str) -> int:
    """Adds a non-recurring penalty (deduction) for an employee."""
    if not _find_employee_by_id(employee_id):
        raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if not penalty_type or amount <= 0:
        raise InvalidInputError("Penalty type and a positive amount are required.")
    try:
        datetime.strptime(effective_date_str, '%Y-%m-%d')
    except ValueError:
        raise InvalidInputError("Invalid effective date format. Use YYYY-MM-DD.")

    query = f"""
        INSERT INTO {database.TABLE_EMP_DEDUCTIONS}
            ({database.COL_DED_EMP_ID}, {database.COL_DED_TYPE}, {database.COL_DED_AMOUNT}, {database.COL_DED_IS_RECURRING}, {database.COL_DED_EFF_DATE}, {database.COL_DED_END_DATE})
        VALUES (?, ?, ?, 0, ?, ?)
    """ # is_recurring = 0, end_date can be same as effective_date
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, penalty_type, amount, effective_date_str, effective_date_str))
            conn.commit()
            logger.info(f"Penalty '{penalty_type}' of {amount} added for employee {employee_id} effective {effective_date_str}.")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error adding penalty for {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to add penalty: {e}")

def get_non_recurring_allowances_for_employee_db(employee_id: str) -> List[Dict]:
    """Fetches all non-recurring allowances for a specific employee, ordered by effective date."""
    if not employee_id:
        return []
    query = f"""
        SELECT {database.COL_ALLW_ID}, {database.COL_ALLW_TYPE}, {database.COL_ALLW_AMOUNT}, {database.COL_ALLW_EFF_DATE}
        FROM {database.TABLE_EMP_ALLOWANCES}
        WHERE {database.COL_ALLW_EMP_ID} = ? AND {database.COL_ALLW_IS_RECURRING} = 0
        ORDER BY {database.COL_ALLW_EFF_DATE} DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (employee_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching non-recurring allowances for employee {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to fetch non-recurring allowances for employee {employee_id}: {e}")

def get_non_recurring_deductions_for_employee_db(employee_id: str) -> List[Dict]:
    """Fetches all non-recurring deductions for a specific employee, ordered by effective date."""
    if not employee_id:
        return []
    query = f"""
        SELECT {database.COL_DED_ID}, {database.COL_DED_TYPE}, {database.COL_DED_AMOUNT}, {database.COL_DED_EFF_DATE}
        FROM {database.TABLE_EMP_DEDUCTIONS}
        WHERE {database.COL_DED_EMP_ID} = ? AND {database.COL_DED_IS_RECURRING} = 0
        ORDER BY {database.COL_DED_EFF_DATE} DESC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_active_employee_allowances_db(employee_id: str, pay_period_end_date_str: str) -> List[Dict]:
    query = f"""
        SELECT {database.COL_ALLW_TYPE}, {database.COL_ALLW_AMOUNT}
        FROM {database.TABLE_EMP_ALLOWANCES}
        WHERE {database.COL_ALLW_EMP_ID} = ?
          AND {database.COL_ALLW_IS_RECURRING} = 1
          AND {database.COL_ALLW_EFF_DATE} <= ?
          AND ({database.COL_ALLW_END_DATE} IS NULL OR {database.COL_ALLW_END_DATE} >= ?)
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, pay_period_end_date_str, pay_period_end_date_str))
        return [dict(row) for row in cursor.fetchall()]

def get_active_employee_deductions_db(employee_id: str, pay_period_end_date_str: str) -> List[Dict]:
    query = f"""
        SELECT {database.COL_DED_TYPE}, {database.COL_DED_AMOUNT}
        FROM {database.TABLE_EMP_DEDUCTIONS}
        WHERE {database.COL_DED_EMP_ID} = ?
          AND {database.COL_DED_IS_RECURRING} = 1
          AND {database.COL_DED_EFF_DATE} <= ?
          AND ({database.COL_DED_END_DATE} IS NULL OR {database.COL_DED_END_DATE} >= ?)
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, pay_period_end_date_str, pay_period_end_date_str))
        return [dict(row) for row in cursor.fetchall()]

def get_non_recurring_allowances_for_period_db(employee_id: str, period_start_str: str, period_end_str: str) -> List[Dict]:
    query = f"""
        SELECT {database.COL_ALLW_TYPE}, {database.COL_ALLW_AMOUNT}
        FROM {database.TABLE_EMP_ALLOWANCES}
        WHERE {database.COL_ALLW_EMP_ID} = ?
          AND {database.COL_ALLW_IS_RECURRING} = 0
          AND {database.COL_ALLW_EFF_DATE} BETWEEN ? AND ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, period_start_str, period_end_str))
        return [dict(row) for row in cursor.fetchall()]

def get_non_recurring_deductions_for_period_db(employee_id: str, period_start_str: str, period_end_str: str) -> List[Dict]:
    query = f"""
        SELECT {database.COL_DED_TYPE}, {database.COL_DED_AMOUNT}
        FROM {database.TABLE_EMP_DEDUCTIONS}
        WHERE {database.COL_DED_EMP_ID} = ?
          AND {database.COL_DED_IS_RECURRING} = 0
          AND {database.COL_DED_EFF_DATE} BETWEEN ? AND ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, period_start_str, period_end_str))
        return [dict(row) for row in cursor.fetchall()]

def get_active_salary_advance_for_repayment_db(employee_id: str, pay_period_end_date_str: str) -> Optional[Dict]:
    query = f"""
        SELECT *
        FROM {database.TABLE_SALARY_ADVANCES}
        WHERE {database.COL_ADV_EMP_ID} = ?
          AND {database.COL_ADV_STATUS} = 'Active'
          AND {database.COL_ADV_REPAY_START_DATE} <= ?
        ORDER BY {database.COL_ADV_DATE} ASC
        LIMIT 1
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id, pay_period_end_date_str))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_leave_request_approval_status_db(request_id: int, new_status: str, approver_comments: Optional[str], processed_by_user_id: int) -> bool:
    """
    Updates the status and approval details of a leave request.
    Args:
        request_id (int): The ID of the leave request to update.
        new_status (str): The new status (e.g., 'Approved', 'Rejected').
        approver_comments (Optional[str]): Comments from the approver.
        processed_by_user_id (int): The ID of the user processing the approval.
    Returns:
        bool: True if the update was successful, False otherwise.
    Raises:
        DatabaseOperationError: If a database error occurs.
        HRException: If the leave request is not found or not in a pending state.
    """
    processed_date_str = datetime.now().isoformat()
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # First, check if the request exists and is pending
            cursor.execute(f"SELECT {database.COL_LR_STATUS} FROM {database.TABLE_LEAVE_REQUESTS} WHERE {database.COL_LR_ID} = ?", (request_id,))
            current_status_row = cursor.fetchone()
            if not current_status_row:
                raise HRException(f"Leave request ID {request_id} not found.")
            if current_status_row[0] != 'Pending Approval':
                raise HRException(f"Leave request ID {request_id} is not in 'Pending Approval' state. Current status: {current_status_row[0]}")

            query = f"""
                UPDATE {database.TABLE_LEAVE_REQUESTS}
                SET {database.COL_LR_STATUS} = ?,
                    {database.COL_LR_APPROVER_COMMENTS} = ?,
                    {database.COL_LR_PROCESSED_BY_USER_ID} = ?,
                    {database.COL_LR_PROCESSED_DATE} = ?
                WHERE {database.COL_LR_ID} = ?
            """
            cursor.execute(query, (new_status, approver_comments, processed_by_user_id, processed_date_str, request_id))
            conn.commit()
            logger.info(f"Leave request ID {request_id} status updated to '{new_status}' by user ID {processed_by_user_id}.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error updating leave request {request_id}: {e}")
        raise DatabaseOperationError(f"Failed to update leave request {request_id}: {e}")

def get_contract_details_by_id_db(contract_id: int) -> Optional[Dict]:
    """Retrieves detailed information for a specific contract by its ID."""
    query = f"""
        SELECT c.*, e.{database.COL_EMP_NAME} as employee_name, u.{database.COL_USER_USERNAME} as assigned_approver_username
        FROM {database.TABLE_CONTRACTS} c
        JOIN {database.TABLE_EMPLOYEES} e ON c.{database.COL_CONTRACT_EMP_ID} = e.{database.COL_EMP_ID}
        LEFT JOIN {database.TABLE_USERS} u ON c.{database.COL_CONTRACT_ASSIGNED_APPROVER_USER_ID} = u.{database.COL_USER_ID}
        WHERE c.{database.COL_CONTRACT_ID} = ?
    """
    with sqlite3.connect(cosnfig.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (contract_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_contract_record_db(contract_data: Dict) -> int:
    """Adds a new contract record to the TABLE_CONTRACTS."""
    # Determine assigned approver
    assigned_approver_user_id = None
    requesting_employee_details = _find_employee_by_id(contract_data[database.COL_CONTRACT_EMP_ID])
    if requesting_employee_details and requesting_employee_details.get(database.COL_EMP_MANAGER_ID):
        manager_emp_id = requesting_employee_details[database.COL_EMP_MANAGER_ID]
        manager_user_details = get_user_by_employee_id_db(manager_emp_id)
        if manager_user_details:
            assigned_approver_user_id = manager_user_details[database.COL_USER_ID]
            logger.info(f"Contract for {contract_data[database.COL_CONTRACT_EMP_ID]} assigned to manager {manager_emp_id} (User ID: {assigned_approver_user_id}) for approval.")

    if not assigned_approver_user_id: # Fallback to default
        default_approver_id_str = database.get_app_setting_db(database.SETTING_DEFAULT_CONTRACT_APPROVER_USER_ID, "1") # New setting
        assigned_approver_user_id = int(default_approver_id_str) if default_approver_id_str and default_approver_id_str.isdigit() else 1
        logger.info(f"Contract for {contract_data[database.COL_CONTRACT_EMP_ID]} assigned to default approver (User ID: {assigned_approver_user_id}) for approval.")

    now_iso = datetime.now().isoformat()
    query = f"""
        INSERT INTO {database.TABLE_CONTRACTS} (
            {database.COL_CONTRACT_EMP_ID}, {database.COL_CONTRACT_DOC_ID}, {database.COL_CONTRACT_TYPE},
            {database.COL_CONTRACT_START_DATE}, {database.COL_CONTRACT_INITIAL_DURATION_YEARS}, {database.COL_CONTRACT_CURRENT_END_DATE},
            {database.COL_CONTRACT_IS_AUTO_RENEWABLE}, {database.COL_CONTRACT_RENEWAL_TERM_YEARS},
            {database.COL_CONTRACT_NOTICE_PERIOD_DAYS}, 
            {database.COL_CONTRACT_LIFECYCLE_STATUS}, {database.COL_CONTRACT_CUSTOM_TERMS},
            {database.COL_CONTRACT_CREATED_AT}, {database.COL_CONTRACT_UPDATED_AT},
            {database.COL_CONTRACT_APPROVAL_STATUS}, {database.COL_CONTRACT_ASSIGNED_APPROVER_USER_ID}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        contract_data[database.COL_CONTRACT_EMP_ID], contract_data.get(database.COL_CONTRACT_DOC_ID),
        contract_data[database.COL_CONTRACT_TYPE], contract_data[database.COL_CONTRACT_START_DATE],
        contract_data.get(database.COL_CONTRACT_INITIAL_DURATION_YEARS), contract_data.get(database.COL_CONTRACT_CURRENT_END_DATE), # Use .get() for optional fields
        contract_data[database.COL_CONTRACT_IS_AUTO_RENEWABLE], contract_data.get(database.COL_CONTRACT_RENEWAL_TERM_YEARS),
        contract_data.get(database.COL_CONTRACT_NOTICE_PERIOD_DAYS), 'Draft', # Initial lifecycle_status
        contract_data.get(database.COL_CONTRACT_CUSTOM_TERMS),
        now_iso, now_iso, 'Pending Approval', assigned_approver_user_id # Initial approval status
    )
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to add contract record: {e}")
        return dict(row) if row else None

def save_signature_image_to_file(image_data: bytes, employee_id: str, signer_type: str = "employee") -> str:
    """
    Saves signature image data (PNG bytes) to a file in the employee's document directory.
    Args:
        image_data (bytes): PNG image data.
        employee_id (str): The employee ID the signature is associated with.
        signer_type (str): 'employee' or 'manager'. Used for filename.
    Returns:
        str: The full path to the saved image file.
    Raises:
        IOError: If file saving fails.
    """
    emp_doc_dir = os.path.join(config.DOCUMENTS_BASE_DIR, employee_id)
    os.makedirs(emp_doc_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{employee_id}_{signer_type}_signature_{timestamp}.png"
    filepath = os.path.join(emp_doc_dir, filename)

    try:
        with open(filepath, 'wb') as f:
            f.write(image_data)
        logger.info(f"Signature image saved to: {filepath}")
        return filepath
    except IOError as e:
        logger.error(f"Failed to save signature image for {employee_id}: {e}")
        raise IOError(f"Failed to save signature image: {e}")

def record_contract_signing_db(doc_id: int, signer_emp_id: Optional[str], signer_user_id: Optional[int], signature_image_path: str, signing_notes: Optional[str] = None) -> int:
    """Records a contract signing event in the database."""
    if not doc_id or not signature_image_path:
        raise InvalidInputError("Document ID and signature image path are required to record signing.")
    if not signer_emp_id and not signer_user_id:
        raise InvalidInputError("Either signer_employee_id or signer_user_id must be provided.")

    signing_timestamp = datetime.now().isoformat()
    query = f"""
        INSERT INTO {database.TABLE_CONTRACT_SIGNATURES} (
            {database.COL_CS_DOC_ID}, {database.COL_CS_SIGNER_EMP_ID}, {database.COL_CS_SIGNER_USER_ID},
            {database.COL_CS_SIGNATURE_IMAGE_PATH}, {database.COL_CS_SIGNING_TIMESTAMP}, {database.COL_CS_SIGNING_NOTES}
        ) VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (doc_id, signer_emp_id, signer_user_id, signature_image_path, signing_timestamp, signing_notes)
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error recording contract signing for doc {doc_id}: {e}")
        raise DatabaseOperationError(f"Failed to record contract signing: {e}")

def _get_employee_open_clock_in(employee_id: str, existing_conn: Optional[sqlite3.Connection] = None) -> Optional[Dict]:
    """Helper to find the most recent open clock-in record for an employee."""
    query = f"""
        SELECT {database.COL_ATT_LOG_ID}, {database.COL_ATT_CLOCK_IN}
        FROM {database.TABLE_ATTENDANCE_LOG}
        WHERE {database.COL_ATT_EMP_ID} = ? AND {database.COL_ATT_CLOCK_OUT} IS NULL
        ORDER BY {database.COL_ATT_CLOCK_IN} DESC
        LIMIT 1
    """
    conn_to_use = existing_conn if existing_conn else sqlite3.connect(config.DATABASE_NAME)
    try:
        conn_to_use.row_factory = sqlite3.Row
        cursor = conn_to_use.cursor()
        cursor.execute(query, (employee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if not existing_conn and conn_to_use:
            conn_to_use.close()

def clock_in_employee(employee_id: str, source: str = "Manual: GUI", notes: Optional[str] = None, performed_by_user_id: Optional[int] = None):
    """Records a clock-in event for an employee."""
    employee = _find_employee_by_id(employee_id) # Uses helper within this module
    if not employee or employee.get(database.COL_EMP_STATUS) != database.STATUS_ACTIVE:
        raise EmployeeNotFoundError(f"Employee {employee_id} not found or is not active.")

    with sqlite3.connect(config.DATABASE_NAME) as conn: # Use config for DB name
        cursor = conn.cursor()
        if _get_employee_open_clock_in(employee_id, existing_conn=conn): # Pass connection
            raise AlreadyClockedInError(f"Employee {employee_id} is already clocked in.")

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today_str = datetime.now().strftime('%Y-%m-%d')

        query = f"INSERT INTO {database.TABLE_ATTENDANCE_LOG} ({database.COL_ATT_EMP_ID}, {database.COL_ATT_CLOCK_IN}, {database.COL_ATT_LOG_DATE}, {database.COL_ATT_SOURCE}, {database.COL_ATT_NOTES}) VALUES (?, ?, ?, ?, ?)"
        try:
            cursor.execute(query, (employee_id, now_str, today_str, source, notes))
            log_employee_action(employee_id, f"Clocked In ({source})", performed_by_user_id, existing_conn=conn)
            conn.commit()
            logger.info(f"Employee {employee_id} clocked in at {now_str} (Source: {source}).")
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error clocking in employee {employee_id}: {e}")
            raise DatabaseOperationError(f"Failed to clock in employee {employee_id}: {e}")

def clock_out_employee(employee_id: str, source: str = "Manual: GUI", notes: Optional[str] = None, performed_by_user_id: Optional[int] = None):
    """Records a clock-out event for an employee."""
    employee = _find_employee_by_id(employee_id) # Uses helper within this module
    if not employee or employee.get(database.COL_EMP_STATUS) != database.STATUS_ACTIVE:
        raise EmployeeNotFoundError(f"Employee {employee_id} not found or is not active.")

    with sqlite3.connect(config.DATABASE_NAME) as conn: # Use config for DB name
        cursor = conn.cursor()
        open_log = _get_employee_open_clock_in(employee_id, existing_conn=conn) # Pass connection
        if not open_log:
            raise NotClockedInError(f"Employee {employee_id} is not currently clocked in.") # Already correct, ensure import is present

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        clock_in_dt = datetime.strptime(open_log[database.COL_ATT_CLOCK_IN], '%Y-%m-%d %H:%M:%S')
        clock_out_dt = datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')
        if clock_out_dt <= clock_in_dt:
             raise InvalidInputError(f"Clock-out time ({now_str}) cannot be before or same as clock-in time ({open_log[database.COL_ATT_CLOCK_IN]}).")

        query = f"UPDATE {database.TABLE_ATTENDANCE_LOG} SET {database.COL_ATT_CLOCK_OUT} = ?, {database.COL_ATT_NOTES} = ? WHERE {database.COL_ATT_LOG_ID} = ?"
        try:
            cursor.execute(query, (now_str, notes, open_log[database.COL_ATT_LOG_ID]))
            log_employee_action(employee_id, f"Clocked Out ({source})", performed_by_user_id, existing_conn=conn)
            conn.commit()
            logger.info(f"Employee {employee_id} clocked out at {now_str} (Source: {source}).")
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error clocking out employee {employee_id}: {e}")
            raise DatabaseOperationError(f"Failed to clock out employee {employee_id}: {e}")

def get_expected_workdays_in_period(period_start_date: dt_date, period_end_date: dt_date, work_day_indices: List[int]) -> int:
    count = 0
    current_date = period_start_date
    while current_date <= period_end_date:
        if current_date.weekday() in work_day_indices and not is_public_holiday(current_date): # Added public holiday check
            count += 1
        current_date += timedelta(days=1)
    return count

def calculate_payroll_for_employee(employee_id: str, pay_period_start_str: str, pay_period_end_str: str) -> Dict:
    employee = _find_employee_by_id(employee_id)
    if not employee:
        raise EmployeeNotFoundError(f"Employee {employee_id} not found for payroll calculation.")
    if employee.get(COL_EMP_STATUS) != database.STATUS_ACTIVE:
        raise InvalidInputError(f"Employee {employee_id} is not 'Active'. Payroll cannot be calculated.")

    default_deduction_rate = float(database.get_app_setting_db(database.SETTING_DEFAULT_DEDUCTION_RATE, "0.0"))
    default_bonus_rate = float(database.get_app_setting_db(database.SETTING_DEFAULT_BONUS_RATE, "0.0"))
    monthly_salary = employee.get(COL_EMP_SALARY, 0.0)
    calculated_basic_salary = monthly_salary
    overtime_pay = 0.0

    try:
        period_start_obj = dt_date.fromisoformat(pay_period_start_str)
        period_end_obj = dt_date.fromisoformat(pay_period_end_str)
    except ValueError:
        raise InvalidInputError("Invalid pay period date format for payroll calculation.")

    expected_workdays_in_pay_period = get_expected_workdays_in_period(period_start_obj, period_end_obj, config.DEFAULT_WORK_DAYS_INDICES)

    attendance_summary = calculate_attendance_and_overtime_for_period(
        employee_id, pay_period_start_str, pay_period_end_str,
        config.DEFAULT_STANDARD_WORK_HOURS_PER_DAY, config.DEFAULT_WORK_DAYS_INDICES
    )
    actual_days_worked = attendance_summary["actual_workdays_count"]

    if attendance_summary["total_overtime_hours"] > 0 and expected_workdays_in_pay_period > 0:
        approx_daily_rate = monthly_salary / expected_workdays_in_pay_period
        approx_hourly_rate = approx_daily_rate / config.DEFAULT_STANDARD_WORK_HOURS_PER_DAY
        overtime_pay = attendance_summary["total_overtime_hours"] * approx_hourly_rate * config.OVERTIME_RATE_MULTIPLIER
        overtime_pay = round(overtime_pay, 2)

    recurring_allowances = get_active_employee_allowances_db(employee_id, pay_period_end_str)
    non_recurring_allowances = get_non_recurring_allowances_for_period_db(employee_id, pay_period_start_str, pay_period_end_str)
    all_allowances_detail = recurring_allowances + non_recurring_allowances
    total_allowances_amount = sum(a[database.COL_ALLW_AMOUNT] for a in all_allowances_detail)
    if default_bonus_rate > 0:
        default_bonus_amount = monthly_salary * default_bonus_rate
        all_allowances_detail.append({"allowance_type": "Default Bonus", "amount": default_bonus_amount}) # This line was missing
        total_allowances_amount += default_bonus_amount # Add to total

    gross_salary = calculated_basic_salary + overtime_pay + total_allowances_amount

    recurring_deductions = get_active_employee_deductions_db(employee_id, pay_period_end_str)
    non_recurring_deductions = get_non_recurring_deductions_for_period_db(employee_id, pay_period_start_str, pay_period_end_str)
    all_deductions_detail = recurring_deductions + non_recurring_deductions
    total_regular_deductions_amount = sum(d[database.COL_DED_AMOUNT] for d in all_deductions_detail)

    advance_repayment_this_period = 0.0
    active_advance = get_active_salary_advance_for_repayment_db(employee_id, pay_period_end_str)
    advance_details_for_payslip = {}

    if active_advance:
        remaining_advance_balance = active_advance[database.COL_ADV_AMOUNT] - active_advance[database.COL_ADV_TOTAL_REPAID]
        repayment_due_this_period = active_advance[database.COL_ADV_REPAY_AMOUNT_PER_PERIOD]
        advance_repayment_this_period = min(repayment_due_this_period, remaining_advance_balance)
        advance_repayment_this_period = max(0, advance_repayment_this_period)
        advance_details_for_payslip = {
            'advance_id': active_advance[database.COL_ADV_ID],
            'amount_deducted': advance_repayment_this_period,
            'new_total_repaid': active_advance[database.COL_ADV_TOTAL_REPAID] + advance_repayment_this_period,
            'original_advance_amount': active_advance[database.COL_ADV_AMOUNT]
        }

    total_deductions_combined = total_regular_deductions_amount + advance_repayment_this_period
    net_pay = gross_salary - total_deductions_combined

    return {
        database.COL_PAY_EMP_ID: employee_id,
        database.COL_PAY_PERIOD_START: pay_period_start_str,
        database.COL_PAY_PERIOD_END: pay_period_end_str,
        "monthly_reference_salary": monthly_salary,
        database.COL_PAY_BASIC_SALARY: round(calculated_basic_salary,2),
        "overtime_hours": attendance_summary["total_overtime_hours"],
        "overtime_pay": overtime_pay,
        "recurring_allowances_detail": recurring_allowances,
        "non_recurring_allowances_detail": non_recurring_allowances,
        database.COL_PAY_TOTAL_ALLOWANCES: round(total_allowances_amount, 2),
        database.COL_PAY_GROSS_SALARY: round(gross_salary,2),
        "recurring_deductions_detail": recurring_deductions,
        "non_recurring_deductions_detail": non_recurring_deductions,
        database.COL_PAY_TOTAL_DEDUCTIONS: round(total_regular_deductions_amount, 2),
        database.COL_PAY_ADVANCE_REPAYMENT: round(advance_repayment_this_period, 2),
        "advance_calculation_details": advance_details_for_payslip,
        database.COL_PAY_NET_PAY: round(net_pay,2),
        "actual_days_worked_in_period": actual_days_worked,
        "expected_workdays_in_period": expected_workdays_in_pay_period,
        database.COL_PAY_GENERATION_DATE: dt_date.today().isoformat()
    }

def record_payslip_db(payslip_data: Dict, existing_conn: Optional[sqlite3.Connection] = None) -> int:
    cols = [
        database.COL_PAY_EMP_ID, database.COL_PAY_PERIOD_START, database.COL_PAY_PERIOD_END,
        database.COL_PAY_BASIC_SALARY, database.COL_PAY_TOTAL_ALLOWANCES, database.COL_PAY_GROSS_SALARY,
        database.COL_PAY_TOTAL_DEDUCTIONS, database.COL_PAY_ADVANCE_REPAYMENT, database.COL_PAY_NET_PAY,
        database.COL_PAY_GENERATION_DATE, database.COL_PAY_NOTES
    ]
    values = [
        payslip_data[database.COL_PAY_EMP_ID], payslip_data[database.COL_PAY_PERIOD_START], payslip_data[database.COL_PAY_PERIOD_END],
        payslip_data[database.COL_PAY_BASIC_SALARY], payslip_data[database.COL_PAY_TOTAL_ALLOWANCES], payslip_data[database.COL_PAY_GROSS_SALARY],
        payslip_data[database.COL_PAY_TOTAL_DEDUCTIONS], payslip_data[database.COL_PAY_ADVANCE_REPAYMENT], payslip_data[database.COL_PAY_NET_PAY],
        payslip_data[database.COL_PAY_GENERATION_DATE], payslip_data.get(database.COL_PAY_NOTES)
    ]

    def _perform_operations(cursor):
        cursor.execute(f"INSERT INTO {database.TABLE_PAYSLIPS} ({', '.join(cols)}) VALUES ({', '.join(['?']*len(cols))})", tuple(values))
        payslip_id = cursor.lastrowid
        advance_calc_details = payslip_data.get("advance_calculation_details", {})
        if advance_calc_details and advance_calc_details.get('advance_id') and advance_calc_details.get('amount_deducted', 0) > 0:
            adv_id = advance_calc_details['advance_id']
            new_total_repaid = advance_calc_details['new_total_repaid']
            original_adv_amount = advance_calc_details['original_advance_amount']
            new_status = 'Active'
            if new_total_repaid >= original_adv_amount:
                new_status = 'Fully Repaid'
            cursor.execute(f"""
                UPDATE {database.TABLE_SALARY_ADVANCES}
                SET {database.COL_ADV_TOTAL_REPAID} = ?, {database.COL_ADV_STATUS} = ?
                WHERE {database.COL_ADV_ID} = ?
            """, (new_total_repaid, new_status, adv_id))
        return payslip_id

    conn_to_use = existing_conn if existing_conn else sqlite3.connect(config.DATABASE_NAME)
    try:
        cursor = conn_to_use.cursor()
        payslip_id = _perform_operations(cursor)
        if not existing_conn:
            conn_to_use.commit()
        logger.info(f"Payslip ID {payslip_id} recorded for employee {payslip_data[database.COL_PAY_EMP_ID]}.")
        return payslip_id
    except sqlite3.IntegrityError as e:
        if not existing_conn: conn_to_use.rollback()
        logger.error(f"Payslip already exists for employee {payslip_data[database.COL_PAY_EMP_ID]} for period {payslip_data[database.COL_PAY_PERIOD_START]}-{payslip_data[database.COL_PAY_PERIOD_END]}. Error: {e}")
        raise DatabaseOperationError(f"Payslip for this period already exists for the employee.")
    except sqlite3.Error as e:
        if not existing_conn: conn_to_use.rollback()
        logger.error(f"Database error recording payslip: {e}")
        raise DatabaseOperationError(f"Failed to record payslip: {e}")
    finally:
        if not existing_conn and conn_to_use:
            conn_to_use.close()

def get_average_performance_by_department_db(period_start_str: str, period_end_str: str) -> Dict[str, float]:
    """Calculates the average performance score by department for active employees within a period."""
    avg_scores = {}
    query = f"""
        SELECT d.{database.COL_DEPT_NAME}, AVG(ev.{database.COL_EVAL_TOTAL_SCORE}) as avg_score
        FROM {database.TABLE_EMPLOYEE_EVALUATIONS} ev
        JOIN {database.TABLE_EMPLOYEES} e ON ev.{database.COL_EVAL_EMP_ID} = e.{database.COL_EMP_ID}
        JOIN {database.TABLE_DEPARTMENTS} d ON e.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
        WHERE e.{database.COL_EMP_STATUS} = ? 
          AND ev.{database.COL_EVAL_DATE} BETWEEN ? AND ?
        GROUP BY d.{database.COL_DEPT_ID}, d.{database.COL_DEPT_NAME}
        ORDER BY avg_score DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (database.STATUS_ACTIVE, period_start_str, period_end_str))
            for row in cursor.fetchall():
                dept_name = row[database.COL_DEPT_NAME] if row[database.COL_DEPT_NAME] else "Unassigned"
                avg_scores[dept_name] = round(row['avg_score'], 2) if row['avg_score'] is not None else 0.0
    except sqlite3.Error as e: # pragma: no cover
        logger.error(f"DB error getting average performance by department: {e}")
    return avg_scores

def get_overall_average_performance_score_db(period_start_str: str, period_end_str: str) -> Optional[float]:
    """Calculates the overall average performance score for active employees within a period."""
    query = f"""
        SELECT AVG(ev.{database.COL_EVAL_TOTAL_SCORE}) as overall_avg_score
        FROM {database.TABLE_EMPLOYEE_EVALUATIONS} ev
        JOIN {database.TABLE_EMPLOYEES} e ON ev.{database.COL_EVAL_EMP_ID} = e.{database.COL_EMP_ID}
        WHERE e.{database.COL_EMP_STATUS} = ? 
          AND ev.{database.COL_EVAL_DATE} BETWEEN ? AND ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (database.STATUS_ACTIVE, period_start_str, period_end_str))
        result = cursor.fetchone()
        return round(result[0], 2) if result and result[0] is not None else None
    
def get_average_performance_by_employee_db(period_start_str: Optional[str] = None, period_end_str: Optional[str] = None) -> List[Dict]:
    """
    Calculates the average performance score for each active employee.
    Optionally filters evaluations by a given period.
    """
    params: List[Any] = [database.STATUS_ACTIVE]
    period_filter_sql = ""

    if period_start_str and period_end_str:
        period_filter_sql = f"AND ev.{database.COL_EVAL_DATE} BETWEEN ? AND ?"
        params.extend([period_start_str, period_end_str])

    query = f"""
        SELECT
            e.{database.COL_EMP_ID} AS employee_id,
            e.{database.COL_EMP_NAME} AS employee_name,
            AVG(ev.{database.COL_EVAL_TOTAL_SCORE}) AS average_score,
            COUNT(ev.{database.COL_EVAL_ID}) AS evaluation_count
        FROM {database.TABLE_EMPLOYEES} e
        JOIN {database.TABLE_EMPLOYEE_EVALUATIONS} ev ON e.{database.COL_EMP_ID} = ev.{database.COL_EVAL_EMP_ID}
        WHERE e.{database.COL_EMP_STATUS} = ?
          {period_filter_sql}
        GROUP BY e.{database.COL_EMP_ID}, e.{database.COL_EMP_NAME}
        ORDER BY average_score DESC, e.{database.COL_EMP_NAME} ASC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        results = [dict(row) for row in cursor.fetchall()]
        return results

def get_salary_distribution_report(num_bins: int = 5) -> str:
    """
    Generates data for a salary distribution report and potentially saves a plot.
    This is a placeholder and needs to be implemented.
    Args:
        num_bins (int): The number of bins for the salary histogram.
    Returns:
        str: A message indicating the status or path to a generated plot.
    """
    logger.info(f"Generating salary distribution report with {num_bins} bins.")
    # Placeholder logic:
    # 1. Fetch all active employee salaries from the database.
    #    Example: salaries = [emp[database.COL_EMP_SALARY] for emp in get_all_employees_db() if emp.get(database.COL_EMP_STATUS) == database.STATUS_ACTIVE and emp.get(database.COL_EMP_SALARY) is not None]
    # 2. Use a library like matplotlib or seaborn to generate a histogram plot.
    #    - import matplotlib.pyplot as plt
    #    - plt.hist(salaries, bins=num_bins)
    #    - plt.title('Salary Distribution')
    #    - plt.xlabel('Salary')
    #    - plt.ylabel('Number of Employees')
    #    - plot_path = os.path.join(config.REPORTS_DIR, "salary_distribution.png") # Define REPORTS_DIR in config
    #    - plt.savefig(plot_path)
    #    - plt.close()
    #    - return plot_path
    return f"Salary distribution plot generation not yet fully implemented. Bins: {num_bins}"

def get_department_statistics_report(start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> List[Dict[str, Union[str, int, float]]]:
    """
    Generates a statistics report for each department.
    Includes: Department Name, Number of Active Employees, Total Logged Person-Days by Active Employees.
    If start_date and end_date are provided, person-days are counted within that period.
    A "person-day" is one employee logging attendance on one day.
    """
    query_params = []
    date_filter_sql = ""
    if start_date_str:
        date_filter_sql += f" AND al.{database.COL_ATT_LOG_DATE} >= ?"
        query_params.append(start_date_str)
    if end_date_str:
        date_filter_sql += f" AND al.{database.COL_ATT_LOG_DATE} <= ?"
        query_params.append(end_date_str)

    final_query = f"""
        SELECT
            d.{database.COL_DEPT_NAME} AS department_name,
            (SELECT COUNT(*)
             FROM {database.TABLE_EMPLOYEES} e_active
             WHERE e_active.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID} AND e_active.{database.COL_EMP_STATUS} = '{database.STATUS_ACTIVE}'
            ) as headcount,
            (SELECT COUNT(DISTINCT al.{database.COL_ATT_EMP_ID} || '-' || al.{database.COL_ATT_LOG_DATE}) -- Count unique employee-day pairs
             FROM {database.TABLE_ATTENDANCE_LOG} al
             JOIN {database.TABLE_EMPLOYEES} e_inner ON al.{database.COL_ATT_EMP_ID} = e_inner.{database.COL_EMP_ID}
             WHERE e_inner.{database.COL_EMP_DEPARTMENT_ID} = d.{database.COL_DEPT_ID}
               AND e_inner.{database.COL_EMP_STATUS} = '{database.STATUS_ACTIVE}'
               {date_filter_sql}
            ) as total_person_days
        FROM {database.TABLE_DEPARTMENTS} d
        ORDER BY d.{database.COL_DEPT_NAME};
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(final_query, tuple(query_params))
        return [dict(row) for row in cursor.fetchall()]

def get_employee_documents_db(employee_id: str) -> List[Dict]:
    """Retrieves all documents for a specific employee."""
    # Optional: Check if employee exists. For now, assume valid ID if called from profile.
    # if not _find_employee_by_id(employee_id):
    #     logger.warning(f"Attempted to get documents for non-existent employee ID: {employee_id}")
    #     raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")

    query = f"""
        SELECT {database.COL_DOC_ID}, {database.COL_DOC_TYPE}, {database.COL_DOC_FILE_PATH}, {database.COL_DOC_UPLOAD_DATE}
        FROM {database.TABLE_EMPLOYEE_DOCUMENTS}
        WHERE {database.COL_DOC_EMP_ID} = ?
        ORDER BY {database.COL_DOC_UPLOAD_DATE} DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (employee_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching documents for employee {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to fetch documents for employee {employee_id}: {e}")

def get_average_employee_tenure_db() -> Optional[float]:
    """Calculates the average tenure (in days) of currently active employees."""
    query = f"""
        SELECT {database.COL_EMP_START_DATE}
        FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_STATUS} = ? 
          AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL) 
          AND {database.COL_EMP_START_DATE} IS NOT NULL
    """
    tenures_in_days = []
    today = dt_date.today()
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (database.STATUS_ACTIVE,))
        for row in cursor.fetchall():
            try:
                start_date = dt_date.fromisoformat(row[0])
                tenures_in_days.append((today - start_date).days)
            except (ValueError, TypeError):
                logger.warning(f"Invalid start_date format encountered for tenure calculation: {row[0]}")
    if not tenures_in_days:
        return None
    return sum(tenures_in_days) / len(tenures_in_days)

def get_terminations_in_period_db(start_date_str: str, end_date_str: str) -> int:
    """Counts employees terminated within a given period."""
    query = f"""
        SELECT COUNT(*) FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_STATUS} = ? 
          AND {database.COL_EMP_TERMINATION_DATE} BETWEEN ? AND ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (database.STATUS_TERMINATED, start_date_str, end_date_str))
        return cursor.fetchone()[0] or 0

def get_new_hires_in_period_db(start_date_str: str, end_date_str: str) -> int:
    """Counts new employees hired within a given period."""
    query = f"""
        SELECT COUNT(*) FROM {database.TABLE_EMPLOYEES}
        WHERE {database.COL_EMP_START_DATE} BETWEEN ? AND ?
    """ # Assumes new hires are immediately active or status is handled elsewhere.
      # If only 'Active' new hires, add: AND {database.COL_EMP_STATUS} = '{database.STATUS_ACTIVE}'
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (start_date_str, end_date_str))
        return cursor.fetchone()[0] or 0

def get_all_app_counters_db() -> List[Dict[str, Any]]:
    """Retrieves all application counters from the app_counters table."""
    query = f"SELECT {database.COL_COUNTER_NAME}, {database.COL_COUNTER_VALUE} FROM {database.TABLE_APP_COUNTERS}"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching app counters: {e}")
        return []

def get_pending_contract_approvals_for_user_db(approver_user_id: int) -> List[Dict]:
    """Fetches contracts pending approval by a specific user."""
    query = f"""
        SELECT c.*, e.{database.COL_EMP_NAME} as employee_name,
               u_creator.{database.COL_USER_USERNAME} as creator_username 
        FROM {database.TABLE_CONTRACTS} c
        JOIN {database.TABLE_EMPLOYEES} e ON c.{database.COL_CONTRACT_EMP_ID} = e.{database.COL_EMP_ID}
        LEFT JOIN {database.TABLE_USERS} u_creator ON c.{database.COL_CONTRACT_EMP_ID} = u_creator.{database.COL_USER_LINKED_EMP_ID} -- Assuming creator is linked to employee
        WHERE c.{database.COL_CONTRACT_ASSIGNED_APPROVER_USER_ID} = ? 
          AND c.{database.COL_CONTRACT_APPROVAL_STATUS} = 'Pending Approval'
        ORDER BY c.{database.COL_CONTRACT_CREATED_AT} ASC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (approver_user_id,))
        return [dict(row) for row in cursor.fetchall()]

# Also, ensure add_employee_document_db and delete_employee_document_db are in queries.py
# if they are called by main_gui.py

def add_employee_document_db(employee_id: str, doc_type: str, source_file_path: str) -> int:
    """Adds a document for an employee. Copies the file to a managed directory."""
    if not _find_employee_by_id(employee_id): # Call directly within the same module
        raise database.EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Source document file not found: {source_file_path}")

    emp_doc_dir = os.path.join(config.DOCUMENTS_BASE_DIR, employee_id)
    os.makedirs(emp_doc_dir, exist_ok=True)

    filename = os.path.basename(source_file_path)
    destination_file_path = os.path.join(emp_doc_dir, filename)
    counter = 1
    base, ext = os.path.splitext(filename)
    while os.path.exists(destination_file_path):
        destination_file_path = os.path.join(emp_doc_dir, f"{base}_{counter}{ext}")
        counter += 1
    
    import shutil # Make sure shutil is imported in queries.py
    shutil.copy2(source_file_path, destination_file_path)

    upload_date_str = dt_date.today().isoformat() # Ensure dt_date is imported
    query = f"INSERT INTO {database.TABLE_EMPLOYEE_DOCUMENTS} ({database.COL_DOC_EMP_ID}, {database.COL_DOC_TYPE}, {database.COL_DOC_FILE_PATH}, {database.COL_DOC_UPLOAD_DATE}) VALUES (?, ?, ?, ?)"
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, doc_type, destination_file_path, upload_date_str))
            conn.commit()
            logger.info(f"Document '{doc_type}' ({filename}) added for employee {employee_id}. Stored at: {destination_file_path}")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error adding document for {employee_id}: {e}")
        if os.path.exists(destination_file_path):
            os.remove(destination_file_path)
        raise database.DatabaseOperationError(f"Failed to add document record: {e}")

def delete_employee_document_db(doc_id: int) -> bool:
    """Deletes a document record from DB and its associated file from storage."""
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT {database.COL_DOC_FILE_PATH} FROM {database.TABLE_EMPLOYEE_DOCUMENTS} WHERE {database.COL_DOC_ID} = ?", (doc_id,))
        row = cursor.fetchone()
        if not row:
            raise FileNotFoundError(f"Document with ID {doc_id} not found in database for deletion.")
        file_to_delete = row[database.COL_DOC_FILE_PATH]
        cursor.execute(f"DELETE FROM {database.TABLE_EMPLOYEE_DOCUMENTS} WHERE {database.COL_DOC_ID} = ?", (doc_id,))
        conn.commit()
        if os.path.exists(file_to_delete): os.remove(file_to_delete) # Ensure os is imported
        logger.info(f"Document ID {doc_id} (path: {file_to_delete}) deleted.")
    return True

def get_employee_action_log_db(employee_id: str) -> List[Dict]:
    """Retrieves the action log for a specific employee, joining with user table for username."""
    query = f"""
        SELECT eal.{database.COL_EAL_TIMESTAMP}, eal.{database.COL_EAL_ACTION_DESC}, u.{database.COL_USER_USERNAME} AS performed_by_username
        FROM {database.TABLE_EMPLOYEE_ACTION_LOG} eal
        LEFT JOIN {database.TABLE_USERS} u ON eal.{database.COL_EAL_PERFORMED_BY_USER_ID} = u.{database.COL_USER_ID}
        WHERE eal.{database.COL_EAL_EMP_ID} = ?
        ORDER BY eal.{database.COL_EAL_TIMESTAMP} DESC
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (employee_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching action log for employee {employee_id}: {e}")
        return [] # Return empty list on error
    
# --- ZKTeco Device Communication (Conceptual) ---

def list_all_users_db() -> List[Dict]:
    """Lists all users from the database."""
    try:
        # Include linked employee ID and name
        query = f""" 
            SELECT u.{database.COL_USER_ID}, u.{database.COL_USER_USERNAME}, u.{database.COL_USER_ROLE}, u.{database.COL_USER_LINKED_EMP_ID}, e.{database.COL_EMP_NAME} as linked_employee_name
            FROM {database.TABLE_USERS} u
            LEFT JOIN {database.TABLE_EMPLOYEES} e ON u.{database.COL_USER_LINKED_EMP_ID} = e.{database.COL_EMP_ID}
            ORDER BY u.{database.COL_USER_USERNAME}
        """
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error listing users: {e}")
        raise DatabaseOperationError(f"Failed to list users: {e}")
    
# ... (MANY OTHER DATABASE FUNCTIONS) ...

def add_leave_request_db(employee_id: str, leave_type: str, start_date_str: str, end_date_str: str,
                         reason: Optional[str] = None) -> int:
    """Adds a new leave request to the database with 'Pending' status."""
    if not _find_employee_by_id(employee_id): # This calls _find_employee_by_id
        raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if not all([leave_type, start_date_str, end_date_str]):
        raise InvalidInputError("Leave type, start date, and end date are required.")
    try:
        start_date_obj = dt_date.fromisoformat(start_date_str)
        end_date_obj = dt_date.fromisoformat(end_date_str)
        if start_date_obj > end_date_obj:
            raise InvalidInputError("Leave start date cannot be after end date.")
    except ValueError:
        raise InvalidInputError("Invalid date format. Use YYYY-MM-DD.")
    
    assigned_approver_user_id = None
    requesting_employee_details = _find_employee_by_id(employee_id)
    if requesting_employee_details and requesting_employee_details.get(database.COL_EMP_MANAGER_ID):
        manager_emp_id = requesting_employee_details[database.COL_EMP_MANAGER_ID]
        manager_user_details = get_user_by_employee_id_db(manager_emp_id) 
        if manager_user_details and manager_user_details.get(database.COL_USER_ID): # Ensure user_id exists
            assigned_approver_user_id = manager_user_details[database.COL_USER_ID]
            logger.info(f"Leave request for {employee_id} assigned to manager {manager_emp_id} (User ID: {assigned_approver_user_id}).")

    if not assigned_approver_user_id: 
        default_approver_id_str = database.get_app_setting_db(database.SETTING_DEFAULT_LEAVE_APPROVER_USER_ID, "1")
        assigned_approver_user_id = int(default_approver_id_str) if default_approver_id_str and default_approver_id_str.isdigit() else 1
        logger.info(f"Leave request for {employee_id} assigned to default approver (User ID: {assigned_approver_user_id}).")

    request_date_str = dt_date.today().isoformat()
    query = f"""
        INSERT INTO {database.TABLE_LEAVE_REQUESTS} (
            {database.COL_LR_EMP_ID}, {database.COL_LR_LEAVE_TYPE}, {database.COL_LR_START_DATE}, {database.COL_LR_END_DATE},
            {database.COL_LR_REASON}, {database.COL_LR_REQUEST_DATE}, {database.COL_LR_STATUS}, {database.COL_LR_ASSIGNED_APPROVER_USER_ID}
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pending Approval', ?)
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, leave_type, start_date_str, end_date_str, reason, request_date_str, assigned_approver_user_id))
            conn.commit()
            logger.info(f"Leave request added for employee {employee_id} from {start_date_str} to {end_date_str}.")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error adding leave request for {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to add leave request: {e}")

def rotate_all_employee_shifts_db() -> int:
    """
    Rotates the shifts for all active employees.
    Cycle: Morning -> Evening -> Night -> Morning.
    Returns the number of employees whose shifts were updated.
    """
    SHIFT_ORDER = ["Morning", "Evening", "Night"]
    employees_updated_count = 0
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Fetch all active employees and their current shifts
            cursor.execute(f"SELECT {database.COL_EMP_ID}, {database.COL_EMP_CURRENT_SHIFT} FROM {database.TABLE_EMPLOYEES} WHERE {database.COL_EMP_STATUS} = ? AND ({database.COL_EMP_IS_ARCHIVED} = 0 OR {database.COL_EMP_IS_ARCHIVED} IS NULL)", (database.STATUS_ACTIVE,))
            active_employees = cursor.fetchall()

            for emp_id, current_shift in active_employees:
                current_shift = current_shift or SHIFT_ORDER[0] # Default to Morning if None
                try:
                    current_index = SHIFT_ORDER.index(current_shift)
                    next_index = (current_index + 1) % len(SHIFT_ORDER)
                    next_shift = SHIFT_ORDER[next_index]
                    cursor.execute(f"UPDATE {database.TABLE_EMPLOYEES} SET {database.COL_EMP_CURRENT_SHIFT} = ? WHERE {database.COL_EMP_ID} = ?", (next_shift, emp_id))
                    employees_updated_count += 1
                except ValueError: # current_shift not in SHIFT_ORDER
                    logger.warning(f"Employee {emp_id} has an unknown shift '{current_shift}'. Setting to '{SHIFT_ORDER[0]}'.")
                    cursor.execute(f"UPDATE {database.TABLE_EMPLOYEES} SET {database.COL_EMP_CURRENT_SHIFT} = ? WHERE {database.COL_EMP_ID} = ?", (SHIFT_ORDER[0], emp_id))
            conn.commit()
            logger.info(f"Rotated shifts for {employees_updated_count} employees.")
    except sqlite3.Error as e:
        logger.error(f"Database error rotating employee shifts: {e}")
        raise DatabaseOperationError(f"Failed to rotate employee shifts: {e}")
    finally:
        if conn: conn.close()

# --- Training Course Management Backend Functions ---
def add_training_course_db(name: str, description: Optional[str] = None, provider: Optional[str] = None, default_duration_hours: Optional[float] = None) -> int:
    """Adds a new training course."""
    if not name:
        raise InvalidInputError("Course name cannot be empty.")
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database.TABLE_TRAINING_COURSES} 
                ({database.COL_COURSE_NAME}, {database.COL_COURSE_DESCRIPTION}, {database.COL_COURSE_PROVIDER}, {database.COL_COURSE_DEFAULT_DURATION_HOURS}) 
                VALUES (?, ?, ?, ?)
            """, (name, description, provider, default_duration_hours))
            conn.commit()
            logger.info(f"Training course '{name}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid # type: ignore
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Training course name '{name}' already exists.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to add training course '{name}': {e}")

def get_all_training_courses_db() -> List[Dict]:
    """Lists all training courses."""
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {database.TABLE_TRAINING_COURSES} ORDER BY {database.COL_COURSE_NAME}")
        return [dict(row) for row in cursor.fetchall()]

def update_training_course_db(course_id: int, name: Optional[str] = None, description: Optional[str] = None, provider: Optional[str] = None, default_duration_hours: Optional[float] = None) -> bool:
    """Updates an existing training course."""
    updates: Dict[str, Any] = {}
    if name is not None: updates[database.COL_COURSE_NAME] = name
    if description is not None: updates[database.COL_COURSE_DESCRIPTION] = description
    if provider is not None: updates[database.COL_COURSE_PROVIDER] = provider
    if default_duration_hours is not None: updates[database.COL_COURSE_DEFAULT_DURATION_HOURS] = default_duration_hours
    
    if not updates: return True

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    params = list(updates.values()) + [course_id]
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {database.TABLE_TRAINING_COURSES} SET {set_clause} WHERE {database.COL_COURSE_ID} = ?", tuple(params))
            if cursor.rowcount == 0:
                raise HRException(f"Training course ID {course_id} not found for update.")
            conn.commit()
        logger.info(f"Training course ID {course_id} updated.")
        return True
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Training course name '{name}' might already exist.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to update training course ID {course_id}: {e}")

def delete_training_course_db(course_id: int) -> bool:
    """Deletes a training course. Fails if it's used in any training sessions (due to RESTRICT - to be added later)."""
    # TODO: Add check for usage in training_sessions table when it's created.
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {database.TABLE_TRAINING_COURSES} WHERE {database.COL_COURSE_ID} = ?", (course_id,))
            if cursor.rowcount == 0: raise HRException(f"Training course ID {course_id} not found for deletion.")
            conn.commit()
        logger.info(f"Training course ID {course_id} deleted.")
        return True
    except sqlite3.IntegrityError: # This will catch the RESTRICT violation if sessions table has FK
        raise DatabaseOperationError(f"Cannot delete course ID {course_id}: it is currently in use in scheduled sessions.")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete course ID {course_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete course ID {course_id}: {e}")

# --- Skill Management Backend Functions ---

def add_skill_db(name: str, description: Optional[str] = None, category: Optional[str] = None) -> int:
    """Adds a new skill to the skills table."""
    if not name:
        raise InvalidInputError("Skill name cannot be empty.")
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database.TABLE_SKILLS}
                ({database.COL_SKILL_NAME}, {database.COL_SKILL_DESCRIPTION}, {database.COL_SKILL_CATEGORY})
                VALUES (?, ?, ?)
            """, (name, description, category))
            conn.commit()
            logger.info(f"Skill '{name}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid # type: ignore
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Skill name '{name}' already exists.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to add skill '{name}': {e}")

def get_all_skills_db() -> List[Dict]:
    """Lists all skills from the skills table."""
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {database.TABLE_SKILLS} ORDER BY {database.COL_SKILL_NAME}")
        return [dict(row) for row in cursor.fetchall()]

def update_skill_db(skill_id: int, name: Optional[str] = None, description: Optional[str] = None, category: Optional[str] = None) -> bool:
    """Updates an existing skill."""
    updates: Dict[str, Any] = {}
    if name is not None: updates[database.COL_SKILL_NAME] = name
    if description is not None: updates[database.COL_SKILL_DESCRIPTION] = description
    if category is not None: updates[database.COL_SKILL_CATEGORY] = category

    if not updates: return True

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    params = list(updates.values()) + [skill_id]
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {database.TABLE_SKILLS} SET {set_clause} WHERE {database.COL_SKILL_ID} = ?", tuple(params))
            if cursor.rowcount == 0:
                raise HRException(f"Skill ID {skill_id} not found for update.")
            conn.commit()
        logger.info(f"Skill ID {skill_id} updated.")
        return True
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Skill name '{name}' might already exist.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to update skill ID {skill_id}: {e}")

def delete_skill_db(skill_id: int) -> bool:
    """Deletes a skill. Fails if it's assigned to any employee (due to RESTRICT)."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Check if skill is in use before attempting deletion (due to RESTRICT)
            cursor.execute(f"SELECT 1 FROM {database.TABLE_EMPLOYEE_SKILLS} WHERE {database.COL_EMP_SKILL_SKILL_ID} = ?", (skill_id,))
            if cursor.fetchone():
                raise DatabaseOperationError(f"Cannot delete skill ID {skill_id}: it is currently assigned to one or more employees.")

            cursor.execute(f"DELETE FROM {database.TABLE_SKILLS} WHERE {database.COL_SKILL_ID} = ?", (skill_id,))
            if cursor.rowcount == 0: raise HRException(f"Skill ID {skill_id} not found for deletion.")
            conn.commit()
        logger.info(f"Skill ID {skill_id} deleted.")
        return True
    except sqlite3.IntegrityError: # Should be caught by the check above now
        raise DatabaseOperationError(f"Cannot delete skill ID {skill_id}: it is currently assigned to one or more employees.")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete skill ID {skill_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete skill ID {skill_id}: {e}")

# --- Employee Skill Management Backend Functions ---

def assign_skill_to_employee_db(employee_id: str, skill_id: int, proficiency_level: Optional[str] = None, acquisition_date_str: Optional[str] = None) -> bool:
    """Assigns a skill to an employee or updates it if it already exists."""
    if not _find_employee_by_id(employee_id): raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    # TODO: Check if skill_id exists in skills table (e.g., create get_skill_by_id_db)
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT OR REPLACE INTO {database.TABLE_EMPLOYEE_SKILLS}
                ({database.COL_EMP_SKILL_EMP_ID}, {database.COL_EMP_SKILL_SKILL_ID}, {database.COL_EMP_SKILL_PROFICIENCY_LEVEL}, {database.COL_EMP_SKILL_ACQUISITION_DATE})
                VALUES (?, ?, ?, ?)
            """, (employee_id, skill_id, proficiency_level, acquisition_date_str))
            conn.commit()
            logger.info(f"Skill ID {skill_id} assigned to/updated for employee {employee_id}.")
            return True
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to assign skill {skill_id} to employee {employee_id}: {e}")

def get_employee_skills_db(employee_id: str) -> List[Dict]:
    """Retrieves all skills for a specific employee, including skill details."""
    query = f"""
        SELECT es.*, s.{database.COL_SKILL_NAME}, s.{database.COL_SKILL_CATEGORY}, s.{database.COL_SKILL_DESCRIPTION}
        FROM {database.TABLE_EMPLOYEE_SKILLS} es
        JOIN {database.TABLE_SKILLS} s ON es.{database.COL_EMP_SKILL_SKILL_ID} = s.{database.COL_SKILL_ID}
        WHERE es.{database.COL_EMP_SKILL_EMP_ID} = ?
        ORDER BY s.{database.COL_SKILL_NAME}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]

def remove_skill_from_employee_db(employee_id: str, skill_id: int) -> bool:
    """Removes a specific skill from an employee."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                DELETE FROM {database.TABLE_EMPLOYEE_SKILLS}
                WHERE {database.COL_EMP_SKILL_EMP_ID} = ? AND {database.COL_EMP_SKILL_SKILL_ID} = ?
            """, (employee_id, skill_id))
            if cursor.rowcount == 0:
                logger.warning(f"No skill ID {skill_id} found for employee {employee_id} to remove.")
                return False # Or raise an exception if preferred
            conn.commit()
            logger.info(f"Skill ID {skill_id} removed from employee {employee_id}.")
            return True
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to remove skill {skill_id} from employee {employee_id}: {e}")
    return employees_updated_count

# --- Skill Management Backend Functions ---

def add_skill_db(name: str, description: Optional[str] = None, category: Optional[str] = None) -> int:
    """Adds a new skill to the skills table."""
    if not name:
        raise InvalidInputError("Skill name cannot be empty.")
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database.TABLE_SKILLS} 
                ({database.COL_SKILL_NAME}, {database.COL_SKILL_DESCRIPTION}, {database.COL_SKILL_CATEGORY}) 
                VALUES (?, ?, ?)
            """, (name, description, category))
            conn.commit()
            logger.info(f"Skill '{name}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid # type: ignore
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Skill name '{name}' already exists.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to add skill '{name}': {e}")

def get_all_skills_db() -> List[Dict]:
    """Lists all skills from the skills table."""
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {database.TABLE_SKILLS} ORDER BY {database.COL_SKILL_NAME}")
        return [dict(row) for row in cursor.fetchall()]

def update_skill_db(skill_id: int, name: Optional[str] = None, description: Optional[str] = None, category: Optional[str] = None) -> bool:
    """Updates an existing skill."""
    updates: Dict[str, Any] = {}
    if name is not None: updates[database.COL_SKILL_NAME] = name
    if description is not None: updates[database.COL_SKILL_DESCRIPTION] = description
    if category is not None: updates[database.COL_SKILL_CATEGORY] = category
    
    if not updates: return True

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    params = list(updates.values()) + [skill_id]
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {database.TABLE_SKILLS} SET {set_clause} WHERE {database.COL_SKILL_ID} = ?", tuple(params))
            if cursor.rowcount == 0:
                raise HRException(f"Skill ID {skill_id} not found for update.")
            conn.commit()
        logger.info(f"Skill ID {skill_id} updated.")
        return True
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Skill name '{name}' might already exist.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to update skill ID {skill_id}: {e}")

def delete_skill_db(skill_id: int) -> bool:
    """Deletes a skill. Fails if it's assigned to any employee (due to RESTRICT)."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Check if skill is in use before attempting deletion (due to RESTRICT)
            cursor.execute(f"SELECT 1 FROM {database.TABLE_EMPLOYEE_SKILLS} WHERE {database.COL_EMP_SKILL_SKILL_ID} = ?", (skill_id,))
            if cursor.fetchone():
                raise DatabaseOperationError(f"Cannot delete skill ID {skill_id}: it is currently assigned to one or more employees.")
            
            cursor.execute(f"DELETE FROM {database.TABLE_SKILLS} WHERE {database.COL_SKILL_ID} = ?", (skill_id,))
            if cursor.rowcount == 0: raise HRException(f"Skill ID {skill_id} not found for deletion.")
            conn.commit()
        logger.info(f"Skill ID {skill_id} deleted.")
        return True
    except sqlite3.IntegrityError: # Should be caught by the check above now
        raise DatabaseOperationError(f"Cannot delete skill ID {skill_id}: it is currently assigned to one or more employees.")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete skill ID {skill_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete skill ID {skill_id}: {e}")

# --- Employee Skill Management Backend Functions ---

def assign_skill_to_employee_db(employee_id: str, skill_id: int, proficiency_level: Optional[str] = None, acquisition_date_str: Optional[str] = None) -> bool:
    """Assigns a skill to an employee or updates it if it already exists."""
    if not _find_employee_by_id(employee_id): raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    # TODO: Check if skill_id exists in skills table
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT OR REPLACE INTO {database.TABLE_EMPLOYEE_SKILLS} 
                ({database.COL_EMP_SKILL_EMP_ID}, {database.COL_EMP_SKILL_SKILL_ID}, {database.COL_EMP_SKILL_PROFICIENCY_LEVEL}, {database.COL_EMP_SKILL_ACQUISITION_DATE})
                VALUES (?, ?, ?, ?)
            """, (employee_id, skill_id, proficiency_level, acquisition_date_str))
            conn.commit()
            logger.info(f"Skill ID {skill_id} assigned to/updated for employee {employee_id}.")
            return True
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to assign skill {skill_id} to employee {employee_id}: {e}")

def get_employee_skills_db(employee_id: str) -> List[Dict]:
    """Retrieves all skills for a specific employee, including skill details."""
    query = f"""
        SELECT es.*, s.{database.COL_SKILL_NAME}, s.{database.COL_SKILL_CATEGORY}, s.{database.COL_SKILL_DESCRIPTION}
        FROM {database.TABLE_EMPLOYEE_SKILLS} es
        JOIN {database.TABLE_SKILLS} s ON es.{database.COL_EMP_SKILL_SKILL_ID} = s.{database.COL_SKILL_ID}
        WHERE es.{database.COL_EMP_SKILL_EMP_ID} = ?
        ORDER BY s.{database.COL_SKILL_NAME}
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]

def remove_skill_from_employee_db(employee_id: str, skill_id: int) -> bool:
    """Removes a specific skill from an employee."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                DELETE FROM {database.TABLE_EMPLOYEE_SKILLS} 
                WHERE {database.COL_EMP_SKILL_EMP_ID} = ? AND {database.COL_EMP_SKILL_SKILL_ID} = ?
            """, (employee_id, skill_id))
            if cursor.rowcount == 0:
                logger.warning(f"No skill ID {skill_id} found for employee {employee_id} to remove.")
                return False # Or raise an exception if preferred
            conn.commit()
            logger.info(f"Skill ID {skill_id} removed from employee {employee_id}.")
            return True
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to remove skill {skill_id} from employee {employee_id}: {e}")

def get_leave_requests_for_employee_db(employee_id: str) -> List[Dict]:
    """
    Fetches all leave requests for a specific employee, ordered by request date descending.
    Args:
        employee_id (str): The ID of the employee.
    Returns:
        List[Dict]: A list of leave request dictionaries.
    Raises:
        DatabaseOperationError: If a database error occurs.
    """
    if not employee_id:
        return []
    query = f"""
        SELECT lr.*, u_approver.{database.COL_USER_USERNAME} as assigned_approver_username
        FROM {database.TABLE_LEAVE_REQUESTS} lr
        LEFT JOIN {database.TABLE_USERS} u_approver ON lr.{database.COL_LR_ASSIGNED_APPROVER_USER_ID} = u_approver.{database.COL_USER_ID}
        WHERE lr.{database.COL_LR_EMP_ID} = ?
        ORDER BY lr.{database.COL_LR_REQUEST_DATE} DESC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]

def is_department_busy_for_leave(department_id: int, leave_start_date_str: str, leave_end_date_str: str, requesting_employee_id: str) -> bool:
    """
    Checks if a department is considered "busy" for a new leave request.
    "Busy" is defined by a configurable percentage of active employees in the department
    already being on approved leave during any part of the requested period.
    """
    if not department_id:
        return False

    busy_threshold_percent_str = database.get_app_setting_db(database.SETTING_LEAVE_BUSY_THRESHOLD_PERCENT_DEPT, "30")
    try:
        busy_threshold_percent = int(busy_threshold_percent_str)
    except ValueError:
        logger.warning(f"Invalid busy threshold '{busy_threshold_percent_str}', defaulting to 30%.")
        busy_threshold_percent = 30

    active_employees_in_dept_count = get_employee_count_for_department_db(department_id)
    if active_employees_in_dept_count == 0:
        return False # No active employees, so not busy

    # Count employees in the department (excluding the requester) already on approved leave during the period
    query = f"""
        SELECT COUNT(DISTINCT lr.{database.COL_LR_EMP_ID})
        FROM {database.TABLE_LEAVE_REQUESTS} lr
        JOIN {database.TABLE_EMPLOYEES} e ON lr.{database.COL_LR_EMP_ID} = e.{database.COL_EMP_ID}
        WHERE e.{database.COL_EMP_DEPARTMENT_ID} = ?
          AND lr.{database.COL_LR_EMP_ID} != ? 
          AND lr.{database.COL_LR_STATUS} = 'Approved'
          AND lr.{database.COL_LR_START_DATE} <= ? 
          AND lr.{database.COL_LR_END_DATE} >= ?
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (department_id, requesting_employee_id, leave_end_date_str, leave_start_date_str))
        concurrent_leaves_count = cursor.fetchone()[0] or 0

    # Calculate percentage of employees on leave
    percentage_on_leave = (concurrent_leaves_count / active_employees_in_dept_count) * 100
    return percentage_on_leave >= busy_threshold_percent

def get_concurrent_department_leaves(department_id: int, leave_start_date_str: str, leave_end_date_str: str, exclude_employee_id: str) -> List[Dict]:
    """
    Finds approved leave requests from other employees in the same department
    that overlap with the given leave period.
    Args:
        department_id (int): The ID of the department to check.
        leave_start_date_str (str): The start date of the proposed leave (YYYY-MM-DD).
        leave_end_date_str (str): The end date of the proposed leave (YYYY-MM-DD).
        exclude_employee_id (str): The ID of the employee requesting the leave (to exclude their own leaves).
    Returns:
        List[Dict]: A list of conflicting leave request dictionaries, including employee name.
    """
    if not department_id:
        return []
    query = f"""
        SELECT lr.*, e.{database.COL_EMP_NAME}
        FROM {database.TABLE_LEAVE_REQUESTS} lr
        JOIN {database.TABLE_EMPLOYEES} e ON lr.{database.COL_LR_EMP_ID} = e.{database.COL_EMP_ID}
        WHERE e.{database.COL_EMP_DEPARTMENT_ID} = ?
          AND lr.{database.COL_LR_EMP_ID} != ?
          AND lr.{database.COL_LR_STATUS} = 'Approved'
          AND lr.{database.COL_LR_START_DATE} <= ? -- Existing leave starts before or on new leave's end date
          AND lr.{database.COL_LR_END_DATE} >= ?   -- Existing leave ends after or on new leave's start date
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (department_id, exclude_employee_id, leave_end_date_str, leave_start_date_str))
        return [dict(row) for row in cursor.fetchall()]

def get_payslips_for_employee_db(employee_id: str) -> List[Dict]:
    """
    Fetches all payslip records for a specific employee, ordered by generation date descending.
    Args:
        employee_id (str): The ID of the employee.
    Returns:
        List[Dict]: A list of payslip dictionaries.
    """
    if not employee_id:
        return []
    query = f"""
        SELECT * FROM {database.TABLE_PAYSLIPS}
        WHERE {database.COL_PAY_EMP_ID} = ?
        ORDER BY {database.COL_PAY_GENERATION_DATE} DESC
    """
    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]
    
def get_leave_request_details_db(request_id: int) -> Optional[Dict]:
    """
    Fetches detailed information for a specific leave request, including the leave type name.
    Args:
        request_id (int): The ID of the leave request.
    Returns:
        Optional[Dict]: A dictionary containing leave request details, or None if not found.
    """
    query = f"""
        SELECT
            lr.*,
            lt.{db_schema.COL_LT_NAME}
        FROM {db_schema.TABLE_LEAVE_REQUESTS} lr
        JOIN {db_schema.TABLE_LEAVE_TYPES} lt ON lr.{db_schema.COL_LR_LEAVE_TYPE_ID} = lt.{db_schema.COL_LT_ID}
        WHERE lr.{db_schema.COL_LR_ID} = ?
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (request_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching leave request details for ID {request_id}: {e}", exc_info=True)
        raise db_schema.DatabaseOperationError(f"Could not fetch leave request details: {e}")

# --- Attendance Utils Support Functions ---
def is_employee_on_approved_leave_today(employee_id: str, date_str: str) -> bool:
    """
    Checks if an employee has an approved leave request for the given date.

    Args:
        employee_id: The ID of the employee.
        date_str: The date to check, in "YYYY-MM-DD" format.

    Returns:
        True if the employee is on approved leave, False otherwise.
    """
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn: # Use sqlite3.connect directly

            cursor = conn.cursor()
            query = f"""
                SELECT 1
                FROM {database.TABLE_LEAVE_REQUESTS}
                WHERE {database.COL_LR_EMP_ID} = ?
                  AND {database.COL_LR_START_DATE} <= ?
                  AND {database.COL_LR_END_DATE} >= ?
                  AND {database.COL_LR_STATUS} = ?
                LIMIT 1
            """
            cursor.execute(query, (employee_id, date_str, date_str, database.STATUS_LEAVE_APPROVED))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Database error checking leave status for employee {employee_id} on {date_str}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error checking leave status for employee {employee_id} on {date_str}: {e}")
    return False

# --- Evaluation Criteria Backend Functions ---
def add_evaluation_criterion_db(name: str, description: Optional[str] = None, max_points: int = 10) -> int:
    """Adds a new evaluation criterion."""
    if not name:
        raise InvalidInputError("Criterion name cannot be empty.")
    if not isinstance(max_points, int) or max_points <= 0:
        raise InvalidInputError("Max points must be a positive integer.")
    try:
        with database.create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database.TABLE_EVALUATION_CRITERIA} 
                ({database.COL_CRITERIA_NAME}, {database.COL_CRITERIA_DESCRIPTION}, {database.COL_CRITERIA_MAX_POINTS}) 
                VALUES (?, ?, ?)
            """, (name, description, max_points))
            conn.commit()
            logger.info(f"Evaluation criterion '{name}' added with ID {cursor.lastrowid}.")
            return cursor.lastrowid # type: ignore
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Evaluation criterion name '{name}' already exists.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to add evaluation criterion '{name}': {e}")

def list_evaluation_criteria_db() -> List[Dict]:
    """Lists all evaluation criteria."""
    with database.create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {database.TABLE_EVALUATION_CRITERIA} ORDER BY {database.COL_CRITERIA_NAME}")
        return [dict(row) for row in cursor.fetchall()]

def update_evaluation_criterion_db(criteria_id: int, name: Optional[str] = None, 
                                   description: Optional[str] = None, max_points: Optional[int] = None) -> bool:
    """Updates an existing evaluation criterion."""
    updates = {}
    if name is not None: updates[database.COL_CRITERIA_NAME] = name
    if description is not None: updates[database.COL_CRITERIA_DESCRIPTION] = description
    if max_points is not None:
        if not isinstance(max_points, int) or max_points <= 0:
            raise InvalidInputError("Max points must be a positive integer.")
        updates[database.COL_CRITERIA_MAX_POINTS] = max_points
    
    if not updates: return True

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    params = list(updates.values()) + [criteria_id]
    try:
        with database.create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {database.TABLE_EVALUATION_CRITERIA} SET {set_clause} WHERE {database.COL_CRITERIA_ID} = ?", tuple(params))
            if cursor.rowcount == 0:
                raise HRException(f"Criterion ID {criteria_id} not found for update.")
            conn.commit()
        logger.info(f"Evaluation criterion ID {criteria_id} updated.")
        return True
    except sqlite3.IntegrityError:
        raise InvalidInputError(f"Evaluation criterion name '{name}' already exists.")
    except sqlite3.Error as e:
        raise DatabaseOperationError(f"Failed to update criterion ID {criteria_id}: {e}")

def delete_evaluation_criterion_db(criteria_id: int) -> bool:
    """Deletes an evaluation criterion. Fails if it's used in any evaluation_details (due to RESTRICT)."""
    try:
        with database.create_connection() as conn:
            cursor = conn.cursor()
            # Check if criterion is in use before attempting deletion
            cursor.execute(f"SELECT 1 FROM {database.TABLE_EVALUATION_DETAILS} WHERE {database.COL_EVAL_DETAIL_CRITERIA_ID} = ?", (criteria_id,))
            if cursor.fetchone():
                raise DatabaseOperationError(f"Cannot delete criterion ID {criteria_id}: it is currently in use in evaluations.")
            
            cursor.execute(f"DELETE FROM {database.TABLE_EVALUATION_CRITERIA} WHERE {database.COL_CRITERIA_ID} = ?", (criteria_id,))
            if cursor.rowcount == 0: raise HRException(f"Criterion ID {criteria_id} not found for deletion.")
            conn.commit()
        logger.info(f"Evaluation criterion ID {criteria_id} deleted.")
        return True
    except sqlite3.IntegrityError: # Should be caught by the check above now
        raise DatabaseOperationError(f"Cannot delete criterion ID {criteria_id}: it is currently in use in evaluations.")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete criterion ID {criteria_id}: {e}")
        raise DatabaseOperationError(f"Failed to delete criterion ID {criteria_id}: {e}")

# --- Employee Evaluation Backend Functions ---
def add_employee_evaluation_db(employee_id: str, period: str, eval_date_str: str,
                               total_score: float, comments: Optional[str],
                               scores_details: List[Dict[str, Any]], # [{"criteria_id": int, "score": float, "comment": str}, ...]
                               evaluator_user_id: int) -> int:
    """Adds a new employee evaluation and its details."""
    if not _find_employee_by_id(employee_id):
        raise EmployeeNotFoundError(f"Employee ID {employee_id} not found.")
    if not period or not eval_date_str:
        raise InvalidInputError("Evaluation period and date are required.")
    try:
        datetime.strptime(eval_date_str, '%Y-%m-%d')
    except ValueError:
        raise InvalidInputError("Invalid evaluation date format. Use YYYY-MM-DD.")

    conn = None
    try:
        conn = database.create_connection()
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # Insert main evaluation record
        cursor.execute(f"""
            INSERT INTO {database.TABLE_EMPLOYEE_EVALUATIONS}
            ({database.COL_EVAL_EMP_ID}, {database.COL_EVAL_PERIOD}, {database.COL_EVAL_DATE},
             {database.COL_EVAL_TOTAL_SCORE}, {database.COL_EVAL_COMMENTS}, {database.COL_EVAL_EVALUATOR_ID})
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, period, eval_date_str, total_score, comments, evaluator_user_id))
        evaluation_id = cursor.lastrowid

        # Insert score details
        for detail in scores_details:
            cursor.execute(f"""
                INSERT INTO {database.TABLE_EVALUATION_DETAILS}
                ({database.COL_EVAL_DETAIL_EVAL_ID}, {database.COL_EVAL_DETAIL_CRITERIA_ID},
                 {database.COL_EVAL_DETAIL_SCORE}, {database.COL_EVAL_DETAIL_COMMENT})
                VALUES (?, ?, ?, ?)
            """, (evaluation_id, detail["criteria_id"], detail["score"], detail.get("comment")))

        conn.commit()
        logger.info(f"Employee evaluation ID {evaluation_id} for {employee_id} added successfully.")
        return evaluation_id
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error adding employee evaluation for {employee_id}: {e}")
        raise DatabaseOperationError(f"Failed to add employee evaluation: {e}")
    finally:
        if conn: conn.close()

def get_employee_evaluations_db(employee_id: str) -> List[Dict]:
    """Retrieves all evaluations for a specific employee, including evaluator's username."""
    query = f"""
        SELECT ev.*, u.{database.COL_USER_USERNAME} as evaluator_username
        FROM {database.TABLE_EMPLOYEE_EVALUATIONS} ev
        LEFT JOIN {database.TABLE_USERS} u ON ev.{database.COL_EVAL_EVALUATOR_ID} = u.{database.COL_USER_ID}
        WHERE ev.{database.COL_EVAL_EMP_ID} = ?
        ORDER BY ev.{database.COL_EVAL_DATE} DESC
    """
    with database.create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (employee_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_evaluation_details_db(evaluation_id: int) -> Optional[Dict]:
    """Retrieves a specific evaluation and its details by evaluation_id."""
    evaluation_data = {}
    # Get main evaluation record
    main_eval_query = f"""
        SELECT ev.*, u.{database.COL_USER_USERNAME} as evaluator_username
        FROM {database.TABLE_EMPLOYEE_EVALUATIONS} ev
        LEFT JOIN {database.TABLE_USERS} u ON ev.{database.COL_EVAL_EVALUATOR_ID} = u.{database.COL_USER_ID}
        WHERE ev.{database.COL_EVAL_ID} = ?
    """
    with database.create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(main_eval_query, (evaluation_id,))
        main_row = cursor.fetchone()
        if not main_row:
            return None
        evaluation_data = dict(main_row)

        # Get evaluation details (scores for criteria)
        details_query = f"""
            SELECT ed.*, ec.{database.COL_CRITERIA_NAME}, ec.{database.COL_CRITERIA_MAX_POINTS}
            FROM {database.TABLE_EVALUATION_DETAILS} ed
            JOIN {database.TABLE_EVALUATION_CRITERIA} ec ON ed.{database.COL_EVAL_DETAIL_CRITERIA_ID} = ec.{database.COL_CRITERIA_ID}
            WHERE ed.{database.COL_EVAL_DETAIL_EVAL_ID} = ?
        """
        cursor.execute(details_query, (evaluation_id,))
        evaluation_data["details"] = [dict(row) for row in cursor.fetchall()]
    return evaluation_data

def get_all_evaluation_criteria_db() -> List[Dict]:
    """Lists all evaluation criteria (renamed from list_evaluation_criteria_db for consistency)."""
    with database.create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {database.TABLE_EVALUATION_CRITERIA} ORDER BY {database.COL_CRITERIA_NAME}")
        return [dict(row) for row in cursor.fetchall()]

# TODO: Implement update_employee_evaluation_db if needed