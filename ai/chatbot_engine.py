# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ai\chatbot_engine.py
import logging
from typing import TYPE_CHECKING, Optional
from data import queries as db_queries
# COL_EMP_DEPARTMENT is not defined in database.py; department name is accessed by string key 'department_name' from queries
from data.database import COL_EMP_ID, COL_EMP_NAME, COL_EMP_POSITION, COL_EMP_STATUS, STATUS_ACTIVE
from utils import localization
from utils.exceptions import EmployeeNotFoundError

# To avoid circular import with ApplicationController and then HRAppGUI -> EmployeeProfileWindow
if TYPE_CHECKING:
    from ..ui.application_controller import ApplicationController
    from ..ui.employee_profile_window import EmployeeProfileWindow

logger = logging.getLogger(__name__)

class ChatbotAssistant:
    def __init__(self, app_controller: 'ApplicationController'):
        self.app_controller = app_controller

    def process_input(self, user_input: str) -> str:
        user_input_lower = user_input.lower().strip()

        if user_input_lower in ["hello", "hi", "hey", localization._("مرحباً").lower(), localization._("أهلاً").lower()]:
            return localization._("chatbot_greeting")
        elif user_input_lower == "help" or user_input_lower == localization._("مساعدة").lower():
            return localization._("chatbot_help_text")
        elif user_input_lower.startswith("show employee") or user_input_lower.startswith(localization._("عرض موظف").lower()):
            parts = user_input.split()
            if len(parts) >= 3:
                emp_id_to_show = parts[-1].upper() # Assume ID is the last part
                return self._handle_show_employee(emp_id_to_show)
            else:
                return "Please specify an employee ID. Usage: show employee [ID]"
        elif user_input_lower == "list employees" or user_input_lower == localization._("قائمة الموظفين").lower():
            return self._handle_list_employees()
        elif user_input_lower in ["how many active employees", "active employee count", localization._("كم عدد الموظفين النشطين").lower(), localization._("عدد الموظفين النشطين").lower()]:
            return self._handle_active_employee_count()
        elif user_input_lower in ["list departments", "show departments", localization._("قائمة الأقسام").lower(), localization._("عرض الأقسام").lower()]:
            return self._handle_list_departments()


        # Add more intents here
        else:
            return localization._("chatbot_unknown_command")

    def _handle_show_employee(self, emp_id: str) -> str:
        try:
            emp = db_queries.view_employee_details(emp_id)
            response = f"Details for Employee {emp_id}:\n"
            response += f"  Name: {emp.get(COL_EMP_NAME, 'N/A')}\n"
            response += f"  Position: {emp.get(COL_EMP_POSITION, 'N/A')}\n"
            response += f"  Department: {emp.get('department_name', 'N/A')}\n" # Use string key 'department_name'
            response += f"  Status: {emp.get(COL_EMP_STATUS, 'N/A')}"
            # Action: Open profile window
            if self.app_controller:
                from ..ui.employee_profile_window import EmployeeProfileWindow # Local import for action
                self.app_controller._create_and_show_toplevel(
                    EmployeeProfileWindow,
                    employee_id=emp_id, # Pass emp_id directly
                    tracker_attr_name=f"active_employee_profile_window_{emp_id}" # Unique tracker
                )
                response += localization._("chatbot_profile_opened_message")
            return response
        except EmployeeNotFoundError:
            return localization._("employee_not_found_error_id", emp_id=emp_id)
        except Exception as e:
            logger.error(f"Chatbot error showing employee {emp_id}: {e}")
            return f"Sorry, an error occurred while fetching details for employee {emp_id}."

    def _handle_list_employees(self) -> str:
        try:
            employees = db_queries.list_all_employees()
            if not employees:
                return localization._("chatbot_no_employees_found")
            response = localization._("chatbot_active_employees_list_header") + "\n"
            count = 0
            for emp in employees:
                if emp.get(COL_EMP_STATUS) == STATUS_ACTIVE:
                    response += f"- {emp.get(COL_EMP_NAME)} ({emp.get(COL_EMP_ID)})\n"
                    count += 1
                    if count >= 10: # Limit display for brevity
                        response += localization._("chatbot_list_limit_message", count=(len(employees) - count))
                        break
            if count == 0:
                return localization._("chatbot_no_active_employees_found")
            return response
        except Exception as e:
            logger.error(f"Chatbot error listing employees: {e}")
            return localization._("chatbot_error_listing_employees")

    def _handle_active_employee_count(self) -> str:
        try:
            active_employees = [emp for emp in db_queries.get_all_employees_db() if emp.get(COL_EMP_STATUS) == STATUS_ACTIVE]
            count = len(active_employees)
            return localization._("chatbot_active_employee_count_response", count=count)
        except Exception as e:
            logger.error(f"Chatbot error getting active employee count: {e}")
            return localization._("chatbot_error_getting_active_count")

    def _handle_list_departments(self) -> str:
        try:
            departments = db_queries.list_departments_db()
            if not departments:
                return localization._("chatbot_no_departments_found")
            response = localization._("chatbot_department_list_header") + "\n"
            response += "\n".join([f"- {dept.get('department_name', 'N/A')}" for dept in departments])
            return response
        except Exception as e:
            logger.error(f"Chatbot error listing departments: {e}")
            return localization._("chatbot_error_listing_departments")