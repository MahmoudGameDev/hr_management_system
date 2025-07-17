# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\manager_portal_gui.py
import tkinter as tk
from tkinter import ttk, messagebox # Added messagebox
import ttkbootstrap as tkb
import logging

from utils import localization
from .themed_tk_window import ThemedTkWindow
# Import other necessary windows/components
from .approvals_window import ApprovalsWindow # For pending approvals
from .attendance_log_viewer_window import AttendanceLogViewerWindow # For team attendance
from .employee_evaluation_window import EmployeeEvaluationWindow # For performance reviews

logger = logging.getLogger(__name__)

class ManagerPortalGUI(ThemedTkWindow):
    def __init__(self, main_tk_window: tk.Tk, parent_app_controller: 'ApplicationController'):
        super().__init__(themename=parent_app_controller.get_current_theme(), parent_app=parent_app_controller)
        self.root = main_tk_window
        self.parent_app = parent_app_controller

        self.title_key = "manager_portal_title" # Add to localization
        self.root.title(localization._(self.title_key))
        self.root.geometry("1100x750") # Adjust as needed

        self._setup_manager_portal_ui()
        self.root.update_idletasks()

    def _setup_manager_portal_ui(self):
        """Sets up the UI specific to the Manager Portal."""
        sidebar_frame = ttk.Frame(self.root, width=200, relief="raised", borderwidth=1)
        sidebar_frame.pack(side="left", fill="y", padx=(5,0), pady=5)

        self.team_overview_btn = ttk.Button(sidebar_frame, text=localization._("team_overview_btn"), command=self._show_team_overview)
        self.team_overview_btn.pack(fill="x", pady=5, padx=5)

        self.pending_approvals_btn = ttk.Button(sidebar_frame, text=localization._("pending_approvals_btn"), command=self._show_pending_approvals)
        self.pending_approvals_btn.pack(fill="x", pady=5, padx=5)

        self.team_attendance_btn = ttk.Button(sidebar_frame, text=localization._("team_attendance_btn"), command=self._show_team_attendance) # Add key
        self.team_attendance_btn.pack(fill="x", pady=5, padx=5)

        self.performance_reviews_btn = ttk.Button(sidebar_frame, text=localization._("performance_reviews_btn"), command=self._show_performance_reviews) # Add key
        self.performance_reviews_btn.pack(fill="x", pady=5, padx=5)

        main_content_area = ttk.Frame(self.root, padding="10")
        main_content_area.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.welcome_label = ttk.Label(main_content_area, text=localization._("welcome_manager_portal_message"), font=("Helvetica", 16))
        self.welcome_label.pack(pady=20)

    def _show_team_overview(self): # pragma: no cover
        logger.info("Manager Portal: Show Team Overview clicked.")
        # This would likely involve a new Toplevel window or a dedicated frame within the main_content_area
        # to display team members, their key stats, etc.
        # For now, let's just log it.
        # Example: self.parent_app._create_and_show_toplevel(TeamOverviewWindow, manager_id=self.parent_app.get_current_employee_id())

    def _show_pending_approvals(self): # pragma: no cover
        logger.info("Manager Portal: Show Pending Approvals clicked.")
        # Assuming ApprovalsWindow can be filtered or defaults to showing items for the current manager
        self.parent_app._create_and_show_toplevel(ApprovalsWindow, parent_app_controller=self.parent_app)

    def _show_team_attendance(self): # pragma: no cover
        logger.info("Manager Portal: Show Team Attendance clicked.")
        current_manager_emp_id = self.parent_app.get_current_employee_id()
        if not current_manager_emp_id:
            messagebox.showwarning(localization._("error_title"), localization._("manager_id_not_found_error"), parent=self.root) # Add keys
            return

        self.parent_app._create_and_show_toplevel(
            AttendanceLogViewerWindow,
            view_mode="manager_team",
            manager_id=current_manager_emp_id,
            # tracker_attr_name is managed by ApplicationController._create_and_show_toplevel
            # but we can suggest a pattern if needed, or let the default handling in ThemedToplevel work.
            # For now, relying on ThemedToplevel's default tracker_attr_name or specific handling in ApplicationController.
            # If AttendanceLogViewerWindow.TRACKER_NAME is defined, it will be used.
        )

    def _show_performance_reviews(self): # pragma: no cover
        logger.info("Manager Portal: Show Performance Reviews clicked.")
        # EmployeeEvaluationWindow might be used to initiate new reviews for team members
        # or view existing ones.
        self.parent_app._create_and_show_toplevel(EmployeeEvaluationWindow, parent_app_controller=self.parent_app, manager_id=self.parent_app.get_current_employee_id())

    def refresh_ui_for_language(self): # pragma: no cover
        super().refresh_ui_for_language()
        self.root.title(localization._(self.title_key))
        self.team_overview_btn.config(text=localization._("team_overview_btn"))
        self.pending_approvals_btn.config(text=localization._("pending_approvals_btn"))
        self.team_attendance_btn.config(text=localization._("team_attendance_btn"))
        self.performance_reviews_btn.config(text=localization._("performance_reviews_btn"))
        self.welcome_label.config(text=localization._("welcome_manager_portal_message"))

    def apply_instance_theme(self, style_obj: tkb.Style = None): # pragma: no cover
        super().apply_instance_theme()