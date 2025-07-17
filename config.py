# config.py
import configparser
import os
from dotenv import load_dotenv
import logging # Use logging for config messages

logger = logging.getLogger(__name__)

CONFIG_FILE = "settings.ini"
DEFAULT_CONFIG = {
    "Database": {
        "name": "hr_system.db",
        "backup_dir": "db_backups",
    },
    "ZKTeco": {
        "device_ip": "192.168.1.201",
        "device_port": "4370",
        "timeout": "10", # Default timeout in seconds
    },
    "Telegram": {
        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE", # Placeholder
        "chat_id": "YOUR_TELEGRAM_CHAT_ID_HERE",   # Placeholder
    },
    "WorkSchedule": {
        "default_work_days_indices": "0,1,2,3,4", # Mon-Fri
        "standard_start_time": "09:00:00", # Renamed for clarity and will be a DB setting
        "standard_end_time": "17:00:00", # New default end time
        "standard_work_hours_per_day": "8.0", # Renamed for clarity
        "overtime_rate_multiplier": "1.5",
# "late_arrival_notification_time": "08:00:00", # Moved to DB settings
        # Instant Status & Smart Alerts Defaults
        "enable_instant_lateness_display": "True",
        "enable_absence_alert": "True",
        "absence_alert_cutoff_time": "09:30:00",
        "absence_alert_telegram_chat_id": "", # Empty means use global chat_id from Telegram section
        "enable_repeated_lateness_alert": "True",
        "lateness_alert_threshold_count": "3",
        "lateness_alert_period_days": "7",
        "repeated_lateness_alert_telegram_chat_id": "",
        "late_arrival_allowed_minutes": "15",
        "late_arrival_penalty_type": "None", # Options: None, Fixed, Percentage
        "standard_lunch_break_minutes": "60", # New setting for lunch break
        "late_arrival_penalty_amount": "0", # Amount or Percentage value
        "min_unexcused_absence_days_for_alert": "1", # New setting
        "max_vacation_carry_over_days": "5",
        "vacation_calculation_method": "Fixed Annual Allocation", # Options: Fixed Annual Allocation, Monthly Accrual
    },
    "General": {
        "employee_id_prefix": "EMP",
        "documents_base_dir": "employee_documents",
    },
    "Appearance": { # This default_theme is the ttkbootstrap theme name
        # The application logic maps "light"/"dark" from settings to these.
        "default_theme": "litera"
    },
    "CompanyDetails": {
        "company_name_for_reports": "Your Company Name LLC",
        "company_registration_country": "Your Country",
        "company_address_for_reports": "123 Main Street, Your City, Your Country"
    },
    "Development": {"debug_mode": "False"} # Added debug_mode
}

config = configparser.ConfigParser()

def load_config():
    """Loads configuration from file, creating a default if not found."""
    if not os.path.exists(CONFIG_FILE):
        logger.info(f"Configuration file '{CONFIG_FILE}' not found. Creating default.")
        create_default_config()
    
    try:
        config.read(CONFIG_FILE)
        logger.info(f"Configuration loaded from '{CONFIG_FILE}'.")
    except configparser.Error as e:
        logger.error(f"Error reading configuration file '{CONFIG_FILE}': {e}. Using defaults for affected values.")
        # Optionally, re-create default config or handle more gracefully

def create_default_config():
    """Creates a default configuration file."""
    temp_config = configparser.ConfigParser()
    for section, options in DEFAULT_CONFIG.items():
        temp_config[section] = options
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            temp_config.write(configfile)
        logger.info(f"Created default configuration file: {CONFIG_FILE}")
    except IOError as e:
        logger.error(f"Could not write default configuration file '{CONFIG_FILE}': {e}")

# Load configuration when this module is imported
load_config()
# Load environment variables from .env file if it exists
load_dotenv()
# --- Getter functions ---
def get_setting(section, key, fallback_type=str):
    """Generic getter with type conversion and fallback."""
    default_value = DEFAULT_CONFIG.get(section, {}).get(key)
    try:
        if fallback_type == int:
            return config.getint(section, key, fallback=int(default_value) if default_value is not None else None)
        elif fallback_type == float:
            return config.getfloat(section, key, fallback=float(default_value) if default_value is not None else None)
        elif fallback_type == bool:
            return config.getboolean(section, key) # Fallback handled by configparser
        return config.get(section, key, fallback=default_value)
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.warning(f"Config option '{key}' in section '{section}' not found. Falling back to default: {default_value}")
        if default_value is None: return None
        return fallback_type(default_value) if callable(fallback_type) else default_value # Ensure fallback_type is callable for str, int, float
    except ValueError as e:
        logger.error(f"Config value error for '{section}.{key}': {e}. Falling back to default: {default_value}")
        if default_value is None: return None
        return fallback_type(default_value) if callable(fallback_type) else default_value



DATABASE_NAME = get_setting("Database", "name")
BACKUP_DIR = get_setting("Database", "backup_dir")

ZKTECO_DEVICE_IP = get_setting("ZKTeco", "device_ip")
ZKTECO_DEVICE_PORT = get_setting("ZKTeco", "device_port", fallback_type=int)
ZKTECO_TIMEOUT = get_setting("ZKTeco", "timeout", fallback_type=int)

# For sensitive data, prioritize environment variables
TELEGRAM_BOT_TOKEN_ENV = os.environ.get("HR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID_ENV = os.environ.get("HR_TELEGRAM_CHAT_ID")

TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN_ENV if TELEGRAM_BOT_TOKEN_ENV else get_setting("Telegram", "bot_token")
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID_ENV if TELEGRAM_CHAT_ID_ENV else get_setting("Telegram", "chat_id")

DEFAULT_WORK_DAYS_INDICES_STR = get_setting("WorkSchedule", "default_work_days_indices")
DEFAULT_WORK_DAYS_INDICES = [int(i.strip()) for i in DEFAULT_WORK_DAYS_INDICES_STR.split(',') if i.strip()] # Ensure empty strings are handled
STANDARD_START_TIME_CONFIG_DEFAULT = get_setting("WorkSchedule", "standard_start_time") # New config var for default
STANDARD_WORK_HOURS_PER_DAY = get_setting("WorkSchedule", "standard_work_hours_per_day", fallback_type=float)
OVERTIME_RATE_MULTIPLIER = get_setting("WorkSchedule", "overtime_rate_multiplier", fallback_type=float)
# LATE_ARRIVAL_NOTIFICATION_TIME_STR = get_setting("WorkSchedule", "late_arrival_notification_time") # Moved to DB settings
LATE_ARRIVAL_ALLOWED_MINUTES = get_setting("WorkSchedule", "late_arrival_allowed_minutes", fallback_type=int)
LATE_ARRIVAL_PENALTY_TYPE = get_setting("WorkSchedule", "late_arrival_penalty_type")
LATE_ARRIVAL_PENALTY_AMOUNT = get_setting("WorkSchedule", "late_arrival_penalty_amount", fallback_type=float)
STANDARD_LUNCH_BREAK_MINUTES_CONFIG_DEFAULT = get_setting("WorkSchedule", "standard_lunch_break_minutes", fallback_type=int) # New
MIN_UNEXCUSED_ABSENCE_DAYS_FOR_ALERT_CONFIG_DEFAULT = get_setting("WorkSchedule", "min_unexcused_absence_days_for_alert", fallback_type=int) # New
MAX_VACATION_CARRY_OVER_DAYS = get_setting("WorkSchedule", "max_vacation_carry_over_days", fallback_type=int)
VACATION_CALCULATION_METHOD = get_setting("WorkSchedule", "vacation_calculation_method")

EMPLOYEE_ID_PREFIX = get_setting("General", "employee_id_prefix")
DOCUMENTS_BASE_DIR = get_setting("General", "documents_base_dir")

DEFAULT_THEME = get_setting("Appearance", "default_theme") # For ttkbootstrap.Window themename
DEBUG_MODE = get_setting("Development", "debug_mode", fallback_type=bool) # Getter for DEBUG_MODE

# --- Company Details for Reports/Contracts ---
COMPANY_NAME_FOR_REPORTS = get_setting("CompanyDetails", "company_name_for_reports")
COMPANY_REGISTRATION_COUNTRY = get_setting("CompanyDetails", "company_registration_country")
COMPANY_ADDRESS_FOR_REPORTS = get_setting("CompanyDetails", "company_address_for_reports")
# --- API Settings ---
# It's best practice to load sensitive keys from environment variables
# The fallback value here is for development convenience if .env is not set up.
API_SECRET_KEY = os.environ.get("HR_API_KEY", "your_very_secret_default_api_key_for_dev_only")
