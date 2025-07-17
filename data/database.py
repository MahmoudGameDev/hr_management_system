# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\data\database.py
import sqlite3
import logging
import bcrypt # For default admin user password hashing
from typing import Optional, List, Dict, Any

# Assuming config.py is in the project root, one level above 'data'
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config # Now this should work

logger = logging.getLogger(__name__)

# --- Database Table and Column Constants ---
TABLE_EMPLOYEES = "employees"
COL_EMP_ID = "id"
COL_EMP_DEPARTMENT = "department_name" # Alias for department name after join
COL_EMP_NAME = "name"
COL_EMP_DEPARTMENT_ID = "department_id" # Foreign key to departments table
COL_EMP_POSITION = "position"
COL_EMP_SALARY = "salary"
COL_EMP_VACATION_DAYS = "vacation_days"
COL_EMP_STATUS = "status"               # e.g., Active, Terminated
COL_EMP_TERMINATION_DATE = "termination_date"
COL_EMP_START_DATE = "start_date"
COL_EMP_PHONE = "phone"
COL_EMP_EMAIL = "email"
COL_EMP_PHOTO_PATH = "photo_path"
COL_EMP_GENDER = "gender"
COL_EMP_MARITAL_STATUS = "marital_status"
COL_EMP_EDUCATION = "educational_qualification"
COL_EMP_EMPLOYMENT_HISTORY = "employment_history"
COL_EMP_DEVICE_USER_ID = "device_user_id"
COL_EMP_MANAGER_ID = "manager_emp_id" # FK to employees table (self-referencing for manager)
COL_EMP_CURRENT_SHIFT = "current_shift" # New column for current shift
COL_EMP_EXCLUDE_VACATION_POLICY = "exclude_vacation_policy" # INTEGER 0 or 1
COL_EMP_IS_ARCHIVED = "is_archived" # INTEGER 0 or 1
COL_EMP_ARCHIVED_DATE = "archived_date" # TEXT ISO8601

TABLE_DEPARTMENTS = "departments"
COL_DEPT_ID = "department_id"
COL_DEPT_NAME = "department_name"
COL_DEPT_DESCRIPTION = "department_description"

TABLE_USERS = "users"
COL_USER_ID = "user_id"
COL_USER_USERNAME = "username"
COL_USER_PASSWORD_HASH = "password_hash"
COL_USER_ROLE = "role"
COL_USER_LINKED_EMP_ID = "employee_id" # Links user to an employee record

TABLE_ATTENDANCE_LOG = "attendance_log"
COL_ATT_LOG_ID = "log_id"
COL_ATT_EMP_ID = "employee_id"
COL_ATT_CLOCK_IN = "clock_in_time"
COL_ATT_CLOCK_OUT = "clock_out_time"
COL_ATT_LOG_DATE = "log_date"
COL_ATT_SOURCE = "source"
COL_ATT_NOTES = "notes"

TABLE_LEAVE_REQUESTS = "leave_requests"
COL_LR_ID = "request_id"
COL_LR_EMP_ID = "employee_id"
COL_LR_LEAVE_TYPE = "leave_type"
COL_LR_START_DATE = "start_date"
COL_LR_END_DATE = "end_date"
COL_LR_REASON = "reason"
COL_LR_REQUEST_DATE = "request_date"
COL_LR_STATUS = "status" # Pending Approval, Approved, Rejected, Cancelled
COL_LR_ASSIGNED_APPROVER_USER_ID = "assigned_approver_user_id"
COL_LR_PROCESSED_BY_USER_ID = "processed_by_user_id"
COL_LR_APPROVER_COMMENTS = "approver_comments"
COL_LR_PROCESSED_DATE = "processed_date"

TABLE_EMPLOYEE_DOCUMENTS = "employee_documents"
COL_DOC_ID = "doc_id"
COL_DOC_EMP_ID = "employee_id"
COL_DOC_TYPE = "doc_type"
COL_DOC_FILE_PATH = "file_path"
COL_DOC_UPLOAD_DATE = "upload_date"
COL_DOC_NOTES = "notes"

TABLE_APP_SETTINGS = "app_settings"
COL_SETTING_KEY = "setting_key"
COL_SETTING_VALUE = "setting_value"
# App Counters Table
TABLE_APP_COUNTERS = "app_counters"
COL_COUNTER_NAME = "counter_name"
COL_COUNTER_VALUE = "current_value"

TABLE_EVALUATION_CRITERIA = "evaluation_criteria"
COL_CRITERIA_ID = "criteria_id"
COL_CRITERIA_NAME = "name"
COL_CRITERIA_DESCRIPTION = "description"
COL_CRITERIA_MAX_POINTS = "max_points"

TABLE_EMPLOYEE_EVALUATIONS = "employee_evaluations"
COL_EVAL_ID = "evaluation_id"
COL_EVAL_EMP_ID = "employee_id"
COL_EVAL_PERIOD = "evaluation_period"
COL_EVAL_DATE = "evaluation_date"
COL_EVAL_TOTAL_SCORE = "total_score"
COL_EVAL_EVALUATOR_ID = "evaluator_id" # User ID of the evaluator
COL_EVAL_COMMENTS = "comments" # Changed from notes to comments for consistency

TABLE_EVALUATION_DETAILS = "evaluation_details"
COL_EVAL_DETAIL_ID = "eval_detail_id"
COL_EVAL_DETAIL_EVAL_ID = "evaluation_id"
COL_EVAL_DETAIL_CRITERIA_ID = "criteria_id"
COL_EVAL_DETAIL_SCORE = "score_awarded"
COL_EVAL_DETAIL_COMMENT = "comment"

TABLE_EMPLOYEE_ACTION_LOG = "employee_action_log"
COL_EAL_LOG_ID = "log_id"
COL_EAL_EMP_ID = "employee_id"
COL_EAL_ACTION_DESC = "action_description"
COL_EAL_PERFORMED_BY_USER_ID = "performed_by_user_id"
COL_EAL_TIMESTAMP = "timestamp"

TABLE_FINGERPRINT_TEMPLATES = "fingerprint_templates"
COL_FP_TEMPLATE_ID = "template_id"
COL_FP_EMP_ID = "employee_id"
COL_FP_TEMPLATE_DATA = "template_data" # BLOB
COL_FP_ENROLLED_DATE = "enrolled_date"

TABLE_EMP_ALLOWANCES = "employee_allowances"
COL_ALLW_ID = "allowance_id"
COL_ALLW_EMP_ID = "employee_id"
COL_ALLW_TYPE = "allowance_type"
COL_ALLW_AMOUNT = "amount"
COL_ALLW_IS_RECURRING = "is_recurring" # INTEGER (0 or 1)
COL_ALLW_EFF_DATE = "effective_date"
COL_ALLW_END_DATE = "end_date"

TABLE_EMP_DEDUCTIONS = "employee_deductions"
COL_DED_ID = "deduction_id"
COL_DED_EMP_ID = "employee_id"
COL_DED_TYPE = "deduction_type"
COL_DED_AMOUNT = "amount"
COL_DED_IS_RECURRING = "is_recurring" # INTEGER (0 or 1)
COL_DED_EFF_DATE = "effective_date"
COL_DED_END_DATE = "end_date"

TABLE_SALARY_ADVANCES = "salary_advances"
COL_ADV_ID = "advance_id"
COL_ADV_EMP_ID = "employee_id"
COL_ADV_DATE = "advance_date"
COL_ADV_AMOUNT = "amount"
COL_ADV_REPAY_AMOUNT_PER_PERIOD = "repayment_amount_per_period"
COL_ADV_REPAY_START_DATE = "repayment_start_date"
COL_ADV_TOTAL_REPAID = "total_repaid_amount"
COL_ADV_STATUS = "status" # Active, Fully Repaid

TABLE_PAYSLIPS = "payslips"
COL_PAY_ID = "payslip_id"
COL_PAY_EMP_ID = "employee_id"
COL_PAY_PERIOD_START = "pay_period_start_date"
COL_PAY_PERIOD_END = "pay_period_end_date"
COL_PAY_BASIC_SALARY = "basic_salary"
COL_PAY_TOTAL_ALLOWANCES = "total_allowances"
COL_PAY_GROSS_SALARY = "gross_salary"
COL_PAY_TOTAL_DEDUCTIONS = "total_deductions"
COL_PAY_ADVANCE_REPAYMENT = "advance_repayment_deducted"
COL_PAY_NET_PAY = "net_pay"
COL_PAY_GENERATION_DATE = "generation_date"
COL_PAY_NOTES = "notes"

TABLE_CONTRACTS = "contracts"
COL_CONTRACT_ID = "contract_id"
COL_CONTRACT_EMP_ID = "employee_id"
COL_CONTRACT_DOC_ID = "document_id" # FK to employee_documents
COL_CONTRACT_TYPE = "contract_type"
COL_CONTRACT_START_DATE = "start_date"
COL_CONTRACT_INITIAL_DURATION_YEARS = "initial_duration_years"
COL_CONTRACT_CURRENT_END_DATE = "current_end_date"
COL_CONTRACT_IS_AUTO_RENEWABLE = "is_auto_renewable" # INTEGER (0 or 1)
COL_CONTRACT_RENEWAL_TERM_YEARS = "renewal_term_years"
COL_CONTRACT_NOTICE_PERIOD_DAYS = "notice_period_days"
COL_CONTRACT_LIFECYCLE_STATUS = "lifecycle_status" # Draft, Active, Expired, Terminated, Upcoming Renewal
COL_CONTRACT_APPROVAL_STATUS = "approval_status" # Pending Approval, Approved, Rejected
COL_CONTRACT_ASSIGNED_APPROVER_USER_ID = "assigned_approver_user_id"
COL_CONTRACT_APPROVAL_COMMENTS = "approval_comments"
COL_CONTRACT_APPROVAL_PROCESSED_BY_USER_ID = "approval_processed_by_user_id"
COL_CONTRACT_APPROVAL_PROCESSED_DATE = "approval_processed_date"
COL_CONTRACT_CUSTOM_TERMS = "custom_terms_from_form"
COL_CONTRACT_CREATED_AT = "created_at"
COL_CONTRACT_UPDATED_AT = "updated_at"
COL_CONTRACT_POSITION = "position_at_signing" # Store position at time of contract
COL_CONTRACT_SALARY = "salary_at_signing"   # Store salary at time of contract

TABLE_CONTRACT_SIGNATURES = "contract_signatures"
COL_CS_ID = "contract_sig_id"
COL_CS_DOC_ID = "doc_id" # FK to employee_documents
COL_CS_SIGNER_EMP_ID = "signer_employee_id"
COL_CS_SIGNER_USER_ID = "signer_user_id"
COL_CS_SIGNATURE_IMAGE_PATH = "signature_image_path"
COL_CS_SIGNING_TIMESTAMP = "signing_timestamp"
COL_CS_SIGNING_NOTES = "signing_notes"

TABLE_INTERVIEWS = "interviews"
COL_INT_ID = "interview_id"
COL_INT_CANDIDATE_NAME = "candidate_name"
COL_INT_INTERVIEWER_EMP_ID = "interviewer_employee_id"
COL_INT_DATE = "interview_date"
COL_INT_TIME = "interview_time"
COL_INT_DURATION_MINUTES = "duration_minutes"
COL_INT_LOCATION = "location"
COL_INT_STATUS = "status" # Scheduled, Completed, Cancelled, Rescheduled
COL_INT_NOTES = "notes"
COL_INT_CREATED_AT = "created_at"
COL_INT_UPDATED_AT = "updated_at"

TABLE_EMPLOYEE_TASKS = "employee_tasks"
COL_TASK_ID = "task_id"
COL_TASK_ASSIGNED_TO_EMP_ID = "assigned_to_emp_id"
COL_TASK_ASSIGNED_BY_USER_ID = "assigned_by_user_id"
COL_TASK_MONITOR_USER_ID = "monitor_user_id"
COL_TASK_CREATED_AT = "created_at"

# --- Attendance Policy, Instant Status, and Smart Alerts Settings ---
# These are keys for the app_settings table
SETTING_ENABLE_INSTANT_LATENESS_DISPLAY = "enable_instant_lateness_display"
# SETTING_ATTENDANCE_GRACE_PERIOD_MINUTES = "attendance_grace_period_minutes" # Using existing SETTING_LATE_ARRIVAL_ALLOWED_MINUTES

# Smart Alerts - Absence
SETTING_ENABLE_ABSENCE_ALERT = "enable_absence_alert"
SETTING_ABSENCE_ALERT_CUTOFF_TIME = "absence_alert_cutoff_time"
SETTING_ABSENCE_ALERT_TELEGRAM_CHAT_ID = "absence_alert_telegram_chat_id"

# Smart Alerts - Repeated Lateness
SETTING_ENABLE_REPEATED_LATENESS_ALERT = "enable_repeated_lateness_alert"
SETTING_LATENESS_ALERT_THRESHOLD_COUNT = "lateness_alert_threshold_count"
SETTING_LATENESS_ALERT_PERIOD_DAYS = "lateness_alert_period_days"
SETTING_REPEATED_LATENESS_ALERT_TELEGRAM_CHAT_ID = "repeated_lateness_alert_telegram_chat_id"

# --- Task Constants ---
TABLE_EMPLOYEE_TASKS = "employee_tasks"
COL_TASK_TITLE = "task_title"
COL_TASK_DESCRIPTION = "task_description"
COL_TASK_CREATION_DATE = "creation_date"
COL_TASK_DUE_DATE = "due_date"
COL_TASK_STATUS = "status" # To Do, In Progress, Completed, Blocked, Cancelled
COL_TASK_PRIORITY = "priority" # High, Medium, Low
COL_TASK_COMPLETION_DATE = "completion_date"
COL_TASK_NOTES = "notes"

# --- Training & Development Module Tables ---
TABLE_TRAINING_COURSES = "training_courses"
COL_COURSE_ID = "course_id"
COL_COURSE_NAME = "course_name"
COL_COURSE_DESCRIPTION = "description"
COL_COURSE_PROVIDER = "provider" # e.g., Internal, Udemy, Coursera
COL_COURSE_DEFAULT_DURATION_HOURS = "default_duration_hours" # Estimated/typical duration

TABLE_SKILLS = "skills"
COL_SKILL_ID = "skill_id"
COL_SKILL_NAME = "skill_name"
COL_SKILL_DESCRIPTION = "skill_description"
COL_SKILL_CATEGORY = "skill_category" # e.g., Technical, Soft Skill, Language

TABLE_EMPLOYEE_SKILLS = "employee_skills"
COL_EMP_SKILL_EMP_ID = "employee_id" # FK to employees
COL_EMP_SKILL_SKILL_ID = "skill_id" # FK to skills
COL_EMP_SKILL_PROFICIENCY_LEVEL = "proficiency_level" # e.g., Beginner, Intermediate, Advanced, Expert or 1-5 scale
COL_EMP_SKILL_ACQUISITION_DATE = "acquisition_date" # Date skill was formally recognized/acquired

# --- Status & Role Constants ---
STATUS_ACTIVE = "Active"
STATUS_TERMINATED = "Terminated"
STATUS_ON_LEAVE = "On Leave"
STATUS_SUSPENDED = "Suspended"
VALID_EMPLOYEE_STATUSES = [STATUS_ACTIVE, STATUS_TERMINATED, STATUS_ON_LEAVE, STATUS_SUSPENDED]

# --- Leave Status Constants ---
STATUS_LEAVE_PENDING_APPROVAL = "Pending Approval"
STATUS_LEAVE_APPROVED = "Approved"
STATUS_LEAVE_REJECTED = "Rejected"
STATUS_LEAVE_CANCELLED = "Cancelled"

ROLE_ADMIN = "Admin"
ROLE_DEPT_MANAGER = "Department Manager"
ROLE_EMPLOYEE = "Employee"
VALID_ROLES = [ROLE_ADMIN, ROLE_DEPT_MANAGER, ROLE_EMPLOYEE]

VALID_TASK_STATUSES = ["To Do", "In Progress", "Completed", "Blocked", "Cancelled"]
VALID_TASK_PRIORITIES = ["High", "Medium", "Low"]
VALID_INTERVIEW_STATUSES = ["Scheduled", "Completed", "Cancelled", "Rescheduled by Candidate", "Rescheduled by Company", "No Show"]
VALID_CONTRACT_TYPES = ["Permanent", "Temporary", "Trial", "Seasonal", "Freelance/Independent"]
VALID_CONTRACT_LIFECYCLE_STATUSES = ["Draft", "Active", "Expired", "Terminated", "Upcoming Renewal"]
VALID_CONTRACT_APPROVAL_STATUSES = ["Pending Approval", "Approved", "Rejected"]

# --- App Counter Names ---
COUNTER_NEXT_EMPLOYEE_ID = "next_employee_id"
COUNTER_TELEGRAM_NOTIFS_SENT = "telegram_notifications_sent"
COUNTER_CONTRACTS_SIGNED_ELECTRONICALLY = "contracts_signed_electronically"
COUNTER_REPORTS_GENERATED_PDF = "reports_generated_pdf"
COUNTER_REPORTS_GENERATED_EXCEL = "reports_generated_excel"

# --- App Setting Keys ---
SETTING_DEFAULT_LANGUAGE = "default_language"
SETTING_DEFAULT_THEME = "default_theme" # For ttkbootstrap theme name (e.g., "cosmo", "darkly") or our logical "light"/"dark"
SETTING_TELEGRAM_BOT_TOKEN = "telegram_bot_token"
SETTING_TELEGRAM_CHAT_ID = "telegram_chat_id"
SETTING_ZKTECO_DEVICE_IP = "zkteco_device_ip"
SETTING_ZKTECO_DEVICE_PORT = "zkteco_device_port"
SETTING_ZKTECO_TIMEOUT = "zkteco_timeout" # New setting key
SETTING_AUTO_BACKUP_ENABLED = "auto_backup_enabled"
SETTING_AUTO_BACKUP_FREQUENCY = "auto_backup_frequency" # Daily, Weekly, Monthly
SETTING_DEFAULT_ANNUAL_LEAVE_DAYS = "default_annual_leave_days"
SETTING_VACATION_ACCUMULATION_POLICY = "vacation_accumulation_policy" # e.g., "None", "MaxDays:30"
SETTING_LEAVE_BUSY_THRESHOLD_PERCENT_DEPT = "leave_busy_threshold_percent_dept"
SETTING_PUBLIC_HOLIDAYS_LIST = "public_holidays_list" # Comma-separated YYYY-MM-DD
SETTING_AUTO_WEEKLY_STATS_ENABLED = "auto_weekly_stats_enabled"
SETTING_AUTO_WEEKLY_STATS_DAY = "auto_weekly_stats_day" # e.g., "Monday"
SETTING_DEFAULT_DEDUCTION_RATE = "default_deduction_rate" # Added
SETTING_DEFAULT_BONUS_RATE = "default_bonus_rate"       # Added
SETTING_AUTO_WEEKLY_STATS_TIME = "auto_weekly_stats_time" # e.g., "09:00"
SETTING_LATE_ARRIVAL_NOTIFICATION_TIME = "late_arrival_notification_time" # e.g., "09:15:00"
SETTING_DEFAULT_CONTRACT_APPROVER_USER_ID = "default_contract_approver_user_id"
SETTING_DEFAULT_LEAVE_APPROVER_USER_ID = "default_leave_approver_user_id"
SETTING_STANDARD_START_TIME = "standard_start_time" # New: Official work start time (HH:MM:SS)
SETTING_GCAL_SYNC_INTERVIEWS = "gcal_sync_interviews" # Boolean (0 or 1)
SETTING_GCAL_SYNC_VACATIONS = "gcal_sync_vacations"   # Boolean (0 or 1)

SETTING_STANDARD_WORK_HOURS_PER_DAY = "standard_work_hours_per_day"
SETTING_STANDARD_END_TIME = "standard_end_time" # New: Official work end time (HH:MM:SS)
SETTING_WORK_DAYS_INDICES = "work_days_indices" # Comma-separated integers (0=Mon)
SETTING_LATE_ARRIVAL_ALLOWED_MINUTES = "late_arrival_allowed_minutes"
SETTING_LATE_ARRIVAL_PENALTY_TYPE = "late_arrival_penalty_type" # None, Fixed, Percentage
SETTING_LATE_ARRIVAL_PENALTY_AMOUNT = "late_arrival_penalty_amount" # Value for fixed/percentage
SETTING_MAX_VACATION_CARRY_OVER_DAYS = "max_vacation_carry_over_days"
SETTING_VACATION_CALCULATION_METHOD = "vacation_calculation_method" # Fixed Annual Allocation, Monthly Accrual
SETTING_MIN_UNEXCUSED_ABSENCE_DAYS_FOR_ALERT = "min_unexcused_absence_days_for_alert" # New
SETTING_STANDARD_LUNCH_BREAK_MINUTES = "standard_lunch_break_minutes" # New

# --- UI Style Constants (Bootstyle names) ---
BS_ADD = "success"
BS_VIEW_EDIT = "info"
BS_DELETE_FINISH = "danger"
BS_NEUTRAL = "secondary"
BS_LIGHT = "light"
BS_PRIMARY_ACTION = "primary"

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

COL_TASK_MONITOR_USER_ID = "monitor_user_id"
COL_TASK_CREATION_DATE = "creation_date"
COL_TASK_COMPLETION_DATE = "completion_date"

# Constants for specific counter names
COUNTER_EMPLOYEES_ADDED = "employees_added"

def init_db():
    """Initializes the database with all necessary tables and default data."""
    conn = None
    try:
        conn = sqlite3.connect(config.DATABASE_NAME)
        cursor = conn.cursor()

        # Enable Foreign Keys
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Create Tables (Order matters due to foreign keys)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_DEPARTMENTS} (
                {COL_DEPT_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_DEPT_NAME} TEXT UNIQUE NOT NULL,
                {COL_DEPT_DESCRIPTION} TEXT
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEES} (
                {COL_EMP_ID} TEXT PRIMARY KEY,
                {COL_EMP_NAME} TEXT NOT NULL,
                {COL_EMP_DEPARTMENT_ID} INTEGER,
                {COL_EMP_POSITION} TEXT,
                {COL_EMP_SALARY} REAL,
                {COL_EMP_VACATION_DAYS} INTEGER DEFAULT 0,
                {COL_EMP_STATUS} TEXT DEFAULT '{STATUS_ACTIVE}',
                {COL_EMP_TERMINATION_DATE} TEXT,
                {COL_EMP_START_DATE} TEXT,
                {COL_EMP_PHONE} TEXT,
                {COL_EMP_EMAIL} TEXT,
                {COL_EMP_PHOTO_PATH} TEXT,
                {COL_EMP_GENDER} TEXT,
                {COL_EMP_MARITAL_STATUS} TEXT,
                {COL_EMP_EDUCATION} TEXT,
                {COL_EMP_EMPLOYMENT_HISTORY} TEXT,
                {COL_EMP_DEVICE_USER_ID} TEXT UNIQUE,
                {COL_EMP_CURRENT_SHIFT} TEXT DEFAULT 'Morning',
                {COL_EMP_MANAGER_ID} TEXT,
                {COL_EMP_EXCLUDE_VACATION_POLICY} INTEGER DEFAULT 0,
                {COL_EMP_IS_ARCHIVED} INTEGER DEFAULT 0,
                {COL_EMP_ARCHIVED_DATE} TEXT,
                FOREIGN KEY ({COL_EMP_DEPARTMENT_ID}) REFERENCES {TABLE_DEPARTMENTS}({COL_DEPT_ID}) ON DELETE SET NULL,
                FOREIGN KEY ({COL_EMP_MANAGER_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE SET NULL
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_USERS} (
                {COL_USER_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_USER_USERNAME} TEXT UNIQUE NOT NULL,
                {COL_USER_PASSWORD_HASH} TEXT NOT NULL,
                {COL_USER_ROLE} TEXT NOT NULL,
                {COL_USER_LINKED_EMP_ID} TEXT UNIQUE,
                FOREIGN KEY ({COL_USER_LINKED_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE SET NULL
            )
        """)

        # --- Create Contracts Table ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CONTRACTS} (
                {COL_CONTRACT_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_CONTRACT_EMP_ID} TEXT NOT NULL,
                {COL_CONTRACT_DOC_ID} INTEGER, -- FK to employee_documents (the PDF file)
                {COL_CONTRACT_TYPE} TEXT NOT NULL, -- From VALID_CONTRACT_TYPES
                {COL_CONTRACT_START_DATE} TEXT NOT NULL, -- YYYY-MM-DD
                {COL_CONTRACT_INITIAL_DURATION_YEARS} INTEGER, -- Integer
                {COL_CONTRACT_CURRENT_END_DATE} TEXT, -- YYYY-MM-DD, updated on renewal
                {COL_CONTRACT_IS_AUTO_RENEWABLE} INTEGER DEFAULT 0, -- INTEGER (0 or 1)
                {COL_CONTRACT_RENEWAL_TERM_YEARS} INTEGER, -- Integer, how long it renews for
                {COL_CONTRACT_NOTICE_PERIOD_DAYS} INTEGER, -- Integer
                {COL_CONTRACT_LIFECYCLE_STATUS} TEXT NOT NULL DEFAULT 'Draft', -- TEXT: Draft, Active, Expired, Terminated, Upcoming Renewal
                {COL_CONTRACT_APPROVAL_STATUS} TEXT NOT NULL DEFAULT 'Pending Approval', -- TEXT: Pending Approval, Approved, Rejected
                {COL_CONTRACT_ASSIGNED_APPROVER_USER_ID} INTEGER, -- INTEGER, FK to users
                {COL_CONTRACT_APPROVAL_COMMENTS} TEXT, -- TEXT
                {COL_CONTRACT_APPROVAL_PROCESSED_BY_USER_ID} INTEGER, -- INTEGER, FK to users
                {COL_CONTRACT_APPROVAL_PROCESSED_DATE} TEXT, -- TEXT
                {COL_CONTRACT_CUSTOM_TERMS} TEXT, -- TEXT
                {COL_CONTRACT_CREATED_AT} TEXT NOT NULL,
                {COL_CONTRACT_UPDATED_AT} TEXT NOT NULL,
                {COL_CONTRACT_POSITION} TEXT, -- Store position at time of contract
                {COL_CONTRACT_SALARY} REAL,   -- Store salary at time of contract
                FOREIGN KEY ({COL_CONTRACT_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_CONTRACT_DOC_ID}) REFERENCES {TABLE_EMPLOYEE_DOCUMENTS}({COL_DOC_ID}) ON DELETE SET NULL,
                FOREIGN KEY ({COL_CONTRACT_ASSIGNED_APPROVER_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL,
                FOREIGN KEY ({COL_CONTRACT_APPROVAL_PROCESSED_BY_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL
            )
        """)

        # --- Create Contract Signatures Table ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CONTRACT_SIGNATURES} (
                {COL_CS_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_CS_DOC_ID} INTEGER NOT NULL, -- FK to employee_documents
                {COL_CS_SIGNER_EMP_ID} TEXT, -- FK to employees (if employee signs)
                {COL_CS_SIGNER_USER_ID} INTEGER, -- FK to users (if user/manager signs)
                {COL_CS_SIGNATURE_IMAGE_PATH} TEXT, -- Path to the image file for THIS signing event
                {COL_CS_SIGNING_TIMESTAMP} TEXT NOT NULL,
                {COL_CS_SIGNING_NOTES} TEXT, -- e.g., "Signed by Employee", "Signed by HR Manager"
                FOREIGN KEY ({COL_CS_DOC_ID}) REFERENCES {TABLE_EMPLOYEE_DOCUMENTS}({COL_DOC_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_CS_SIGNER_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE SET NULL,
                FOREIGN KEY ({COL_CS_SIGNER_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL
            )
        """)

        # Add all other CREATE TABLE statements here, following the structure from the monolithic file
        # For brevity, I'm showing a few more. Ensure all tables are created.

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_ATTENDANCE_LOG} (
                {COL_ATT_LOG_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_ATT_EMP_ID} TEXT NOT NULL,
                {COL_ATT_CLOCK_IN} TEXT NOT NULL,
                {COL_ATT_CLOCK_OUT} TEXT,
                {COL_ATT_LOG_DATE} TEXT NOT NULL,
                {COL_ATT_SOURCE} TEXT,
                {COL_ATT_NOTES} TEXT,
                FOREIGN KEY ({COL_ATT_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_INTERVIEWS} (
                {COL_INT_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_INT_CANDIDATE_NAME} TEXT NOT NULL,
                {COL_INT_INTERVIEWER_EMP_ID} TEXT,
                {COL_INT_DATE} TEXT NOT NULL,
                {COL_INT_TIME} TEXT NOT NULL,
                {COL_INT_DURATION_MINUTES} INTEGER,
                {COL_INT_LOCATION} TEXT,
                {COL_INT_STATUS} TEXT,
                {COL_INT_NOTES} TEXT,
                {COL_INT_CREATED_AT} TEXT,
                {COL_INT_UPDATED_AT} TEXT,
                FOREIGN KEY ({COL_INT_INTERVIEWER_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE SET NULL
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_LEAVE_REQUESTS} (
                {COL_LR_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_LR_EMP_ID} TEXT NOT NULL,
                {COL_LR_LEAVE_TYPE} TEXT NOT NULL,
                {COL_LR_START_DATE} TEXT NOT NULL,
                {COL_LR_END_DATE} TEXT NOT NULL,
                {COL_LR_REASON} TEXT,
                {COL_LR_REQUEST_DATE} TEXT NOT NULL,
                {COL_LR_STATUS} TEXT NOT NULL,
                {COL_LR_ASSIGNED_APPROVER_USER_ID} INTEGER,
                {COL_LR_PROCESSED_BY_USER_ID} INTEGER,
                {COL_LR_APPROVER_COMMENTS} TEXT,
                {COL_LR_PROCESSED_DATE} TEXT,
                FOREIGN KEY ({COL_LR_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_LR_ASSIGNED_APPROVER_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL,
                FOREIGN KEY ({COL_LR_PROCESSED_BY_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL
            )
        """)
        
        # --- Create App Settings Table ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_APP_SETTINGS} (
                {COL_SETTING_KEY} TEXT PRIMARY KEY,
                {COL_SETTING_VALUE} TEXT
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEE_DOCUMENTS} (
                {COL_DOC_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_DOC_EMP_ID} TEXT NOT NULL,
                {COL_DOC_TYPE} TEXT NOT NULL,
                {COL_DOC_FILE_PATH} TEXT NOT NULL UNIQUE,
                {COL_DOC_UPLOAD_DATE} TEXT NOT NULL,
                {COL_DOC_NOTES} TEXT,
                FOREIGN KEY ({COL_DOC_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE
            )
        """)

        # ... (Include CREATE TABLE for ALL other tables like TABLE_EMPLOYEE_DOCUMENTS, 
        # TABLE_APP_COUNTERS, TABLE_EVALUATION_CRITERIA, etc. if they are missing)
        # For example, TABLE_APP_COUNTERS:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_APP_COUNTERS} (
                {COL_COUNTER_NAME} TEXT PRIMARY KEY,
                {COL_COUNTER_VALUE} INTEGER
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEE_TASKS} (
                {COL_TASK_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_TASK_ASSIGNED_TO_EMP_ID} TEXT NOT NULL,
                {COL_TASK_ASSIGNED_BY_USER_ID} INTEGER NOT NULL,
                {COL_TASK_MONITOR_USER_ID} INTEGER,
                {COL_TASK_TITLE} TEXT NOT NULL,
                {COL_TASK_DESCRIPTION} TEXT,
                {COL_TASK_CREATION_DATE} TEXT NOT NULL,
                {COL_TASK_DUE_DATE} TEXT,
                {COL_TASK_STATUS} TEXT NOT NULL,
                {COL_TASK_PRIORITY} TEXT NOT NULL,
                {COL_TASK_COMPLETION_DATE} TEXT,
                {COL_TASK_NOTES} TEXT,
                FOREIGN KEY ({COL_TASK_ASSIGNED_TO_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_TASK_ASSIGNED_BY_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_TASK_MONITOR_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL
            )
        """)

        # --- Create Evaluation Related Tables ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EVALUATION_CRITERIA} (
                {COL_CRITERIA_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_CRITERIA_NAME} TEXT UNIQUE NOT NULL,
                {COL_CRITERIA_DESCRIPTION} TEXT,
                {COL_CRITERIA_MAX_POINTS} INTEGER DEFAULT 10
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEE_EVALUATIONS} (
                {COL_EVAL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_EVAL_EMP_ID} TEXT NOT NULL,
                {COL_EVAL_PERIOD} TEXT,
                {COL_EVAL_DATE} TEXT NOT NULL,
                {COL_EVAL_TOTAL_SCORE} REAL,
                {COL_EVAL_EVALUATOR_ID} INTEGER, 
                {COL_EVAL_COMMENTS} TEXT,
                FOREIGN KEY ({COL_EVAL_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_EVAL_EVALUATOR_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL 
            )
        """)
        # Note: COL_EVAL_EVALUATOR_ID was referencing employees table in monolithic, 
        # but it makes more sense to reference TABLE_USERS if evaluators are users.
        # If evaluators are other employees, then it should be:
        # FOREIGN KEY ({COL_EVAL_EVALUATOR_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE SET NULL

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EVALUATION_DETAILS} (
                {COL_EVAL_DETAIL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_EVAL_DETAIL_EVAL_ID} INTEGER NOT NULL,
                {COL_EVAL_DETAIL_CRITERIA_ID} INTEGER NOT NULL,
                {COL_EVAL_DETAIL_SCORE} REAL NOT NULL,
                {COL_EVAL_DETAIL_COMMENT} TEXT,
                FOREIGN KEY ({COL_EVAL_DETAIL_EVAL_ID}) REFERENCES {TABLE_EMPLOYEE_EVALUATIONS}({COL_EVAL_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_EVAL_DETAIL_CRITERIA_ID}) REFERENCES {TABLE_EVALUATION_CRITERIA}({COL_CRITERIA_ID}) ON DELETE RESTRICT
            )
        """)
        # Using ON DELETE RESTRICT for criteria to prevent deleting a criterion if it's used in an evaluation detail.
        # Alternatively, ON DELETE SET NULL or a different strategy could be used.


        # --- Create Payroll Related Tables ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMP_ALLOWANCES} (
                {COL_ALLW_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_ALLW_EMP_ID} TEXT NOT NULL,
                {COL_ALLW_TYPE} TEXT NOT NULL,
                {COL_ALLW_AMOUNT} REAL NOT NULL,
                {COL_ALLW_IS_RECURRING} INTEGER DEFAULT 0,
                {COL_ALLW_EFF_DATE} TEXT NOT NULL,
                {COL_ALLW_END_DATE} TEXT,
                FOREIGN KEY ({COL_ALLW_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMP_DEDUCTIONS} (
                {COL_DED_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_DED_EMP_ID} TEXT NOT NULL,
                {COL_DED_TYPE} TEXT NOT NULL,
                {COL_DED_AMOUNT} REAL NOT NULL,
                {COL_DED_IS_RECURRING} INTEGER DEFAULT 0,
                {COL_DED_EFF_DATE} TEXT NOT NULL,
                {COL_DED_END_DATE} TEXT,
                FOREIGN KEY ({COL_DED_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SALARY_ADVANCES} (
                {COL_ADV_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_ADV_EMP_ID} TEXT NOT NULL,
                {COL_ADV_DATE} TEXT NOT NULL,
                {COL_ADV_AMOUNT} REAL NOT NULL,
                {COL_ADV_REPAY_AMOUNT_PER_PERIOD} REAL NOT NULL,
                {COL_ADV_REPAY_START_DATE} TEXT NOT NULL,
                {COL_ADV_TOTAL_REPAID} REAL DEFAULT 0,
                {COL_ADV_STATUS} TEXT NOT NULL,
                FOREIGN KEY ({COL_ADV_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_PAYSLIPS} (
                {COL_PAY_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_PAY_EMP_ID} TEXT NOT NULL,
                {COL_PAY_PERIOD_START} TEXT NOT NULL,
                {COL_PAY_PERIOD_END} TEXT NOT NULL,
                {COL_PAY_BASIC_SALARY} REAL,
                {COL_PAY_TOTAL_ALLOWANCES} REAL,
                {COL_PAY_GROSS_SALARY} REAL,
                {COL_PAY_TOTAL_DEDUCTIONS} REAL,
                {COL_PAY_ADVANCE_REPAYMENT} REAL,
                {COL_PAY_NET_PAY} REAL,
                {COL_PAY_GENERATION_DATE} TEXT,
                {COL_PAY_NOTES} TEXT,
                FOREIGN KEY ({COL_PAY_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                UNIQUE ({COL_PAY_EMP_ID}, {COL_PAY_PERIOD_START}, {COL_PAY_PERIOD_END})
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEE_ACTION_LOG} (
                {COL_EAL_LOG_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_EAL_EMP_ID} TEXT NOT NULL,
                {COL_EAL_ACTION_DESC} TEXT NOT NULL,
                {COL_EAL_PERFORMED_BY_USER_ID} INTEGER,
                {COL_EAL_TIMESTAMP} TEXT NOT NULL,
                FOREIGN KEY ({COL_EAL_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_EAL_PERFORMED_BY_USER_ID}) REFERENCES {TABLE_USERS}({COL_USER_ID}) ON DELETE SET NULL
            )
        """)

        # --- Training Courses Table ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_TRAINING_COURSES} (
                {COL_COURSE_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_COURSE_NAME} TEXT UNIQUE NOT NULL,
                {COL_COURSE_DESCRIPTION} TEXT,
                {COL_COURSE_PROVIDER} TEXT,
                {COL_COURSE_DEFAULT_DURATION_HOURS} REAL
            )
        """)

        # --- Skills Table ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SKILLS} (
                {COL_SKILL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COL_SKILL_NAME} TEXT UNIQUE NOT NULL,
                {COL_SKILL_DESCRIPTION} TEXT,
                {COL_SKILL_CATEGORY} TEXT
            )
        """)

        # --- Employee Skills Table (Junction Table) ---
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_EMPLOYEE_SKILLS} (
                {COL_EMP_SKILL_EMP_ID} TEXT NOT NULL,
                {COL_EMP_SKILL_SKILL_ID} INTEGER NOT NULL,
                {COL_EMP_SKILL_PROFICIENCY_LEVEL} TEXT,
                {COL_EMP_SKILL_ACQUISITION_DATE} TEXT, -- YYYY-MM-DD
                PRIMARY KEY ({COL_EMP_SKILL_EMP_ID}, {COL_EMP_SKILL_SKILL_ID}),
                FOREIGN KEY ({COL_EMP_SKILL_EMP_ID}) REFERENCES {TABLE_EMPLOYEES}({COL_EMP_ID}) ON DELETE CASCADE,
                FOREIGN KEY ({COL_EMP_SKILL_SKILL_ID}) REFERENCES {TABLE_SKILLS}({COL_SKILL_ID}) ON DELETE RESTRICT
            )
        """)
        # --- Initialize App Counters ---
        cursor.execute(f"INSERT OR IGNORE INTO {TABLE_APP_COUNTERS} ({COL_COUNTER_NAME}, {COL_COUNTER_VALUE}) VALUES (?, ?)", (COUNTER_NEXT_EMPLOYEE_ID, 1))
        cursor.execute(f"INSERT OR IGNORE INTO {TABLE_APP_COUNTERS} ({COL_COUNTER_NAME}, {COL_COUNTER_VALUE}) VALUES (?, ?)", (COUNTER_TELEGRAM_NOTIFS_SENT, 0))
        # Add other counters

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_APP_COUNTERS} (
                {COL_COUNTER_NAME} TEXT PRIMARY KEY,
                {COL_COUNTER_VALUE} INTEGER DEFAULT 0
            )
        """)
       
        # --- Initialize Default App Settings ---
        
        default_settings = {
            SETTING_DEFAULT_LANGUAGE: "en",
            SETTING_DEFAULT_THEME: "light", # This is the logical theme for the app
            SETTING_TELEGRAM_BOT_TOKEN: config.TELEGRAM_BOT_TOKEN,
            SETTING_TELEGRAM_CHAT_ID: config.TELEGRAM_CHAT_ID,
            SETTING_ZKTECO_DEVICE_IP: config.ZKTECO_DEVICE_IP,
            SETTING_ZKTECO_DEVICE_PORT: str(config.ZKTECO_DEVICE_PORT),
            SETTING_ZKTECO_TIMEOUT: str(config.ZKTECO_TIMEOUT), # Add new setting to defaults
            SETTING_AUTO_BACKUP_ENABLED: "false",
            SETTING_AUTO_BACKUP_FREQUENCY: "Weekly",
            SETTING_DEFAULT_ANNUAL_LEAVE_DAYS: "21",
            SETTING_VACATION_ACCUMULATION_POLICY: "None",
            SETTING_LEAVE_BUSY_THRESHOLD_PERCENT_DEPT: "30",
            SETTING_PUBLIC_HOLIDAYS_LIST: "",
            SETTING_AUTO_WEEKLY_STATS_ENABLED: "false",
            SETTING_AUTO_WEEKLY_STATS_DAY: "Monday",
            SETTING_AUTO_WEEKLY_STATS_TIME: "09:00",
            SETTING_LATE_ARRIVAL_NOTIFICATION_TIME: config.STANDARD_START_TIME_CONFIG_DEFAULT,
            SETTING_DEFAULT_CONTRACT_APPROVER_USER_ID: "1", # Assuming user ID 1 is an admin/manager
            SETTING_DEFAULT_LEAVE_APPROVER_USER_ID: "1",   # Assuming user ID 1 is an admin/manager
            SETTING_DEFAULT_DEDUCTION_RATE: "0.0", # Added default
            SETTING_DEFAULT_BONUS_RATE: "0.0",      # Added default
            SETTING_STANDARD_START_TIME: config.STANDARD_START_TIME_CONFIG_DEFAULT, # New
            SETTING_STANDARD_WORK_HOURS_PER_DAY: str(config.STANDARD_WORK_HOURS_PER_DAY),
            SETTING_WORK_DAYS_INDICES: config.DEFAULT_WORK_DAYS_INDICES_STR,
            SETTING_LATE_ARRIVAL_ALLOWED_MINUTES: str(config.LATE_ARRIVAL_ALLOWED_MINUTES),
            SETTING_LATE_ARRIVAL_PENALTY_TYPE: config.LATE_ARRIVAL_PENALTY_TYPE,
            SETTING_LATE_ARRIVAL_PENALTY_AMOUNT: str(config.LATE_ARRIVAL_PENALTY_AMOUNT),
            SETTING_STANDARD_LUNCH_BREAK_MINUTES: str(config.STANDARD_LUNCH_BREAK_MINUTES_CONFIG_DEFAULT), # New
            SETTING_MIN_UNEXCUSED_ABSENCE_DAYS_FOR_ALERT: str(config.MIN_UNEXCUSED_ABSENCE_DAYS_FOR_ALERT_CONFIG_DEFAULT), # New
            SETTING_MAX_VACATION_CARRY_OVER_DAYS: str(config.MAX_VACATION_CARRY_OVER_DAYS),
            SETTING_VACATION_CALCULATION_METHOD: config.VACATION_CALCULATION_METHOD,
        }
        for key, value in default_settings.items():
            cursor.execute(f"INSERT OR IGNORE INTO {TABLE_APP_SETTINGS} ({COL_SETTING_KEY}, {COL_SETTING_VALUE}) VALUES (?, ?)", (key, value))
            # Initialize Calendar Sync Settings
            cursor.execute(f"INSERT OR IGNORE INTO {TABLE_APP_SETTINGS} ({COL_SETTING_KEY}, {COL_SETTING_VALUE}) VALUES (?, ?)",
                       (SETTING_GCAL_SYNC_INTERVIEWS, "0")) # Default to off
            cursor.execute(f"INSERT OR IGNORE INTO {TABLE_APP_SETTINGS} ({COL_SETTING_KEY}, {COL_SETTING_VALUE}) VALUES (?, ?)",
                       (SETTING_GCAL_SYNC_VACATIONS, "0")) # Default to off

        # --- Create Default Admin User (if not exists) ---
        cursor.execute(f"SELECT {COL_USER_ID} FROM {TABLE_USERS} WHERE {COL_USER_USERNAME} = 'admin'")
        if not cursor.fetchone():
            hashed_password = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
            cursor.execute(f"INSERT INTO {TABLE_USERS} ({COL_USER_USERNAME}, {COL_USER_PASSWORD_HASH}, {COL_USER_ROLE}) VALUES (?, ?, ?)",
                           ('admin', hashed_password.decode('utf-8'), ROLE_ADMIN))
            logger.info("Default admin user created.")

        conn.commit()
        logger.info("Database initialized/verified successfully.")

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise # Re-raise the exception to be caught by main.py
    finally:
        if conn:
            conn.close()

def get_app_setting_db(setting_key: str, default_value: Optional[str] = None) -> Optional[str]: # Ensure default_value is present
    """Retrieves an application setting from the database."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {COL_SETTING_VALUE} FROM {TABLE_APP_SETTINGS} WHERE {COL_SETTING_KEY} = ?", (setting_key,))
            row = cursor.fetchone()
            return row[0] if row else default_value # Use default_value if row is None
    except sqlite3.Error as e:
        logger.error(f"Error fetching app setting '{setting_key}': {e}. Returning default: {default_value}")
        return default_value

def set_app_setting_db(setting_key: str, setting_value: str) -> bool:
    """Sets or updates an application setting in the database."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Use INSERT OR REPLACE to handle both new and existing settings
            cursor.execute(f"INSERT OR REPLACE INTO {TABLE_APP_SETTINGS} ({COL_SETTING_KEY}, {COL_SETTING_VALUE}) VALUES (?, ?)",
                           (setting_key, setting_value))
            conn.commit()
            logger.info(f"App setting '{setting_key}' set to '{setting_value}'.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Error setting app setting '{setting_key}': {e}")
        return False

def increment_app_counter(counter_name: str, increment_by: int = 1):
    """Increments a specific application counter in the database."""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {TABLE_APP_COUNTERS} ({COL_COUNTER_NAME}, {COL_COUNTER_VALUE})
                VALUES (?, ?)
                ON CONFLICT({COL_COUNTER_NAME}) DO UPDATE SET {COL_COUNTER_VALUE} = {COL_COUNTER_VALUE} + excluded.{COL_COUNTER_VALUE};
            """, (counter_name, increment_by))
            conn.commit()
        logger.info(f"App counter '{counter_name}' incremented by {increment_by}.")
    except sqlite3.Error as e:
        logger.error(f"Database error incrementing app counter '{counter_name}': {e}")
        # Optionally re-raise a custom error or handle as appropriate

if __name__ == '__main__': # pragma: no cover
    # This allows running this script directly to initialize the DB
    # (e.g., python -m data.database)
    print("Initializing database directly...")
    init_db()
    print("Database initialization complete.")
    # Example: Set a setting
    # set_app_setting_db("test_setting", "test_value")
    # print(f"Test setting value: {get_app_setting_db('test_setting')}")
