# core/auth_manager.py
import logging
from typing import Optional # Import Optional for type hinting
from data import queries as db_queries
from data import database as db_schema # For column constants

logger = logging.getLogger(__name__)

class AuthManager:
    def authenticate(self, username: str, password: str) -> tuple[bool, Optional[dict]]:
        """
        Authenticates a user.
        Returns a tuple: (success_status, user_details_dict_or_None)
        """
        try:
            user_tuple = db_queries.get_user_by_username_db(username)
            if user_tuple and db_queries.verify_password(user_tuple[db_schema.COL_USER_PASSWORD_HASH_INDEX], password): # Assuming COL_USER_PASSWORD_HASH_INDEX is defined in db_schema or you use the correct index
                # Convert tuple to a dictionary for easier use, similar to ApplicationController
                user_dict = {
                    db_schema.COL_USER_ID: user_tuple[db_schema.COL_USER_ID_INDEX],
                    db_schema.COL_USER_USERNAME: user_tuple[db_schema.COL_USER_USERNAME_INDEX],
                    db_schema.COL_USER_ROLE: user_tuple[db_schema.COL_USER_ROLE_INDEX],
                    db_schema.COL_USER_LINKED_EMP_ID: user_tuple[db_schema.COL_USER_LINKED_EMP_ID_INDEX] if len(user_tuple) > db_schema.COL_USER_LINKED_EMP_ID_INDEX else None
                }
                return True, user_dict
            return False, None
        except Exception as e:
            logger.error(f"Error during authentication for user {username}: {e}", exc_info=True)
            return False, None