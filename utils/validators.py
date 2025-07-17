# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\validators.py
import re
import logging

logger = logging.getLogger(__name__)

def is_valid_email(email: str) -> bool:
    """
    Validates an email address using a basic regex pattern.
    """
    if not email:
        return False
    # A common, though not exhaustive, regex for email validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """
    Validates a phone number. Allows digits, spaces, hyphens, parentheses, and plus sign.
    This is a very basic validation and might need to be adjusted for specific country formats.
    """
    if not phone:
        return False
    # Allows for international numbers, spaces, hyphens, parentheses. Min 7 digits.
    pattern = r"^\+?[\d\s\-\(\)]{7,}$"
    return bool(re.match(pattern, phone))