# controller/auth_controller.py
import logging
from typing import TYPE_CHECKING
from core.auth_manager import AuthManager

if TYPE_CHECKING:
    from ui.application_controller import ApplicationController

logger = logging.getLogger(__name__)

class AuthController:
    def __init__(self, app_controller: 'ApplicationController'):
        self.app_controller = app_controller
        self.auth_manager = AuthManager()

    def login(self, username: str, password: str):
        logger.debug(f"AuthController: Attempting login for user '{username}'")
        success, user_details = self.auth_manager.authenticate(username, password)
        if success and user_details:
            self.app_controller.on_login_success(user_details[db_schema.COL_USER_ID], user_details[db_schema.COL_USER_USERNAME], user_details[db_schema.COL_USER_ROLE], user_details.get(db_schema.COL_USER_LINKED_EMP_ID))
        else:
            self.app_controller.on_login_failed()