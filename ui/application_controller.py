# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\application_controller.py
import tkinter as tk
import threading # Import the threading module
from tkinter import messagebox
import logging
import ttkbootstrap as ttkb
from typing import Dict, Optional, List, Any # Added List, Any
# Project-specific imports - these will need careful adjustment
from data import queries as db_queries # Assuming queries.py is in data directory
from data import database as db_schema # For constants like COL_USER_ROLE, ROLE_ADMIN, COL_USER_ID, COL_USER_USERNAME, COL_USER_LINKED_EMP_ID
from utils import telegram_notifier, alert_utils # Import the new notifier and alert_utils
from utils import localization # Removed attendance_utils from here
from utils.gui_utils import center_toplevel_on_parent # Import the helper function
import sys # Ensure sys is imported
import config as app_config # Import config for default theme
from datetime import datetime, timedelta # Added for scheduling
# UI Window imports - these will be created as separate files in the ui directory later
from .themed_toplevel import ThemedToplevel # Assuming ThemedToplevel is moved to ui
# For now, we'll comment them out or define dummy classes if needed for ApplicationController to load
from .login_window import LoginWindow
from .main_gui import HRAppGUI # Import HRAppGUI
from .employee_portal_gui import EmployeePortalGUI # Placeholder for new Employee Portal
from .manager_portal_gui import ManagerPortalGUI # Placeholder for new Manager Portal
from controller.auth_controller import AuthController # Import the new AuthController
from .settings_window import SettingsWindow # Import the correct class name
# from .employee_form_window import EmployeeFormWindow # Example
# from .department_form_window import DepartmentManagementWindow # Example
from .dashboard_window import DashboardWindow
# --- Placeholder for missing imports, these would need to be defined or imported correctly ---
# These are used but their origin is not clear from the provided context.
# If they are part of your project, ensure they are imported.
# If they are from the old monolithic file, they need to be refactored.
class PredictiveAnalytics: pass
class EmployeeFormWindow: pass
class ReportsWindow: pass
class PayrollWindow: pass
class AlertsWindow: pass
from .task_management_window import TaskManagementWindow # Import the new TaskManagementWindow
# ... other window imports

logger = logging.getLogger(__name__)

class ApplicationController:
    """
    Main controller for the HR application.
    Manages user sessions, main GUI, and coordinates application flow.
    """
    def __init__(self, root_tk_window: tk.Tk):
        self.root = root_tk_window
        self.current_user_id: Optional[int] = None
        self.current_username: Optional[str] = None
        self.current_user_role: Optional[str] = None
        self.current_employee_id: Optional[str] = None
        self.current_user_details: Optional[Dict] = None
        # Default theme for login or before main GUI is fully themed
        self.current_app_theme_name_for_login: str = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_THEME, "light")

        self.hr_app_gui: Optional[HRAppGUI] = None # HRAppGUI is created after successful login
        self.hr_app_gui_created = False
        self.login_window: Optional[LoginWindow] = None
        self.auth_controller: AuthController = AuthController(self) # Instantiate AuthController
        self.active_windows: Dict[str, ThemedToplevel] = {} # Initialize active_windows tracker

        # Initialize trackers for modal windows
        # These are now managed by self.active_windows dictionary using tracker_attr_name
        # self.active_reports_window: Optional[ReportsWindow] = None # Example, will be in active_windows
        # self.active_payroll_window: Optional[PayrollWindow] = None # Example
        # self.active_alerts_window: Optional[AlertsWindow] = None # Example
        # self.active_dashboard_window: Optional['DashboardWindow'] = None # Example
        # self.active_settings_window: Optional[SettingsWindow] = None # Example
        # self.active_attendance_log_viewer_window: Optional['AttendanceLogViewerWindow'] = None # Example
        # self.active_metrics_dashboard_window: Optional['MetricsDashboardWindow'] = None # Example
        # self.active_interview_scheduling_window: Optional['InterviewSchedulingWindow'] = None # Example
        # self.active_about_dialog: Optional['AboutDialog'] = None # Example
        # self.active_professional_reports_window: Optional['ProfessionalReportsWindow'] = None # Example
        self.active_employee_form_window: Optional['EmployeeFormWindow'] = None # Specific tracker for modal EmployeeForm
        self.active_task_management_window: Optional[TaskManagementWindow] = None # Tracker for TaskManagementWindow
        # self.active_chatbot_window: Optional['ChatbotWindow'] = None # Example
        self.absence_alert_timer: Optional[threading.Timer] = None

        self.weekly_stats_timer: Optional[threading.Timer] = None

        # --- GUI Elements ---
        # self.active_chatbot_window: Optional['ChatbotWindow'] = None # Example, managed by active_windows
        self.export_progress_bar: Optional[ttk.Progressbar] = None # For CSV/PDF export progress
        self.active_operation_lock = threading.Lock() # To prevent multiple long ops at once

        # init_db() and config.load_config() are called in main.py before ApplicationController instantiation
        # So, they are redundant here.
        # init_db()
        # config.load_config()
    
        # --- Login Bypass (for now) ---
        

        # To re-enable the login window, comment out or remove the following lines:
        # self.current_user_role = db_schema.ROLE_ADMIN 
        # self.current_user_details = {
        # db_schema.COL_USER_ID: 0, 
        # db_schema.COL_USER_USERNAME: "admin_bypass",
        # db_schema.COL_USER_ROLE: db_schema.ROLE_ADMIN
        # }
        # --- End Login Bypass ---        
        # Apply theme immediately after HRAppGUI is created and before mainloop starts
        # This is now handled in show_main_gui after HRAppGUI is instantiated.

        

    def _clear_main_window_content(self):
        """Destroys all direct children of the root window, preparing for a new view (login or main app)."""
        if self.root and self.root.winfo_exists():
            for widget in list(self.root.winfo_children()):
                # This loop is for widgets packed/gridded directly into self.root.
                # Toplevels like LoginWindow are not direct children in this sense.
                widget.destroy()
        if self.hr_app_gui:
            self.hr_app_gui = None # Dereference
            self.hr_app_gui_created = False

    def logout(self):
        """Handles user logout."""
        logger.info(f"User {self.current_user_details.get(db_schema.COL_USER_USERNAME, 'Unknown') if self.current_user_details else 'Unknown'} logging out.")
        
        self.stop_scheduler_on_exit() # Stop schedulers on logout
        self._stop_absence_alert_scheduler() # Stop absence alert scheduler
        # Close all active Toplevel windows
        for window_key in list(self.active_windows.keys()): # Iterate over a copy of keys
            window = self.active_windows.pop(window_key, None) # Remove and get
            if window and window.winfo_exists():
                window.destroy()
        
        if self.active_employee_form_window and self.active_employee_form_window.winfo_exists():
            self.active_employee_form_window.destroy()
            self.active_employee_form_window = None

        self._clear_main_window_content()

        self.current_user_details = None
        self.current_user_role = None
        
        self.root.withdraw() # Hide the main window
        self.show_login_window() # Show login screen

    def get_current_theme(self) -> str:
        """Returns the current logical theme name ('light' or 'dark')."""
        if self.hr_app_gui and hasattr(self.hr_app_gui, 'current_theme'):
            return self.hr_app_gui.current_theme
        return self.current_app_theme_name_for_login

    def toggle_theme(self):
        """Toggles the application theme between light and dark."""
        current_logical_theme = self.get_current_theme()
        new_logical_theme = "dark" if current_logical_theme == "light" else "light"
        
        self.current_app_theme_name_for_login = new_logical_theme # Update for consistency
        
        if self.hr_app_gui:
            self.hr_app_gui.current_theme = new_logical_theme
            if self.hr_app_gui.style: # Ensure style object exists
                 self.hr_app_gui.apply_instance_theme(self.hr_app_gui.style)
        # Update all active Toplevels
        active_toplevels_to_update = list(self.active_windows.values())
        if self.active_employee_form_window and self.active_employee_form_window.winfo_exists():
            active_toplevels_to_update.append(self.active_employee_form_window)

        for window in active_toplevels_to_update:
            if window and window.winfo_exists() and hasattr(window, 'update_local_theme_elements'):
                window.update_local_theme_elements()
        logger.info(f"Theme toggled to: {new_logical_theme}")

    def toggle_app_language(self):
        """Toggles the application language and refreshes the UI."""
        current_lang = localization.LANG_MANAGER.current_lang
        new_lang = "ar" if current_lang == "en" else "en"
        
        if localization.LANG_MANAGER.set_language(new_lang):
            logger.info(f"Language toggled to: {new_lang}")
            # Save the new language preference to database settings
            db_schema.set_app_setting_db(db_schema.SETTING_DEFAULT_LANGUAGE, new_lang)

            # Refresh main GUI
            if self.hr_app_gui and self.hr_app_gui.root.winfo_exists():
                self.hr_app_gui.refresh_ui_for_language()
            
            # Refresh all active Toplevel windows
            active_toplevels_to_update = list(self.active_windows.values())
            if self.active_employee_form_window and self.active_employee_form_window.winfo_exists():
                active_toplevels_to_update.append(self.active_employee_form_window)

            for window in active_toplevels_to_update:
                if window and window.winfo_exists() and hasattr(window, 'refresh_ui_for_language'):
                    window.refresh_ui_for_language()
        else:
            logger.warning(f"Failed to toggle language to {new_lang}.")


    def _initial_schedule_weekly_stats(self):
        """Schedules the first weekly stats report check."""
        logger.info("Initializing weekly statistics scheduler.")
        self._schedule_next_weekly_stats_report()

    def _schedule_next_weekly_stats_report(self):
        """Calculates next run time and schedules the weekly stats report."""
        if self.weekly_stats_timer: # Cancel any existing timer
            self.weekly_stats_timer.cancel()
            self.weekly_stats_timer = None
        self._stop_absence_alert_scheduler() # Ensure it's stopped before rescheduling

        enabled_str = db_schema.get_app_setting_db(db_schema.SETTING_AUTO_WEEKLY_STATS_ENABLED, "false")
        if not enabled_str or enabled_str.lower() != "true":
            logger.info("Weekly statistics reporting is disabled.")
            return

        report_day_name = db_schema.get_app_setting_db(db_schema.SETTING_AUTO_WEEKLY_STATS_DAY, "Monday")
        report_time_str = db_schema.get_app_setting_db(db_schema.SETTING_AUTO_WEEKLY_STATS_TIME, "09:00")

        try:
            report_weekday_index = db_schema.DAYS_OF_WEEK.index(report_day_name) # Monday is 0
            report_time_obj = datetime.strptime(report_time_str, "%H:%M").time()
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid day/time for weekly stats: {report_day_name}, {report_time_str}. Error: {e}")
            return # pragma: no cover

        now = datetime.now()
        days_ahead = report_weekday_index - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.time() >= report_time_obj):
            days_ahead += 7
        
        next_run_date = now.date() + timedelta(days=days_ahead)
        next_run_datetime = datetime.combine(next_run_date, report_time_obj)
        delay_seconds = (next_run_datetime - now).total_seconds()

        if delay_seconds > 0:
            self.weekly_stats_timer = threading.Timer(delay_seconds, self._send_weekly_stats_report_and_reschedule)
            self.weekly_stats_timer.daemon = True
            self.weekly_stats_timer.start()
            logger.info(f"Weekly statistics report scheduled for {next_run_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    def _send_weekly_stats_report_and_reschedule(self):
        logger.info("Generating and sending weekly statistics report...")
        try:
            stats = db_queries.get_weekly_statistics_summary_db()
            message = telegram_notifier.format_weekly_stats_for_telegram(stats) # Assuming it's in telegram_notifier
            telegram_notifier.send_telegram_notification(message)
            logger.info("Weekly statistics report sent.")
        except Exception as e:
            logger.error(f"Error during weekly statistics report generation/sending: {e}", exc_info=True) # pragma: no cover
        
        if self.root.winfo_exists(): # Check if root window still exists
            self.root.after(1000, self._schedule_next_weekly_stats_report)
        else: # pragma: no cover
            logger.info("Root window destroyed, not rescheduling weekly stats report via root.after.")

    def reschedule_weekly_stats(self):
        logger.info("Rescheduling weekly stats report due to settings change.")
        self._schedule_next_weekly_stats_report()

    def stop_scheduler_on_exit(self):
        if self.weekly_stats_timer:
            self.weekly_stats_timer.cancel()
            logger.info("Weekly statistics timer cancelled on exit.")
        self._stop_absence_alert_scheduler()
        # Cancel any other timers/threads managed by the controller here
        # Example: if you had a separate timer for daily checks
        # if self.daily_check_timer:
        #     self.daily_check_timer.cancel()

    def set_current_user(self, user_id: int, username: str, role: str, employee_id: Optional[str] = None):
        self.current_user_id = user_id
        self.current_username = username
        self.current_user_details = db_queries.get_user_by_id_db(user_id) # Fetch full details
        self.current_user_role = role
        self.current_employee_id = employee_id
        logger.info(f"User '{username}' (Role: {role}, EmpID: {employee_id or 'N/A'}) set as current user.")
        if self.hr_app_gui and self.hr_app_gui.root.winfo_exists(): # Use hr_app_gui
            self.hr_app_gui.update_status_bar_user(username, role)
            self.hr_app_gui.update_ui_for_role(role) # Refresh UI based on new role
            
    def get_current_user_role(self) -> Optional[str]:
        return self.current_user_role

    def get_current_user_id(self) -> Optional[int]:
        # Use self.current_user_details for robustness if it's populated
        if self.current_user_details:
            return self.current_user_details.get(db_schema.COL_USER_ID)
        return None # Fallback if details not set
    
    def get_current_username(self) -> Optional[str]:
        return self.current_username

    def get_current_employee_id(self) -> Optional[str]:
        return self.current_employee_id

    def is_admin(self) -> bool:
        return self.current_user_role == db_schema.ROLE_ADMIN

    def start(self):
        """
        Starts the application.
        Original behavior: Shows the login window.
        Current behavior (for development): Bypasses login and shows main GUI with a mock admin user.
        """
        logger.info("Bypassing login window for development.")
        # Simulate a logged-in admin user for development
        self.current_user_details = {
            db_schema.COL_USER_ID: 1, # Use ID 1 (assuming default admin user)
            db_schema.COL_USER_USERNAME: "dev_admin",
            db_schema.COL_USER_ROLE: db_schema.ROLE_ADMIN,
            db_schema.COL_USER_LINKED_EMP_ID: None # No linked employee for this dev user
        }
        # Also set the individual convenience attributes
        self.current_username = self.current_user_details[db_schema.COL_USER_USERNAME]
        self.current_user_role = self.current_user_details[db_schema.COL_USER_ROLE]
        self.current_user_id = self.current_user_details[db_schema.COL_USER_ID]
        self.current_employee_id = self.current_user_details[db_schema.COL_USER_LINKED_EMP_ID]
        self.show_main_gui()
        # self.show_login_window() # Original line to show login window

    def show_login_window(self):     
        
        # Close any other stray Toplevels first
        for window_key in list(self.active_windows.keys()): # Iterate over a copy of keys
            window = self.active_windows.pop(window_key, None) # Remove and get            if window and window.winfo_exists():
            window.destroy()
            if self.active_employee_form_window and self.active_employee_form_window.winfo_exists():
                self.active_employee_form_window.destroy()
                self.active_employee_form_window = None
        # If hr_app_gui exists (e.g., from a previous session/logout), ensure its content is cleared
        # and self.root is withdrawn.
        if self.hr_app_gui and self.hr_app_gui.root.winfo_exists():
            self.root.withdraw() # Ensure main root is hidden
            # Destroy children of hr_app_gui.root (which is self.root)
            # This is to clean up HRAppGUI's widgets before showing login.
            # A more structured way would be for HRAppGUI to have a .destroy_widgets() method.
            self._clear_main_window_content() # This also sets hr_app_gui to None
            

        if self.login_window and self.login_window.winfo_exists():
            self.login_window.lift()
            self.login_window.focus_set()
        else:
            if not self.root.winfo_exists(): # Should ideally not happen
                logger.critical("Main root window does not exist when trying to show LoginWindow. Cannot proceed.")
                # Optionally, raise an exception or show a critical error messagebox and exit.
                # For now, just log and return to prevent further errors.
                return
            self.root.withdraw() # Ensure root is hidden before login window appears
            # Pass auth_controller and self (app_controller) to LoginWindow
            self.login_window = LoginWindow(self.root, self.auth_controller, self)
            self.login_window.protocol("WM_DELETE_WINDOW", self.on_close_main_app)


    def on_login_success(self, user_id: int, username: str, role: str, employee_id: Optional[str]):
        logger.info(f"ApplicationController: Login successful for user '{username}'")
        self.set_current_user(user_id, username, role, employee_id)
        if self.login_window and self.login_window.winfo_exists():
            self.login_window.destroy()
            self.login_window = None
        self.show_main_gui() # This will deiconify the root window

    def on_login_failed(self):
        logger.warning("ApplicationController: Login failed.")
        if self.login_window and self.login_window.winfo_exists():
            messagebox.showerror(localization._("login_failed_title"), localization._("login_invalid_credentials_error"), parent=self.login_window)
            self.login_window.password_var.set("") # Clear password field
            self.login_window.username_entry.focus_set() # Focus username

    def show_main_gui(self):
        if self.hr_app_gui is None or not (self.hr_app_gui.root.winfo_exists() if self.hr_app_gui.root else False):
            # If root was destroyed by logout, it needs to be recreated or main.py needs to handle re-init
            if not self.root.winfo_exists():
                # If the main root window (from main.py) is gone, the application cannot properly continue.
                # Log this critical error and exit.
                self.root = tk.Tk() # Recreate root if necessary
                logger.critical("Main root window does not exist when trying to show main GUI. Application cannot continue.")
                # Attempt to show a messagebox, but it might fail if Tkinter is in a bad state.
                try:
                    messagebox.showerror("Critical Error", "Main application window is missing. Application will exit.", parent=None)
                except tk.TclError:
                    logger.error("Failed to show critical error messagebox as Tkinter may be unstable.")
                sys.exit(1) # Exit application            

            self.hr_app_gui = HRAppGUI(self.root, self) # Pass self (ApplicationController)
            self.hr_app_gui_created = True
            
            # Apply theme after HRAppGUI is created
            if self.hr_app_gui.style:
                self.hr_app_gui.apply_instance_theme(self.hr_app_gui.style) # HRAppGUI applies its own theme
            else: # pragma: no cover
                logger.error("HRAppGUI style object not available for initial theme application in show_main_gui.")
        
            self.root.deiconify() # Show the root window which is now the HRAppGUI
            if self.hr_app_gui: # Ensure hr_app_gui is not None
                self.hr_app_gui.root.lift() # Bring to front
                self.hr_app_gui.update_status_bar_user(self.get_current_username(), self.get_current_user_role())
                self.hr_app_gui.update_ui_for_role(self.get_current_user_role()) # type: ignore
            self._initial_schedule_weekly_stats() # Schedule after main GUI is up
 
    def _stop_absence_alert_scheduler(self):
        if self.absence_alert_timer:
            self.absence_alert_timer.cancel()
            self.absence_alert_timer = None
            logger.info("Absence alert timer cancelled by _stop_absence_alert_scheduler.")

    def on_close_main_app(self):
        if messagebox.askokcancel(localization._("quit_app_dialog_title"), localization._("quit_app_dialog_message"), parent=self.root):
            logger.info("Application shutdown initiated by user.")
            
            # 1. Stop schedulers (threading.Timer based)
            self.stop_scheduler_on_exit()

            # 2. Close all active Toplevel windows gracefully
            # This allows them to run their own WM_DELETE_WINDOW handlers,
            # which should include cancelling any self.after() calls they manage.
            # Iterate over a copy of keys because destroying a window might modify the dict via its close handler.
            for window_key in list(self.active_windows.keys()):
                window = self.active_windows.get(window_key)
                if window and window.winfo_exists():
                    try:
                        logger.debug(f"Destroying tracked window: {window.title()} during app shutdown.")
                        window.destroy() # This should trigger its WM_DELETE_WINDOW protocol
                    except tk.TclError as e:
                        logger.warning(f"TclError destroying window {window.title()} during shutdown: {e}")
            self.active_windows.clear() # Clear the tracking dict

            # Handle specifically tracked windows like EmployeeFormWindow
            if self.active_employee_form_window and self.active_employee_form_window.winfo_exists():
                try:
                    logger.debug(f"Destroying active EmployeeFormWindow during app shutdown.")
                    self.active_employee_form_window.destroy()
                except tk.TclError as e:
                    logger.warning(f"TclError destroying EmployeeFormWindow during shutdown: {e}")
            self.active_employee_form_window = None
            
            # Give Tkinter a moment to process window destruction events
            if self.root.winfo_exists():
                self.root.update_idletasks() 
                # Schedule the final part of the shutdown to run after current event processing
                self.root.after(50, self._finalize_shutdown) # Small delay
            else:
                # If root is already gone, just exit
                logger.info("Root window already destroyed. Exiting process.")
                sys.exit(0)

    def _create_and_show_toplevel(self, window_class, *args, tracker_attr_name: Optional[str] = None, **kwargs):
        """
        Creates and shows a Toplevel window, ensuring only one instance (if tracker_attr_name is provided).
        Manages window focus and tracks active windows.
        """
        if tracker_attr_name:
            active_window = self.active_windows.get(tracker_attr_name)
            if active_window and active_window.winfo_exists():
                active_window.deiconify()
                active_window.lift()
                active_window.focus_set()
                # logger.debug(f"Window for {tracker_attr_name} already open. Bringing to front.")
                # messagebox.showinfo("Window Active", f"The '{active_window.title()}' window is already open.", parent=active_window)
                return None # Indicate that an existing window was focused

        # Pass self (ApplicationController) as app_instance
        parent_widget = self.hr_app_gui.root if self.hr_app_gui and self.hr_app_gui.root.winfo_exists() else self.root
        win = window_class(parent_widget, self, *args, **kwargs)

        if win.winfo_exists(): # Check if window was successfully created
            win.update_idletasks()
            # Center the new Toplevel window relative to the main_gui or root
            # self.main_gui is not an attribute. self.root is the main application window.
            parent_for_centering = self.root
            center_toplevel_on_parent(win, parent_for_centering)

            if tracker_attr_name:
                self.active_windows[tracker_attr_name] = win # type: ignore
                logger.debug(f"Opened and tracking new window for {tracker_attr_name}: {win}")
            elif window_class == EmployeeFormWindow: # Special handling for EmployeeFormWindow
                self.active_employee_form_window = win # type: ignore
                logger.debug(f"Opened and tracking new EmployeeFormWindow: {win}")


            def on_close_toplevel():
                window_title = win.title() if win.winfo_exists() else "Unknown Window"
                logger.debug(f"Closing window: {window_title}")
                
                if tracker_attr_name and self.active_windows.get(tracker_attr_name) == win:

                    self.active_windows.pop(tracker_attr_name, None)
                    logger.debug(f"Unregistered {window_title} from active_windows using tracker: {tracker_attr_name}")
                elif window_class == EmployeeFormWindow and self.active_employee_form_window == win:
                    self.active_employee_form_window = None
                    logger.debug(f"Unregistered EmployeeFormWindow from dedicated tracker.")
                
                # Compatibility: Also remove from HRAppGUI's list if it's being tracked there
                if self.hr_app_gui and hasattr(self.hr_app_gui, 'active_toplevels') and win in self.hr_app_gui.active_toplevels:
                    self.hr_app_gui.active_toplevels.remove(win)
                    logger.debug(f"Removed {window_title} from hr_app_gui.active_toplevels.")

                if win.winfo_exists():
                    win.destroy()
            return win # Return the newly created window
        return None # Should not happen if window_class is valid

    def _finalize_shutdown(self):
        logger.info("Finalizing application shutdown sequence.")
        if self.root.winfo_exists():
            try:
                # Destroy the main GUI components if they exist and haven't been cleared
                if self.hr_app_gui and hasattr(self.hr_app_gui, '_cancel_all_recurring_tasks'):
                    logger.debug("Calling HRAppGUI._cancel_all_recurring_tasks before root destroy.")
                    self.hr_app_gui._cancel_all_recurring_tasks()
                
                self.root.destroy() # Destroy the main window and all its children
                logger.info("Tkinter root window destroyed.")
            except tk.TclError as e:
                logger.error(f"TclError during final root destroy: {e}")
            except Exception as e_final: # Catch any other error during destroy
                logger.error(f"Unexpected error during final root destroy: {e_final}")
        else:
            logger.info("Root window was already destroyed before _finalize_shutdown.")
        logger.info("Application shutdown complete. Exiting process.")
        sys.exit(0) # Ensure the Python process exits