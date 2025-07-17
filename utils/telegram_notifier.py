# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\telegram_notifier.py
import logging
import requests
from datetime import datetime

import config
from data import database as db_schema
from data import queries as db_queries

logger = logging.getLogger(__name__)

def send_telegram_notification(message: str, bot_token: str = None, chat_id: str = None) -> bool:
    """Sends a notification message via Telegram."""
    if not bot_token:
        bot_token = db_schema.get_app_setting_db(db_schema.SETTING_TELEGRAM_BOT_TOKEN, config.TELEGRAM_BOT_TOKEN)
    if not chat_id:
        chat_id = db_schema.get_app_setting_db(db_schema.SETTING_TELEGRAM_CHAT_ID, config.TELEGRAM_CHAT_ID)

    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID is not configured. Cannot send notification.")
        return False

    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown" # Optional: for formatting
    }
    try:
        response = requests.post(send_url, data=payload, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        logger.info(f"Telegram notification sent successfully to chat ID {chat_id}.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False
    except Exception as e_gen: # Catch any other unexpected error
        logger.error(f"Unexpected error sending Telegram notification: {e_gen}", exc_info=True)
        return False

def send_weekly_hr_stats_to_telegram():
    """Fetches HR stats and sends them as a Telegram notification."""
    logger.info("Attempting to send weekly HR stats to Telegram...")
    try:
        total_employees = db_queries.get_total_employee_count_db()
        active_employees = db_queries.get_total_employee_count_db(active_only=True) # Assuming this param exists
        new_hires_this_month = db_queries.get_new_employees_this_month_count_db()
        # Add more stats as needed, e.g., pending leave requests, upcoming birthdays

        message = f"*Weekly HR Statistics - {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        message += f"👥 Total Employees: {total_employees}\n"
        message += f"✅ Active Employees: {active_employees}\n"
        message += f"🎉 New Hires (This Month): {new_hires_this_month}\n"
        # message += f"🌴 Pending Leave Requests: {get_pending_leave_requests_count_db()}\n" # Example

        if send_telegram_notification(message):
            logger.info("Weekly HR stats sent successfully to Telegram.")
            db_queries.set_app_setting_db(db_schema.SETTING_LAST_WEEKLY_STATS_SENT_DATE, datetime.now().isoformat())
        else:
            logger.error("Failed to send weekly HR stats to Telegram.")

    except Exception as e:
        logger.error(f"Error generating or sending weekly HR stats: {e}", exc_info=True)
        # Optionally send a simpler error notification via Telegram if the main one fails
        send_telegram_notification(f"Error: Could not generate weekly HR stats. Please check logs. ({type(e).__name__})")