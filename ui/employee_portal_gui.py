# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\employee_portal_gui.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tkb
import logging

from utils import localization
from .themed_tk_window import ThemedTkWindow
# Import other necessary windows/components that this portal might open or use
from .vacation_management_window import VacationManagementWindow
from .attendance_log_viewer_window import AttendanceLogViewerWindow
from .payroll_management_window import PayrollWindow # Assuming this is the correct name
from .document_management_window import DocumentManagementWindow

logger = logging.getLogger(__name__)

class EmployeePortalGUI(ThemedTkWindow):
    def __init__(self, main_tk_window: tk.Tk, parent_app_controller: 'ApplicationController'):
        super().__init__(themename=parent_app_controller.get_current_theme(), parent_app=parent_app_controller)
        self.root = main_tk_window # This is the main Tk() instance, now managed by ThemedTkWindow
        self.parent_app = parent_app_controller

        self.title_key = "employee_portal_title" # Add to localization
        self.root.title(localization._(self.title_key))
        self.root.geometry("1000x700") # Adjust as needed

        self._setup_employee_portal_ui()
        self.root.update_idletasks() # Ensure UI creation tasks are processed

        # Initial theme and language application is handled by ThemedTkWindow's _deferred_initial_theme_application

    def _setup_employee_portal_ui(self):
        """Sets up the UI specific to the Employee Portal."""
        # Example: Simplified sidebar
        sidebar_frame = ttk.Frame(self.root, width=180, relief="raised", borderwidth=1)
        sidebar_frame.pack(side="left", fill="y", padx=(5,0), pady=5)

        self.my_profile_btn = ttk.Button(sidebar_frame, text=localization._("my_profile_btn"), command=self._show_my_profile)
        self.my_profile_btn.pack(fill="x", pady=5, padx=5)

        self.my_leave_requests_btn = ttk.Button(sidebar_frame, text=localization._("my_leave_requests_btn"), command=self._show_my_leave_requests)
        self.my_leave_requests_btn.pack(fill="x", pady=5, padx=5)

        self.my_attendance_btn = ttk.Button(sidebar_frame, text=localization._("my_attendance_btn"), command=self._show_my_attendance) # Add key
        self.my_attendance_btn.pack(fill="x", pady=5, padx=5)

        self.my_payslips_btn = ttk.Button(sidebar_frame, text=localization._("my_payslips_btn"), command=self._show_my_payslips) # Add key
        self.my_payslips_btn.pack(fill="x", pady=5, padx=5)

        self.my_documents_btn = ttk.Button(sidebar_frame, text=localization._("my_documents_btn"), command=self._show_my_documents) # Add key
        self.my_documents_btn.pack(fill="x", pady=5, padx=5)

        main_content_area = ttk.Frame(self.root, padding="10")
        main_content_area.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.welcome_label = ttk.Label(main_content_area, text=localization._("welcome_employee_portal_message"), font=("Helvetica", 16))
        self.welcome_label.pack(pady=20)

    def _show_my_profile(self): # pragma: no cover
        logger.info("Employee Portal: Show My Profile clicked.")
        # Assuming EmployeeProfileWindow exists and takes employee_id
        # from .employee_profile_window import EmployeeProfileWindow # Local import if not at top
        # self.parent_app._create_and_show_toplevel(EmployeeProfileWindow, employee_id=self.parent_app.get_current_employee_id(), tracker_attr_name=f"active_employee_profile_window_{self.parent_app.get_current_employee_id()}")

    def _show_my_leave_requests(self): # pragma: no cover
        logger.info("Employee Portal: Show My Leave Requests clicked.")
        # VacationManagementWindow might need to be opened with employee_id context
        self.parent_app._create_and_show_toplevel(VacationManagementWindow, parent_app_controller=self.parent_app, default_emp_id=self.parent_app.get_current_employee_id(), tracker_attr_name=f"active_vacation_management_window_{self.parent_app.get_current_employee_id()}")

    def _show_my_attendance(self): # pragma: no cover
        logger.info("Employee Portal: Show My Attendance clicked.")
        # AttendanceLogViewerWindow needs to be filtered for the current employee
        self.parent_app._create_and_show_toplevel(AttendanceLogViewerWindow, parent_app_controller=self.parent_app, default_emp_id=self.parent_app.get_current_employee_id(), tracker_attr_name=f"active_attendance_log_viewer_window_{self.parent_app.get_current_employee_id()}")

    def _show_my_payslips(self): # pragma: no cover
        logger.info("Employee Portal: Show My Payslips clicked.")
        # PayrollWindow needs to be filtered or opened in a mode for the current employee
        self.parent_app._create_and_show_toplevel(PayrollWindow, parent_app_controller=self.parent_app, default_emp_id=self.parent_app.get_current_employee_id(), tracker_attr_name=f"active_payroll_window_{self.parent_app.get_current_employee_id()}")

    def _show_my_documents(self): # pragma: no cover
        logger.info("Employee Portal: Show My Documents clicked.")
        # DocumentManagementWindow needs employee_id
        self.parent_app._create_and_show_toplevel(DocumentManagementWindow, employee_id=self.parent_app.get_current_employee_id(), tracker_attr_name=f"active_document_management_window_{self.parent_app.get_current_employee_id()}")

    def refresh_ui_for_language(self): # pragma: no cover
        super().refresh_ui_for_language() # Call parent's method
        self.root.title(localization._(self.title_key))
        self.my_profile_btn.config(text=localization._("my_profile_btn"))
        self.my_leave_requests_btn.config(text=localization._("my_leave_requests_btn"))
        self.my_attendance_btn.config(text=localization._("my_attendance_btn"))
        self.my_payslips_btn.config(text=localization._("my_payslips_btn"))
        self.my_documents_btn.config(text=localization._("my_documents_btn"))
        self.welcome_label.config(text=localization._("welcome_employee_portal_message"))

    def apply_instance_theme(self, style_obj: tkb.Style = None): # pragma: no cover
        # ThemedTkWindow's apply_instance_theme should handle most of it.
        # Add any specific theming for non-ttk widgets in EmployeePortalGUI here if needed.
        super().apply_instance_theme()