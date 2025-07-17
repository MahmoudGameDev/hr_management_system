# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\main_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys # For stderr and path manipulation
import os # For path manipulation
from .approvals_window import ApprovalsWindow
# Add the project root directory to sys.path to allow importing 'config'
# __file__ is ui/main_gui.py
# os.path.dirname(__file__) is ui/
# os.path.dirname(os.path.dirname(__file__)) is the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- CRITICAL IMPORT TEST FOR TTKBOOTSTRAP ---
try:
    import ttkbootstrap as tkb
    print(f"DEBUG: In ui/main_gui.py - ttkbootstrap imported as tkb: {tkb}", file=sys.stdout)
    if tkb is None: # Should not happen if import succeeded
        raise ImportError("ttkbootstrap imported as tkb, but tkb is None.")
except ImportError as e_import_tb:
    print(f"CRITICAL ERROR: Failed to import ttkbootstrap in ui/main_gui.py: {e_import_tb}", file=sys.stderr)
    tkb = None # Ensure tkb is defined, even if as None, to prevent NameError later if code proceeds
    # Consider re-raising or sys.exit(1) if ttkbootstrap is absolutely essential for any part of this module to load
    # raise # Re-raise to halt execution if ttkbootstrap is critical for module-level definitions

from tkinter.scrolledtext import ScrolledText
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip # type: ignore
from ttkbootstrap.widgets import DateEntry # Import DateEntry
from ttkbootstrap.dialogs import Messagebox, Querybox
from PIL import Image, ImageTk, UnidentifiedImageError
import os
import logging
import datetime as dt
from datetime import datetime, timedelta, date as dt_date
import re
import webbrowser
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import queue
import json
import csv # Added missing import for csv
from typing import List, Dict, Union, Any, Optional # Added Any and Optional
from .employee_profile_window import EmployeeProfileWindow # Added import
from utils import attendance_utils # For Instant Status Assessment
from utils import fingerprint_log_processor # For Fingerprint Analysis
from .skill_management_window import SkillManagementWindow # New Import for Skills

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None # Define fitz as None if import fails
    logging.warning("PyMuPDF (fitz) not installed. PDF signing features in main_gui might be limited.")

# --- Project-specific imports ---
import config # Assuming config.py is in the root of hr_dashboard_project
from data import database as db_schema
from data import queries as db_queries # For database operations # Corrected
from utils.exceptions import DatabaseOperationError, InvalidInputError, EmployeeNotFoundError, UserNotFoundError, HRException, AttendanceError, AlreadyClockedInError, NotClockedInError # Import custom exceptions # Corrected
from utils.localization import _, LANG_MANAGER # Import both _ and LANG_MANAGER
from utils.theming_utils import (
    get_theme_palette_global,
    _theme_text_widget_global, _theme_widget_recursively_global,
    HRAppGUI_static_themes,
    )
from utils import image_utils # Changed import style
from utils import file_utils # Changed import style
from utils import validators # Changed import style
from utils.gui_utils import (CustomDialog, extract_id_from_combobox_selection, # Added CustomDialog
                             populate_employee_combobox, populate_department_combobox, populate_user_combobox) # Added populate_department_combobox

# Import other UI components that HRAppGUI will manage/open
# These will be moved to their own files in the ui/ directory later.
# For now, we'll assume they will be available for import from the 'ui' package.
from ui.themed_tk_window import ThemedTkWindow
from ui.themed_toplevel import ThemedToplevel # Base for modal dialogs
from ui.components import AutocompleteCombobox # Corrected import
# Import all modal windows that HRAppGUI will open
from ui.employee_form_window import EmployeeFormWindow
from ui.department_form_window import DepartmentManagementWindow
from ui.user_management_window import UserManagementWindow
from ui.settings_window import SettingsWindow # Changed AppSettingsWindow to SettingsWindow
from ui.electronic_contract_window import ElectronicContractWindow # Ensure this is imported
from ui.about_dialog import AboutDialog
from ui.dashboard_window import DashboardWindow
from ui.attendance_log_viewer_window import AttendanceLogViewerWindow
from ui.payroll_management_window import PayrollWindow
from ui.document_management_window import DocumentManagementWindow
from ui.evaluation_criteria_window import EvaluationCriteriaWindow
from ui.task_management_window import TaskFormWindow # Corrected class name
from ui.employee_evaluation_window import EmployeeEvaluationWindow # Corrected class name
from ui.vacation_management_window import VacationManagementWindow
from ui.interview_scheduler_window import InterviewSchedulerWindow
from ui.data_management_window import DataManagementWindow
from .approvals_window import ApprovalsWindow # Ensure ApprovalsWindow is imported
from .user_management_window import UserManagementWindow
from .alerts_window import AlertsWindow
from .zkteco_management_window import ZKTecoManagementWindow # Placeholder
from .training_course_management_window import TrainingCourseManagementWindow # New Import
# Import placeholder windows that will be created later
from ui.reports_window import ReportsWindow # Placeholder
from ui.alerts_window import AlertsWindow # Placeholder
from ui.approvals_window import ApprovalsWindow # Placeholder
from ui.advanced_search_window import AdvancedSearchWindow # Placeholder
from ui.chatbot_window import ChatbotWindow # Placeholder
from ui.zkteco_management_window import ZKTecoManagementWindow # Ensure this is imported
from ui.metrics_dashboard_window import MetricsDashboardWindow # Placeholder
from ui.task_management_window import TaskManagementWindow # Import the new TaskManagementWindow

from analytics.predictor import PredictiveAnalytics # Added import
logger = logging.getLogger(__name__)
# The previous debug log line is now part of the try-except block or can be removed
# if the print statement in the try-except block is sufficient for debugging.
# If tkb is None after the try-except, the earlier print would have shown it or an error.
# logger_main_gui.info(f"ttkbootstrap imported as tkb: {tkb}")

# --- GUI Class ---
class HRAppGUI:
    def __init__(self, main_tk_window: tk.Tk, parent_app_controller: 'ApplicationController'): # Renamed root to main_tk_window for clarity
        self.root = main_tk_window # This is the main Tk() instance
        self.parent_app = parent_app_controller  # This is the ApplicationController instance

        # Initialize theme based on ApplicationController's state
        # Default to 'light' if parent_app or its theme info isn't fully set up yet
        self.current_theme = "light"
        if self.parent_app and hasattr(self.parent_app, 'get_current_theme'):
            # This might be too early if parent_app's theme relies on DB settings not yet loaded by HRAppGUI
            pass # current_theme will be set properly after style initialization

        self.main_notebook = None # Initialize main notebook attribute
        self.style = tkb.Style() # Create the Style object once
        # --- Robust Style Initialization ---
        if self.style.theme is None:
            logger.critical("Default ttkbootstrap theme (e.g., litera) failed to load during Style object initialization.")
            logger.info("Attempting to explicitly load 'clam' into the Style object.")
            try:
                self.style.load_theme("clam") # This method sets self.style.theme
                if self.style.theme is None:
                    logger.critical("Style.load_theme('clam') also failed. Theming will be severely impacted.")
                else:
                    logger.info(f"Successfully loaded 'clam' into Style object. Current Style theme: {self.style.theme.name}")
                    # Try to apply it to Tk as well, so Tk knows a theme is active
                    self.style.tk.call("ttk::style", "theme", "use", "clam")
                    logger.info("Applied 'clam' to Tk via ttk::style theme use as initial fallback.")
            except Exception as e_load_clam:
                logger.critical(f"Exception trying to load/apply 'clam' as initial theme for Style object: {e_load_clam}")
        else:
            logger.info(f"ttkbootstrap.Style initialized successfully with theme: {self.style.theme.name}")

        # Determine self.current_theme (string name for our app's logic like "light" or "dark")
        default_theme_db_setting = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_THEME, "light") 
        self.current_theme = default_theme_db_setting if default_theme_db_setting in ["light", "dark"] else "light"
        logger.info(f"HRAppGUI initial current_theme (string for app logic): {self.current_theme}")
        
        self.active_toplevels: List[ThemedToplevel] = []
        self.task_queue = queue.Queue()  # For threaded tasks

        # --- Main Window Setup ---
        self.root.title(_("app_title"))
        self.root.geometry("1300x900") # Slightly larger for more content
        # Load the default theme setting from the database
        default_theme_db = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_THEME, "light")
        self.current_theme = default_theme_db if default_theme_db in ["light", "dark"] else "light"
        logger.info(f"Initial theme set to: {self.current_theme} from DB/default.")
        # --- Initialize UI Elements ---
        # Most UI elements are created in _setup_main_ui, called below.
        # Ensure critical attributes are initialized before _setup_main_ui if it uses them.
        # For Device Sync Panel
        self.device_name_var = tk.StringVar(value="Biometric Device 01") # Default, can be from config
        self.last_sync_var = tk.StringVar(value="N/A")
        self.translatable_widgets = [] # For i18n
        self.device_status_var = tk.StringVar(value="❓ Unknown") # Also uncomment related vars if needed
        self.sync_message_var = tk.StringVar(value="Ready.")     # Also uncomment related vars if needed
        self.sync_log_data = [] # Stores tuples of (timestamp, status, message)
        self.auto_sync_enabled_var = tk.BooleanVar(value=False) # Placeholder for auto-sync
        # Attributes for storing after IDs for recurring tasks
        self.zk_sync_after_id: Optional[str] = None
        self.csv_export_after_id: Optional[str] = None
        # --- Build the Main UI ---
        # This method should create all the frames, widgets, etc.
        self._setup_main_ui()
        self.root.update_idletasks() # Ensure UI creation tasks are processed before scheduling theme

        # Initialize trackers for other modal windows
        self.parent_app.active_reports_window = None
        self.parent_app.active_payroll_window = None
        self.parent_app.active_alerts_window = None
        self.parent_app.active_dashboard_window = None
        self.parent_app.active_settings_window = None
        self.parent_app.active_attendance_log_viewer_window = None
        
        self.parent_app.active_about_dialog = None

        # The initial theme application is now handled by ApplicationController._apply_initial_theme
        # which is called via self.root.after_idle from ApplicationController.__init__.
        # This ensures HRAppGUI is fully constructed.
        
        # If ApplicationController._apply_initial_theme is correctly calling self.hr_app_gui.apply_instance_theme,
        # then this explicit call in HRAppGUI.__init__ is not needed.
        
        self.show_employee_details_view() # Set default view
        self.gui_show_all_employees()  # Load initial employee data into the treeview
        self._bind_shortcuts()         # Setup keyboard shortcuts
        self._update_stats_summary()   # Load initial stats
        self._apply_role_permissions() # Apply UI changes based on user role

    def _setup_main_ui(self):
        """Sets up the main UI layout and components."""
        
        # --- Sidebar Navigation ---
        self.sidebar_frame = ttk.Frame(self.root, width=180, relief="raised", borderwidth=1) # Adjust width as needed
        self.sidebar_frame.pack(side="left", fill="y", padx=(5,0), pady=5) # Pad on left and top/bottom
        self._create_sidebar_navigation(self.sidebar_frame) # Pass the sidebar frame as parent

        # --- Main Content Area (PanedWindow for resizable sections) ---
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(side="left", fill="both", expand=True, padx=5, pady=5) # Pack next to sidebar

        # --- Left Pane (Employee List, Search, Actions) ---
        self.left_pane_frame = ttk.Frame(self.main_paned_window, padding="5")
        self.main_paned_window.add(self.left_pane_frame, weight=1) 
        self._create_employee_list_and_search_frame(self.left_pane_frame)

        # --- Right Pane (Employee Details Form / Other Views) ---
        # This frame will be cleared and repopulated by view-switching methods
        self.main_display_area = ttk.Frame(self.main_paned_window, padding="5")
        self.main_paned_window.add(self.main_display_area, weight=2) # Initial weight
        # --- Main Notebook for Views ---
        self.main_notebook = ttk.Notebook(self.main_display_area)
        self.main_notebook.pack(expand=True, fill="both")

        # --- Create View Frames ---
        self.employee_details_frame = ttk.Frame(self.main_notebook, padding="0") # No padding here, internal notebook has padding
        # self.search_view_frame = ttk.Frame(self.main_notebook, padding="10") # REMOVED Search Tab Frame # This line is correct
        # self.dashboard_view_frame = ttk.Frame(self.main_notebook, padding="10") # REMOVED Dashboard Tab Frame
        self.reports_view_frame = ttk.Frame(self.main_notebook, padding="10") # Reports opens a window, this tab might be placeholder or show summary
        # self.payroll_view_frame = ttk.Frame(self.main_notebook, padding="10") # REMOVED Payroll Tab Frame
        # self.alerts_view_frame = ttk.Frame(self.main_notebook, padding="10") # REMOVED Alerts Tab Frame
        self.analytics_view_frame = ttk.Frame(self.main_notebook, padding="10")
        self.user_admin_view_frame = ttk.Frame(self.main_notebook, padding="10")
        self.settings_view_frame = ttk.Frame(self.main_notebook, padding="10") # Settings opens a window
        self.device_sync_view_frame = ttk.Frame(self.main_notebook, padding="10") # New Device Sync Tab
        # self.employee_tasks_view_frame = ttk.Frame(self.main_notebook, padding="10") # REMOVED Tasks Tab
        self.metrics_view_frame = ttk.Frame(self.main_notebook, padding="10")
        self.interview_scheduling_view_frame = ttk.Frame(self.main_notebook, padding="10") # New Interview Scheduling Tab
        self.approvals_view_frame = ttk.Frame(self.main_notebook, padding="10") # New Approvals Tab
        self.fingerprint_analysis_tab = ttk.Frame(self.main_notebook, padding="10") # New Fingerprint Analysis Tab
        # --- Add Frames as Tabs with Translatable Text ---
        self.main_notebook.add(self.employee_details_frame, text=_("main_tab_employees"))
        # self.main_notebook.add(self.dashboard_view_frame, text=_("main_tab_dashboard")) # REMOVED Dashboard Tab
        # self.main_notebook.add(self.reports_view_frame, text=_("main_tab_reports")) # REMOVED Reports Tab
        # self.main_notebook.add(self.payroll_view_frame, text=_("main_tab_payroll")) # REMOVED Payroll Tab
        # self.main_notebook.add(self.alerts_view_frame, text=_("main_tab_alerts")) # REMOVED Alerts Tab
        self.main_notebook.add(self.analytics_view_frame, text=_("main_tab_analytics"))
        # self.main_notebook.add(self.user_admin_view_frame, text=_("main_tab_user_admin"))
        # self.main_notebook.add(self.settings_view_frame, text=_("main_tab_settings")) # REMOVED Settings Tab
        self.main_notebook.add(self.device_sync_view_frame, text=_("main_tab_device_sync"))
        # self.main_notebook.add(self.employee_tasks_view_frame, text=_("main_tab_tasks")) # REMOVED Tasks Tab
        # self.main_notebook.add(self.metrics_view_frame, text=_("main_tab_metrics")) # REMOVED Metrics Tab
        # self.main_notebook.add(self.interview_scheduling_view_frame, text=_("main_tab_interview_scheduling")) # REMOVED Interview Scheduling Tab # This line is correct
        # self.main_notebook.add(self.approvals_view_frame, text=_("main_tab_approvals")) # REMOVED Approvals Tab
        self.main_notebook.add(self.fingerprint_analysis_tab, text=_("main_tab_fingerprint_analysis"))
        # --- Create Widgets for Each View (Called Once) ---
        self._create_employee_details_tab_content(self.employee_details_frame) # Content for the main "Employees" tab (now includes internal tabs)
        # self._create_dashboard_view_widgets(self.dashboard_view_frame) # REMOVED call to create dashboard view widgets
        # self.reports_view_frame is still created, so its content method is called.
        self._create_reports_view_widgets(self.reports_view_frame) # Reports UI (Placeholder)
        # self._create_alerts_view_widgets(self.alerts_view_frame) # REMOVED call to create alerts view widgets
        # self._create_payroll_view_widgets(self.payroll_view_frame) # REMOVED call to create payroll view widgets
        self._create_analytics_view_widgets(self.analytics_view_frame) # Analytics UI
        self._create_user_admin_widgets(self.user_admin_view_frame) # User Admin UI
        self._create_settings_view_widgets(self.settings_view_frame)
        self._create_device_sync_section(self.device_sync_view_frame) # Device Sync UI # Corrected
        # self._create_employee_tasks_view_widgets(self.employee_tasks_view_frame) # REMOVED - Tasks UI moved to its own window
        self._create_metrics_view_widgets(self.metrics_view_frame) # Content for the (now hidden) metrics frame
        self._create_interview_scheduling_view_widgets(self.interview_scheduling_view_frame) # Content for the (now hidden) interview scheduling frame
        self._create_fingerprint_analysis_tab_content(self.fingerprint_analysis_tab) # Create content for new tab
        self._create_approvals_view_widgets(self.approvals_view_frame) # Content for the (now hidden) approvals frame
        self.main_display_area.update_idletasks() # Update the area containing the notebook
        self.root.update_idletasks() # Update the root

        # Set default view
        
        self.parent_app.active_reports_window = None
        self.parent_app.active_payroll_window = None
        self.parent_app.active_alerts_window = None
        # --- Status Bar ---
        self._create_status_bar()
        self.refresh_ui_for_language() # Initial language setup for all translatable widgets
        # --- Status Bar ---
        self._create_status_bar()

    # Renamed from _create_top_bar_navigation
    def _create_sidebar_navigation(self, parent_frame): # parent_frame is self.sidebar_frame
        """Creates the sidebar navigation."""
        
        # Frame for the main navigation buttons, allows bottom frame to be separate
        nav_buttons_container = ttk.Frame(parent_frame)
        # Pack this container at the top, allow it to fill 'x' but not expand vertically beyond its content
        nav_buttons_container.pack(side="top", fill="x", expand=False, padx=2, pady=(5,0))

        # Define role permissions for navigation buttons
        # Map button key to a list of roles that can see/use it
        self.nav_button_permissions = {
            "nav_employees_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER, db_schema.ROLE_EMPLOYEE], # Corrected
            "nav_adv_search_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER, db_schema.ROLE_EMPLOYEE], # Corrected
            "nav_dashboard_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_reports_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_payroll_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_alerts_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_analytics_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_user_admin_btn_text": [db_schema.ROLE_ADMIN], # Corrected
            "nav_settings_btn_text": [db_schema.ROLE_ADMIN], # Corrected
            "nav_device_sync_btn_text": [db_schema.ROLE_ADMIN], # Corrected
            "nav_chatbot_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER, db_schema.ROLE_EMPLOYEE], # Corrected
            "nav_metrics_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_interview_scheduling_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Corrected
            "nav_dept_mgt_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # Added Department Management
            "nav_employee_tasks_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER, db_schema.ROLE_EMPLOYEE], # Corrected
            "nav_approvals_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER],  # Corrected
            "nav_skill_mgt_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # New
            "nav_training_dev_btn_text": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER], # New
            "about_dialog_title": [db_schema.ROLE_ADMIN, db_schema.ROLE_DEPT_MANAGER, db_schema.ROLE_EMPLOYEE], # Corrected
        }
        # Define navigation buttons with translation keys
        # Reordered for logical grouping
        nav_buttons_config = [
            # Group 1: Core Navigation & Data Entry
            ("nav_employees_btn_text", self.show_employee_details_view, db_schema.BS_PRIMARY_ACTION), # Employees
            ("nav_adv_search_btn_text", self._gui_open_advanced_search_window, db_schema.BS_PRIMARY_ACTION), # RE-ADDED Advanced Search Button
            # SEPARATOR
            # Group 2: Key HR Modules
            ("nav_dashboard_btn_text", self.show_dashboard_view, db_schema.BS_VIEW_EDIT),
            ("nav_reports_btn_text", self.show_reports_view, db_schema.BS_VIEW_EDIT),
            ("nav_payroll_btn_text", self.gui_show_payroll_window, db_schema.BS_VIEW_EDIT),
            ("nav_alerts_btn_text", self.show_alerts_view, db_schema.BS_VIEW_EDIT),
            ("nav_dept_mgt_btn_text", self.gui_show_department_management_window, db_schema.BS_VIEW_EDIT), # Added Department Management
            # SEPARATOR
            # Group 3: Operational & Advanced Modules
            ("nav_employee_tasks_btn_text", self.show_employee_tasks_view, db_schema.BS_VIEW_EDIT), # Tasks
            ("nav_interview_scheduling_btn_text", self.gui_show_interview_scheduling_window, db_schema.BS_VIEW_EDIT), # Interviews
            ("nav_analytics_btn_text", self.show_analytics_view, db_schema.BS_VIEW_EDIT),
            ("nav_skill_mgt_btn_text", self.gui_show_skill_management_window, db_schema.BS_VIEW_EDIT), # New Skill Mgt
            ("nav_training_dev_btn_text", self.gui_show_training_course_management_window, db_schema.BS_VIEW_EDIT), # New
            ("nav_metrics_btn_text", self.gui_show_metrics_dashboard_window, db_schema.BS_VIEW_EDIT), # Metrics
            # SEPARATOR
            # Group 4: System & Admin
            ("nav_device_sync_btn_text", self.show_device_sync_view, db_schema.BS_VIEW_EDIT), # Device Sync
            ("nav_user_admin_btn_text", self.show_user_admin_view, db_schema.BS_VIEW_EDIT), # User Admin (Style changed)
            ("nav_settings_btn_text", self.gui_show_app_settings_window, db_schema.BS_NEUTRAL),
            # SEPARATOR
            ("nav_approvals_btn_text", self.show_approvals_view, db_schema.BS_VIEW_EDIT), # New Approvals Button
            # Group 5: Help & Utility
            ("nav_chatbot_btn_text", self.gui_show_chatbot_window, db_schema.BS_LIGHT), # Chatbot
            ("about_dialog_title", self.gui_show_about_dialog, db_schema.BS_LIGHT), # About
        ]

        self.nav_buttons = {} # Store nav buttons for role permissions
        separator_keys = [
            "nav_adv_search_btn_text", # RE-ADDED to separator list
            "nav_alerts_btn_text", 
            "nav_dept_mgt_btn_text", # Add separator after Department Management
            "nav_metrics_btn_text",
            "nav_settings_btn_text",
            "nav_approvals_btn_text", # Add separator after approvals
            "nav_skill_mgt_btn_text", # Add separator after Skill Management
            "nav_training_dev_btn_text" # Add separator after Training & Dev
            ]

        for key, command, style in nav_buttons_config:
            btn = ttk.Button(nav_buttons_container, text=_(key), command=command, bootstyle=style) # width removed for fill="x"
            btn.pack(side="top", fill="x", padx=5, pady=3) # Pack vertically, fill width of sidebar
            self._add_translatable_widget(btn, key) # Add for language refresh
            self.nav_buttons[key] = btn # Store by key for role permissions

            # Add separator after specific buttons
            if key in separator_keys:
                sep = ttk.Separator(nav_buttons_container, orient=tk.HORIZONTAL) # Horizontal separator
                sep.pack(side="top", fill="x", pady=5, padx=5) # Fill x for horizontal line

            # Add tooltips for each button
            tooltip_text = ""
            if key == "nav_employees_btn_text": tooltip_text = _("tooltip_view_manage_employees")
            elif key == "nav_adv_search_btn_text": tooltip_text = _("tooltip_adv_search_employees") # RE-ADDED
            elif key == "nav_dashboard_btn_text": tooltip_text = _("tooltip_view_dashboard")
            elif key == "nav_reports_btn_text": tooltip_text = _("tooltip_generate_reports")
            elif key == "nav_payroll_btn_text": tooltip_text = _("tooltip_manage_payroll")
            elif key == "nav_alerts_btn_text": tooltip_text = _("tooltip_view_hr_alerts")
            elif key == "nav_analytics_btn_text": tooltip_text = _("tooltip_access_analytics")
            elif key == "nav_user_admin_btn_text": tooltip_text = _("tooltip_manage_users")
            elif key == "nav_settings_btn_text": tooltip_text = _("tooltip_configure_settings")
            elif key == "nav_device_sync_btn_text": tooltip_text = _("tooltip_sync_device_data")
            elif key == "nav_dept_mgt_btn_text": tooltip_text = _("tooltip_manage_departments") # Added tooltip
            elif key == "nav_chatbot_btn_text": tooltip_text = _("tooltip_open_chatbot")
            elif key == "nav_employee_tasks_btn_text": tooltip_text = _("tooltip_manage_tasks")
            elif key == "nav_metrics_btn_text": tooltip_text = _("tooltip_view_metrics")
            elif key == "nav_interview_scheduling_btn_text": tooltip_text = _("tooltip_manage_interviews")
            elif key == "nav_approvals_btn_text": tooltip_text = _("tooltip_manage_approvals") # TODO: Add translation key
            elif key == "nav_skill_mgt_btn_text": tooltip_text = _("tooltip_skill_mgt")
            elif key == "nav_training_dev_btn_text": tooltip_text = _("tooltip_training_dev")
            elif key == "about_dialog_title": tooltip_text = _("tooltip_show_about_program")
            
            
            if tooltip_text:
                ToolTip(btn, text=tooltip_text) # tooltip_text is already translated

        # --- Bottom Frame for Theme/Language Toggles ---
        # This frame will be packed at the bottom of the parent_frame (sidebar)
        bottom_controls_frame = ttk.Frame(parent_frame)
        bottom_controls_frame.pack(side="bottom", fill="x", pady=10, padx=2)

        # Theme Toggle Button
        # Text for this button is dynamic based on current_theme, handled in apply_instance_theme
        self.theme_toggle_btn = ttk.Button(bottom_controls_frame, text=_("toggle_dark_mode_btn_text"), command=self.toggle_theme, bootstyle="info-outline")
        ToolTip(self.theme_toggle_btn, text=_("tooltip_toggle_theme"))
        self.theme_toggle_btn.pack(side="top", fill="x", padx=5, pady=2) # Pack vertically at bottom
        # Note: Theme toggle button text is handled by apply_instance_theme, not refresh_ui_for_language directly for its dynamic text.

        # Language Toggle Button
        self.lang_toggle_btn_main = ttk.Button(bottom_controls_frame, text=_("toggle_language_btn"), command=self.toggle_app_language, bootstyle="info-outline")
        self.lang_toggle_btn_main.pack(side="top", fill="x", padx=5, pady=2) # Pack vertically at bottom
        # This button's text is handled by refresh_ui_for_language as it's a static key.
        self._add_translatable_widget(self.lang_toggle_btn_main, "toggle_language_btn")


    def _create_employee_list_and_search_frame(self, parent_frame):
        """Creates the content for the left pane (list, search, actions)."""
        # Search Controls Section
        search_frame_key = "search_filter_frame_title"
        search_frame = ttk.LabelFrame(parent_frame, text=_(search_frame_key), padding="5")
        search_frame.pack(fill="x", pady=(0, 5))
        self._add_translatable_widget(search_frame, search_frame_key)
        self._create_search_controls(search_frame) # search_term_entry is created here

        # Employee List (Treeview) Section
        # --- Miniature Statistics Display ---
        stats_frame_key = "stats_summary_frame_title"
        stats_frame = ttk.LabelFrame(parent_frame, text=_(stats_frame_key), padding="5")
        stats_frame.pack(fill="x", pady=(0, 5))
        self._add_translatable_widget(stats_frame, stats_frame_key)
        self._create_stats_summary_widgets(stats_frame) # Key needed if text is static
        list_frame_key = "employee_list_frame_title"
        list_frame = ttk.LabelFrame(parent_frame, text=_(list_frame_key), padding="5")
        self._add_translatable_widget(list_frame, list_frame_key)

        # --- Miniature Statistics Display ---
        # Moved above the list frame
        list_frame.pack(fill="both", expand=True, pady=5)
        self._create_employee_list_widgets(list_frame) # self.tree is created here

        # Action Buttons below the Treeview
        table_actions_frame_key = "employee_actions_table_frame_title"
        table_actions_frame = ttk.LabelFrame(parent_frame, text=_(table_actions_frame_key), padding="5")
        table_actions_frame.pack(fill="x", pady=5)
        self._add_translatable_widget(table_actions_frame, table_actions_frame_key)
        self._create_table_action_buttons(table_actions_frame)
        # --- Miniature Statistics Display ---
        stats_frame_key = "stats_summary_frame_title"
        stats_frame = ttk.LabelFrame(parent_frame, text=_(stats_frame_key), padding="5")
        stats_frame.pack(fill="x", pady=(0, 5))
        self._add_translatable_widget(stats_frame, stats_frame_key)
        # Import/Export Section (Moved under table actions for better grouping)
        # io_frame = ttk.LabelFrame(parent_frame, text="Data Import/Export", padding="5")
        # io_frame.pack(fill="x", pady=5)
        # self._create_import_export_buttons(io_frame) # Buttons are now part of table_actions_frame

        # Attendance Controls Section (for selected employee from table) - Stays in left pane
        attendance_frame_key = "selected_employee_actions_frame_title"
        attendance_frame = ttk.LabelFrame(parent_frame, text=_(attendance_frame_key), padding="5")
        attendance_frame.pack(fill="x", pady=(5,0)) # Reduced bottom padding if device_sync_frame is next
        self._add_translatable_widget(attendance_frame, attendance_frame_key)
        self._create_attendance_controls(attendance_frame) # Device sync buttons removed from here
        # Miniature Statistics Display (Moved here from _create_employee_list_and_search_frame)
        # stats_frame_key = "stats_summary_frame_title"
        # stats_frame = ttk.LabelFrame(parent_frame, text=_(stats_frame_key), padding="5")
        # stats_frame.pack(fill="x", pady=(0, 5))

    def _create_employee_details_tab_content(self, parent_frame):
        """Creates the content for the main 'Employees' tab, which is now an internal notebook."""
        self.employee_details_notebook = ttk.Notebook(parent_frame)
        self.employee_details_notebook.pack(expand=True, fill="both", padx=5, pady=5) # Add padding here

        # Add tabs
        self._create_employee_general_details_tab(self.employee_details_notebook, "emp_details_tab_general_info")
        self._create_employee_attendance_tab(self.employee_details_notebook, "emp_details_tab_attendance")
        self._create_employee_payroll_tab(self.employee_details_notebook, "emp_details_tab_payroll")
        self._create_employee_documents_tab(self.employee_details_notebook, "emp_details_tab_documents")
        self._create_employee_action_log_tab(self.employee_details_notebook, "emp_details_tab_action_log")


        # Bind tab change event to load data dynamically
        self.employee_details_notebook.bind("<<NotebookTabChanged>>", self._on_employee_details_tab_changed)

        # Add Manage Leave button here, as it's related to the selected employee details
        leave_button_frame = ttk.Frame(parent_frame) # Frame to hold the button
        leave_button_frame.pack(fill="x", pady=5)
        self._create_leave_management_button_in_employee_view(leave_button_frame)


    def _create_status_bar(self):
        """Creates the status bar at the bottom of the window."""
        self.status_bar_frame = ttk.Frame(self.root, padding=(5, 2), relief="sunken")
        self.status_bar_frame.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value=_("status_bar_ready_text")) # Use translation key
        # The status_var itself will be updated with dynamic text, so the label doesn't need a static key.
        # However, its initial value can be translated.
        status_label = ttk.Label(self.status_bar_frame, textvariable=self.status_var, anchor="w") # No key needed here as text is dynamic
        status_label.pack(side="left", fill="x", expand=True) # Allow label to expand

        # Add a progress bar to the status bar for general operations like export
        self.export_progress_bar = ttk.Progressbar(self.status_bar_frame, mode="determinate", length=150)
        self.export_progress_bar.pack(side="right", padx=5) # Pack to the right of the status label
        # status_label.pack(fill="x") # Already packed above
        # If we wanted the "Status:" prefix to be translatable and static, we'd need a separate label.

    def gui_show_full_profile(self):
        """Opens the EmployeeProfileWindow (modal) for the selected employee."""
        # This method remains to open the dedicated modal window, which might have
        # additional features or a different layout than the main GUI tabs.
        # The content of this window might overlap with the main GUI tabs.
        # If the goal is to *replace* the modal window with tabs in the main GUI,
        # this method would be removed, and double-clicking/view profile button
        # would simply select the employee in the tree and switch to the main "Employees" tab.
        # For now, keeping it as a separate "full profile" view.

        
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showwarning("View Profile", "Please select an employee from the list first.", parent=self.root)
            return
        
        # Delegate to ApplicationController
        self.parent_app._create_and_show_toplevel(
            EmployeeProfileWindow, 
            employee_id=emp_id, 
            tracker_attr_name=f"active_employee_profile_window_{emp_id}" # Make tracker unique per employee
        )

    def _show_employee_qr_code(self):
        """Shows the QR code for the selected employee's ID in a new window."""
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id: # If still no emp_id
            messagebox.showwarning(_("qr_code_title"), _("select_employee_warning"), parent=self.root)
            return

        # Use ApplicationController to create this simple Toplevel if it needs consistent theming/tracking
        # For a very simple, non-tracked window like this, direct instantiation might be okay,
        # but for consistency, let's consider if it should be managed.
        # For now, keeping direct instantiation as it's not a major tracked window.
        qr_window = ThemedToplevel(self.root, self.parent_app) 
        qr_window.title(_("qr_code_window_title_specific", emp_id=emp_id))
        qr_window.geometry("300x350") # Adjusted for save button

        # Generate QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(emp_id) # Data to encode
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert PIL image to PhotoImage for Tkinter
        # Resize for display if too large, make sure it fits 250x250
        img.thumbnail((250, 250), Image.Resampling.LANCZOS) # Resize in place
        qr_photo_image = ImageTk.PhotoImage(img)

        qr_label = ttk.Label(qr_window, image=qr_photo_image)
        qr_label.image = qr_photo_image # Keep a reference!
        qr_label.pack(pady=10)

        ttk.Label(qr_window, text=_("qr_code_employee_id_label", emp_id=emp_id)).pack(pady=5)

        def save_qr():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                title=_("qr_code_save_dialog_title_specific", emp_id=emp_id),
                initialfile=f"{emp_id}_qr.png",
                parent=qr_window # Parent dialog to QR window
            )
            if filepath: img.save(filepath)

        save_button = ttk.Button(qr_window, text=_("qr_code_save_button"), command=save_qr, bootstyle=BS_ADD)
        save_button.pack(pady=10)

    def _clear_main_display_area(self):
        """Clears all widgets from the main_display_area (right pane)."""
        for widget in self.main_display_area.winfo_children():
            widget.destroy()

    def show_employee_details_view(self):
        """Switches the main_display_area to show the employee details form."""
        self.main_notebook.select(self.employee_details_frame) # Select the main "Employees" tab
        # If an employee was selected in the tree, re-populate the form
        if self.tree.selection():
            self.on_tree_select(None) # Trigger re-population of the internal tabs
        
    def show_analytics_view(self):
        """Switches to the Analytics view tab."""
        if self.main_notebook: self.main_notebook.select(self.analytics_view_frame)

    def show_device_sync_view(self):
        """Switches to the Device Sync view tab.
        AdvancedSearchWindow is opened from the sidebar.
        For now, assuming the "Advanced Search" button in sidebar opens it.
        """
        # self.parent_app._create_and_show_toplevel(AdvancedSearchWindow, tracker_attr_name="active_advanced_search_window")
        self.main_notebook.select(self.device_sync_view_frame)

    def show_employee_tasks_view(self):
        """Opens the Task Management window."""
        self.parent_app._create_and_show_toplevel(
            TaskManagementWindow, tracker_attr_name="active_task_management_window"
        )
    
    def show_interview_scheduling_view(self): # Renamed from gui_show_interview_scheduling_window
        """Opens the dedicated Interview Scheduling window."""
        
        self.gui_show_interview_scheduling_window() # Opens the dedicated window

    def show_approvals_view(self):
        """Opens the Approvals window."""
        self.gui_show_approvals_window()

    def show_metrics_view(self):
        """Switches to the Metrics view tab and opens the dedicated window."""
        
        self.gui_show_metrics_dashboard_window() # Directly open the window

    def show_settings_view(self):
         """Opens the dedicated Settings window.""" # Changed description
        
         self.gui_show_app_settings_window() # Directly open the window

    def gui_show_chatbot_window(self):
        """Opens the Chatbot Assistant window.""" # This line is correct
        # Delegate to ApplicationController # This line is correct
        self.parent_app._create_and_show_toplevel(
            ChatbotWindow, 
            tracker_attr_name="active_chatbot_window"
        )

    def show_reports_view(self):
        """Switches to the Reports view tab and opens the dedicated window."""
        
        self.gui_show_reports_window() # Directly open the window, no tab selection needed

    def _gui_show_attrition_predictions(self):
        """Updates the analytics view with current attrition model status/predictions.""" # This line is correct
        try: # Add try block here # This line is correct
            self.attrition_predictions_text.config(state="normal")
            self.attrition_predictions_text.delete("1.0", tk.END)
            
            if hasattr(self.parent_app, 'predictor') and self.parent_app.predictor and self.parent_app.predictor.attrition_model:
                self.attrition_predictions_text.insert(tk.END, "Attrition model is trained.\n\n")
                # TODO: Implement logic to get predictions for active employees and display them
                # Example placeholder (corrected):
                # active_employees_df = self.parent_app.predictor._get_historical_data_for_attrition() # Or a dedicated method
                # active_employees_df = active_employees_df[active_employees_df[db_schema.COL_EMP_STATUS] == db_schema.STATUS_ACTIVE].copy()
                # if not active_employees_df.empty:
                #     predictions = self.parent_app.predictor.predict_employee_attrition(active_employees_df)
                #     self.attrition_predictions_text.insert(tk.END, "Predictions for Active Employees (Probability of Leaving):\n")
                #     for i, emp_id in enumerate(active_employees_df[db_schema.COL_EMP_ID]):
                #         self.attrition_predictions_text.insert(tk.END, f"- {emp_id}: {predictions[i]:.2f}\n")
            # No specific exceptions are caught here, but the finally block will always execute.
        finally: # This line is correct
            self.root.after(0, lambda: self.root.config(cursor="")) # Reset cursor

    def _gui_train_attrition_model(self):
        if not hasattr(self.parent_app, 'predictor') or self.parent_app.predictor is None:
            self.parent_app.predictor = PredictiveAnalytics()

        if hasattr(self.parent_app, 'predictor') and self.parent_app.predictor and self.parent_app.predictor.attrition_model:
            self.attrition_predictions_text.insert(tk.END, "Attrition model is trained.\nPrediction display for active employees is a future step.")
        else:
            self.attrition_predictions_text.insert(tk.END, "Attrition model not trained yet or training failed.")
        self.attrition_predictions_text.config(state="disabled")

        # Define the worker function *inside* the GUI method
        def _train_in_thread():
            try:
                self.root.after(0, lambda: self.status_var.set("Attrition model training in progress..."))
                self.parent_app.predictor.train_attrition_model()
                # Use self.root.after to schedule GUI updates on the main thread
                self.root.after(0, lambda: self.status_var.set("Attrition model training finished successfully."))
                self.root.after(0, lambda: messagebox.showinfo("Training Complete", "Attrition model training finished.", parent=self.root))
                self.root.after(0, self._gui_show_attrition_predictions) # Update display after training
            except Exception as e:
                error_message_for_status = f"Attrition model training failed: {type(e).__name__}"
                logger.error(f"Attrition model training error: {e}")
                self.root.after(0, lambda msg=error_message_for_status: self.status_var.set(msg))
                self.root.after(0, lambda err_str=str(e): messagebox.showerror("Training Error", f"Failed to train attrition model: {err_str}", parent=self.root))
            finally:
                self.root.after(0, lambda: self.root.config(cursor="")) # Reset cursor

        # Code that runs on the main GUI thread to start the process
        self.root.config(cursor="watch") # Indicate processing
        messagebox.showinfo("Training", "Attrition model training started. This might take a moment.", parent=self.root)
        self.status_var.set("Attrition model training started...")
        thread = threading.Thread(target=_train_in_thread, daemon=True)
        thread.start()

    # New method to create the Leave Management button in the Employee view
    def _create_leave_management_button_in_employee_view(self, parent_frame): # This button is now in the Employee Details tab
        btn_key = "manage_leave_button_text"
        self.manage_vacations_btn_employee_view = ttk.Button(parent_frame, text=_(btn_key), command=self.gui_show_vacation_management_window, bootstyle=db_schema.BS_VIEW_EDIT, state="disabled")
        self.manage_vacations_btn_employee_view.pack(side="left", padx=10, pady=5) 
        self._add_translatable_widget(self.manage_vacations_btn_employee_view, btn_key)
        ToolTip(self.manage_vacations_btn_employee_view, text=_( "tooltip_manage_leave"))
    
    def clear_input_fields(self, clear_id=True):
        """Clears input fields in the HRAppGUI, primarily the left-pane search."""
        if hasattr(self, 'left_pane_search_term_entry') and self.left_pane_search_term_entry.winfo_exists(): # pragma: no cover
            self.left_pane_search_term_entry.delete(0, tk.END)
        
        if hasattr(self, 'left_pane_search_field_combo') and self.left_pane_search_field_combo.winfo_exists(): # pragma: no cover
            self.left_pane_search_field_combo.set(db_schema.COL_EMP_NAME) # Corrected
        # The read-only display fields are cleared by _reset_selection_dependent_ui

    def _create_readonly_detail_widgets(self, parent_frame):
        """Creates the read-only employee details display widgets for the General Info tab."""
        # This method is now used to create the content for the "General Info" tab within the internal notebook
        canvas = tk.Canvas(parent_frame, borderwidth=0, highlightthickness=0) # highlightthickness=0 can also be used
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        
        # This frame will contain all the actual employee data widgets
        scrollable_inner_frame = ttk.Frame(canvas, padding="5") # Ensure this line is present and correctly placed

        scrollable_inner_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # This method now sets up read-only display fields.
        # Store references to these labels to update them in on_tree_select
        self.readonly_labels = {} 
        # Note: The labels created here (e.g., "Personal Information") are LabelFrames.
        # The field labels (e.g., "ID:", "Name:") are ttk.Labels.
        # Define the layout for the General Info tab      
        fields_config = [
            ("personal_info_section_title", [
                (_("employee_id_label"), db_schema.COL_EMP_ID), # Corrected
                (_("name_label"), db_schema.COL_EMP_NAME), # Corrected
                (_("marital_status_icon_label"), db_schema.COL_EMP_MARITAL_STATUS), # Corrected
                (_("gender_icon_label"), db_schema.COL_EMP_GENDER), # Corrected
            ]),
            ("personal_info_section_title", [ # Re-using key for another section under same title if desired, or use new key
                (_("phone_icon_label"), db_schema.COL_EMP_PHONE), # Corrected
                (_("email_icon_label"), db_schema.COL_EMP_EMAIL), # Corrected
            ]),
            ("job_details_section_title", [
                (_("department_icon_label"), "department_name"), # Use string key for department name
                (_("position_icon_label"), db_schema.COL_EMP_POSITION), # Corrected
                (_("salary_icon_label"), db_schema.COL_EMP_SALARY), # Corrected
                (_("start_date_icon_label"), db_schema.COL_EMP_START_DATE), # Corrected
                (_("status_icon_label"), db_schema.COL_EMP_STATUS), # Corrected
                (_("termination_date_icon_label"), db_schema.COL_EMP_TERMINATION_DATE), # Corrected

            ]),
            ("benefits_device_section_title", [
                (_("vacation_days_icon_label"), db_schema.COL_EMP_VACATION_DAYS), # Corrected
                (_("exclude_vacation_policy_icon_label"), "exclude_vacation_policy"),
                (_("device_user_id_icon_label"), db_schema.COL_EMP_DEVICE_USER_ID), # Corrected
            ]),
            ("qualifications_history_section_title", [
                (_("education_icon_label"), db_schema.COL_EMP_EDUCATION), # Corrected
                # Employment history might be too long for a simple label, consider a Text widget or separate view
            ]),
        ]

        for section_title_key, fields in fields_config:
            section_frame = ttk.LabelFrame(scrollable_inner_frame, text=_(section_title_key), padding="10")
            section_frame.pack(fill="x", pady=5, padx=5)
            section_frame.columnconfigure(1, weight=1)
            self._add_translatable_widget(section_frame, section_title_key) # For the LabelFrame title

            for i, (label_text_from_config, data_key_from_config) in enumerate(fields):
                    # label_text_from_config is already the result of _(key) or a static string
                    lbl_widget = ttk.Label(section_frame, text=label_text_from_config)
                    lbl_widget.grid(row=i, column=0, sticky="w", padx=5, pady=2)
                    # The label_text_from_config itself is the translated string. If the key used to get it
                    # was, e.g., "marital_status_icon_label", then that key is what would be used for re-translation.
                    # Since _() is called directly in fields_config, these labels will update if their source keys are translated.
                    value_var = tk.StringVar(value="N/A")
                    
                    value_label = ttk.Entry(section_frame, textvariable=value_var, state="readonly", width=40)
                    value_label.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
                    self.readonly_labels[data_key_from_config] = value_var # Use data_key_from_config
        
        # Special handling for multi-line fields like Employment History
        hist_frame_key = "emp_hist_section_title"
        hist_frame = ttk.LabelFrame(scrollable_inner_frame, text=_(hist_frame_key), padding="10")
        hist_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(hist_frame, hist_frame_key)
        self.readonly_employment_history_text = tk.Text(hist_frame, height=5, width=50, relief="solid", borderwidth=1, state="disabled", wrap="word") # Hardcoded width
        self.readonly_employment_history_text.pack(fill="x", expand=True, pady=5)
        # Apply theme to this Text widget
        palette = get_theme_palette_global(self.current_theme)
        _theme_text_widget_global(self.readonly_employment_history_text, palette)

        # Photo Preview (remains in the read-only display)
        photo_frame_key = "photo_section_title"
        photo_frame = ttk.LabelFrame(scrollable_inner_frame, text=_(photo_frame_key), padding="10")
        photo_frame.pack(pady=5, padx=5)
        self._add_translatable_widget(photo_frame, photo_frame_key)
        self.readonly_photo_preview_label = ttk.Label(photo_frame, text=_("no_photo_text"), relief="groove", anchor="center")
        self._add_translatable_widget(self.readonly_photo_preview_label, "no_photo_text")
        self.readonly_photo_preview_label.pack(pady=5)
        self._readonly_photo_image_ref = None # For the read-only display

# Add Manage Leave button here, as it's related to the selected employee details
        # --- Recommendations & Alerts Section ---
        self._create_recommendations_section(scrollable_inner_frame)

    def _create_recommendations_section(self, parent_frame):
        """Creates the section for recommendations and alerts within the General Info tab."""
        reco_frame_key = "recommendations_alerts_frame_title"
        reco_frame = ttk.LabelFrame(parent_frame, text=_(reco_frame_key), padding="10")
        reco_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(reco_frame, reco_frame_key)

        self.recommendations_text = tk.Text(reco_frame, height=4, wrap="word", relief="solid", borderwidth=1, state="disabled")
        self.recommendations_text.pack(fill="x", expand=True, pady=5)
        # Apply theme to Text widget
        palette = get_theme_palette_global(self.current_theme)
        _theme_text_widget_global(self.recommendations_text, palette)

    # --- Documents Section (Moved from EmployeeProfileWindow) ---
    def _create_documents_section(self, parent_tab):
        """Creates the UI for the Documents tab/section."""
        doc_main_frame = ttk.LabelFrame(parent_tab, text=_("profile_doc_section_title"), padding="10")
        doc_main_frame.pack(fill="both", expand=True); self._add_translatable_widget(doc_main_frame, "profile_doc_section_title")

        doc_actions_frame = ttk.Frame(doc_main_frame)
        doc_actions_frame.pack(side="top", fill="x", pady=5) # Added missing pack

        self.view_doc_btn = ttk.Button(doc_actions_frame, text=_("profile_doc_view_btn"), command=self._gui_view_document, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.view_doc_btn.pack(side="left", padx=5) # Corrected

        self._add_translatable_widget(self.view_doc_btn, "profile_doc_view_btn")

        self.delete_doc_btn = ttk.Button(doc_actions_frame, text=_("profile_doc_delete_btn"), command=self._gui_delete_document, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH) # Corrected
        self.delete_doc_btn.pack(side="left", padx=5) # Added missing pack

        self._add_translatable_widget(self.delete_doc_btn, "profile_doc_delete_btn")

        self.add_doc_btn = ttk.Button(doc_actions_frame, text=_("profile_doc_add_btn"), command=self._gui_add_document_for_selected_employee, bootstyle=db_schema.BS_ADD) # Corrected command
        self.add_doc_btn.pack(side="right", padx=5) # Changed side to right # Added missing pack
        self._add_translatable_widget(self.add_doc_btn, "profile_doc_add_btn")

        self.sign_doc_btn = ttk.Button(doc_actions_frame, text=_("profile_doc_sign_btn"), command=self._gui_sign_document, state="disabled", bootstyle="success")
        # --- New Contract Button ---
        self.create_contract_btn = ttk.Button(doc_actions_frame, text=_("profile_doc_create_contract_btn"), command=self._gui_create_new_contract, bootstyle=db_schema.BS_ADD) # Corrected
        self.create_contract_btn.pack(side="right", padx=5) # Placed after Add Document # Added missing pack
        self._add_translatable_widget(self.create_contract_btn, "profile_doc_create_contract_btn")
        if not fitz: # If fitz is not imported
            self.sign_doc_btn.config(state="disabled")
            ToolTip(self.sign_doc_btn, text="PDF signing library (PyMuPDF) not installed.")
        self.sign_doc_btn.pack(side="left", padx=5) # Placed after delete, before add
        self._add_translatable_widget(self.sign_doc_btn, "profile_doc_sign_btn")
        
        # Treeview for documents
        doc_list_frame = ttk.Frame(doc_main_frame) # Added missing parent
        doc_list_frame.pack(fill="both", expand=True, pady=5)

        self.doc_tree_cols = ("doc_id_display", db_schema.COL_DOC_TYPE, "filename", db_schema.COL_DOC_UPLOAD_DATE)
        self.doc_tree = ttk.Treeview(doc_list_frame, columns=self.doc_tree_cols, show="headings")
        self._update_doc_tree_headers() # Set initial headers

        self.doc_tree.column("doc_id_display", width=60, anchor="e", stretch=tk.NO)
        self.doc_tree.column(db_schema.COL_DOC_TYPE, width=150)
        self.doc_tree.column("filename", width=250, stretch=tk.YES)
        self.doc_tree.column(db_schema.COL_DOC_UPLOAD_DATE, width=120, anchor="center")

        doc_scrollbar = ttk.Scrollbar(doc_list_frame, orient="vertical", command=self.doc_tree.yview)
        self.doc_tree.configure(yscrollcommand=doc_scrollbar.set)
        self.doc_tree.pack(side="left", fill="both", expand=True)
        doc_scrollbar.pack(side="right", fill="y")

        self.doc_tree.bind("<<TreeviewSelect>>", self._on_document_tree_select)

        # Add drag and drop binding to the treeview
        # Note: This requires a library like tkdnd for cross-platform file drops from OS # Added missing comment
        # Standard Tkinter <Drop> might not work as expected.
        # self.doc_tree.bind("<Drop>", self._handle_document_drop) # Disabled unsupported event

    def _update_doc_tree_headers(self): # Renamed from _update_doc_tree_headers_main_gui
        """Updates the headers of the main GUI's document treeview."""
        if hasattr(self, 'doc_tree') and self.doc_tree.winfo_exists():
            self.doc_tree.heading("doc_id_display", text=_("profile_doc_id_header"))
            self.doc_tree.heading(db_schema.COL_DOC_TYPE, text=_("profile_doc_type_header")) # Corrected
            self.doc_tree.heading("filename", text=_("profile_doc_filename_header"))
            self.doc_tree.heading(db_schema.COL_DOC_UPLOAD_DATE, text=_("profile_doc_uploaded_header")) # Corrected


    def _load_documents_tab(self, emp_id: str):
        """Loads documents for the selected employee into the Documents tab."""
        # This method is now used for the Documents tab in the main GUI,
        # as well as potentially in the separate EmployeeProfileWindow if kept.
        if not hasattr(self, 'doc_tree') or not self.doc_tree.winfo_exists(): return # Treeview not created/visible
        for item in self.doc_tree.get_children():
            self.doc_tree.delete(item)
        try: # Corrected: Use db_queries alias
            documents = db_queries.get_employee_documents_db(emp_id) # Use the passed emp_id
            for doc in documents:
                filename = os.path.basename(doc[db_schema.COL_DOC_FILE_PATH])
                self.doc_tree.insert("", "end", values=(
                    doc[db_schema.COL_DOC_ID], doc[db_schema.COL_DOC_TYPE], filename, doc[db_schema.COL_DOC_UPLOAD_DATE]
                ), iid=doc[db_schema.COL_DOC_ID])
        except (DatabaseOperationError, EmployeeNotFoundError) as e:
            logger.error(f"Error loading documents for tab: {e}")
            # messagebox.showerror("Error Loading Documents", str(e), parent=self.root) # Avoid modal dialog
        self._on_document_tree_select() # Reset button states

    def _on_document_tree_select(self, event=None):
        is_selected = bool(self.doc_tree.selection())
        self.view_doc_btn.config(state="normal" if is_selected else "disabled")
        self.delete_doc_btn.config(state="normal" if is_selected else "disabled")
        can_sign = False
        if is_selected and fitz: # Only check if fitz is available
            selected_item_iid = self.doc_tree.focus()
            item_values = self.doc_tree.item(selected_item_iid, "values")
            # Values: doc_id, doc_type, filename, upload_date
            if item_values:
                doc_type = item_values[1]
                filename = item_values[2]
                if filename.lower().endswith(".pdf") and doc_type.lower() == "contract":
                    can_sign = True
        self.sign_doc_btn.config(state="normal" if can_sign else "disabled")

    def _handle_document_drop(self, event):
        """Handles files dropped onto the documents treeview."""
        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("Drop Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return # Should not happen if selected_item is valid

        # This is a placeholder. Extracting file paths from the event data
        # is highly dependent on the Tkinter version and platform, or requires tkdnd.
        # Assuming event.data contains a list of file paths (common with tkdnd)
        # If using standard Tkinter, event.data might be different. # This line is correct
        
        dropped_files = event.data.split() # Example: assuming space-separated paths
        if not dropped_files:
            logger.warning("No files found in drop event data.")
            return

        for filepath in dropped_files:
            if os.path.exists(filepath):
                # Trigger the add document process for each file
                # This will prompt for document type for each file
                self._gui_add_document(emp_id, initial_filepath=filepath) # Pass emp_id
            else:
                logger.warning(f"Dropped path does not exist: {filepath}")

    def _gui_add_document_for_selected_employee(self, initial_filepath: Optional[str] = None):
        """Helper to add a document for the currently selected employee in the main tree."""
        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("Add Document Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return # Should not happen if selected_item is valid
        # Open DocumentManagementWindow for the selected employee
        self.parent_app._create_and_show_toplevel(
            DocumentManagementWindow,
            employee_id=emp_id,
            tracker_attr_name=f"active_document_management_window_{emp_id}"
        )
        # The DocumentManagementWindow will handle the actual file dialog and DB addition.
        # If initial_filepath is provided, it could be passed to DocumentManagementWindow.

    # def _gui_add_document(self, emp_id: str, initial_filepath: Optional[str] = None): # This method is now effectively replaced
    #     """Handles adding a document for the selected employee, optionally starting with a pre-selected file."""
    #     # This logic is now primarily in DocumentManagementWindow
    #     # For HRAppGUI, it should open DocumentManagementWindow
    #     self.parent_app._create_and_show_toplevel(
    #         DocumentManagementWindow,
    #         employee_id=emp_id,
    #         # initial_filepath=initial_filepath, # Pass if DocumentManagementWindow supports it
    #         tracker_attr_name=f"active_document_management_window_{emp_id}"
    #     )
    def _gui_view_document(self):
        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid: return

        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("View Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return

        # Retrieve the full file path stored with the item
        # We need to fetch it from the DB again using doc_id, or store it in the tree (less ideal for full paths)
        try:
            # Assuming db_queries.get_employee_documents_db returns a list of dicts
            documents = db_queries.get_employee_documents_db(emp_id) # Use the selected emp_id
            doc_to_view = next((doc for doc in documents if str(doc[db_schema.COL_DOC_ID]) == selected_item_iid), None)
            if doc_to_view and os.path.exists(doc_to_view[db_schema.COL_DOC_FILE_PATH]):
                if os.name == 'nt': # Windows
                    os.startfile(doc_to_view[db_schema.COL_DOC_FILE_PATH])
                elif os.name == 'posix': # macOS, Linux
                    subprocess.call(('open', doc_to_view[db_schema.COL_DOC_FILE_PATH]) if sys.platform == 'darwin' else ('xdg-open', doc_to_view[db_schema.COL_DOC_FILE_PATH]))
            else:
                messagebox.showerror("Error", "Document file not found or path is invalid.", parent=self.root) # Use root as parent
        except Exception as e:
            logger.error(f"Error opening document: {e}")
            messagebox.showerror("Error", f"Could not open document: {e}", parent=self.root) # Use root as parent

    def _gui_delete_document(self):
        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid: return

        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("Delete Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return

        doc_id_to_delete = int(selected_item_iid) # IID is the doc_id

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this document?", parent=self.root): # Use root as parent
            try:
                db_queries.delete_employee_document_db(doc_id_to_delete)
                messagebox.showinfo("Success", "Document deleted successfully.", parent=self.root) # Use root as parent
                self._load_documents_tab(emp_id) # Refresh the documents tab for this employee
            except (FileNotFoundError, DatabaseOperationError) as e:
                messagebox.showerror("Error Deleting Document", str(e), parent=self.root) # Use root as parent

    def _gui_create_new_contract(self):
        """Opens the ElectronicContractWindow to create a new contract for the selected employee."""
        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("Contract Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return
        # Corrected: Use self.parent_app._create_and_show_toplevel
        self._create_and_show_toplevel(ElectronicContractWindow, employee_id=emp_id, tracker_attr_name="active_electronic_contract_window")
        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            employee_id=emp_id,
            # callback_on_save=lambda: self._load_documents_tab(emp_id), # Optional: refresh docs tab
            tracker_attr_name=f"active_electronic_contract_window_{emp_id}"
        )
    def _gui_sign_document(self):
        if not fitz:
            messagebox.showerror("Error", "PDF signing library (PyMuPDF) is not installed. This feature is unavailable.", parent=self.root) # Use root as parent
            return

        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid:
            messagebox.showerror("Error", "No document selected.", parent=self.root) # Use root as parent
            return

        selected_item = self.tree.focus() # Get selected employee from main tree
        if not selected_item:
            messagebox.showwarning("Signing Error", "Please select an employee first.", parent=self.root)
            return
        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return

        doc_id_to_sign = int(selected_item_iid)
        try:
            documents = db_queries.get_employee_documents_db(emp_id) # Use the selected emp_id
            doc_to_sign = next((doc for doc in documents if doc[db_schema.COL_DOC_ID] == doc_id_to_sign), None)
            if not doc_to_sign:
                messagebox.showerror("Error", "Selected document not found in database.", parent=self.root) # Use root as parent
                return

            pdf_path = doc_to_sign[db_schema.COL_DOC_FILE_PATH]
            if not pdf_path.lower().endswith(".pdf"): # Should be caught by button state, but double check
                messagebox.showerror("Error", "Selected document is not a PDF.", parent=self.root) # Use root as parent
                return

            doc_info = fitz.open(pdf_path)
            num_pages = len(doc_info)
            doc_info.close()

            page_num_str = simpledialog.askstring(
                "Page Number for Signature",
                f"Enter page number to place signature (1 to {num_pages}):",
                parent=self.root # Use root as parent
            )
            if not page_num_str: return
            try:
                page_num_to_sign = int(page_num_str) - 1 # Convert to 0-indexed
                if not (0 <= page_num_to_sign < num_pages):
                    messagebox.showerror("Error", f"Invalid page number. Must be between 1 and {num_pages}.", parent=self.root) # Use root as parent
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid page number entered.", parent=self.root) # Use root as parent
                return

            # Need to get signature image path from user input or a saved location
            signature_image_path = filedialog.askopenfilename(
                title="Select Signature Image File",
                filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
                parent=self.root # Use root as parent
            )
            if not signature_image_path: return

            embed_image_in_pdf(pdf_path, signature_image_path, page_num_to_sign, sig_width=100, sig_height=50, position="bottom-right")
            messagebox.showinfo("Success", "Document signed successfully. The original file has been updated.", parent=self.root) # Use root as parent
            # Optionally refresh the document list to show the modified date/time if needed
            self._load_documents_tab(emp_id)

        except Exception as e:
            logger.error(f"Error signing document: {e}", exc_info=True)
            messagebox.showerror("Signing Error", f"An error occurred while signing: {e}", parent=self.root) # Use root as parent

    # --- Action Log Section (Moved from EmployeeProfileWindow) ---
    def _create_action_log_section(self, parent_tab):
        """Creates the UI for the Action Log tab/section."""
        log_main_frame = ttk.Frame(parent_tab, padding="10")
        log_main_frame.pack(fill="both", expand=True) # Added missing pack

        # Treeview for action log
        log_list_frame = ttk.LabelFrame(log_main_frame, text=_("profile_action_log_section_title"), padding="10") # Added missing parent
        log_list_frame.pack(fill="both", expand=True, pady=5)

        self._add_translatable_widget(log_list_frame, "profile_action_log_section_title")
        self.action_log_tree_cols = ("timestamp", "action", "performed_by"); self.action_log_tree = ttk.Treeview(log_list_frame, columns=self.action_log_tree_cols, show="headings")
        self._update_action_log_tree_headers() # Set initial headers

        self.action_log_tree.column("timestamp", width=150, anchor="w")
        self.action_log_tree.column("action", width=350, stretch=tk.YES, anchor="w")
        self.action_log_tree.column("performed_by", width=150, anchor="w")

        log_scrollbar = ttk.Scrollbar(log_list_frame, orient="vertical", command=self.action_log_tree.yview)
        self.action_log_tree.configure(yscrollcommand=log_scrollbar.set)
        self.action_log_tree.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        # Data loading is handled by _load_action_log_tab when the tab is selected # Added missing comment
    def _update_action_log_tree_headers(self):
        if hasattr(self, 'action_log_tree') and self.action_log_tree.winfo_exists():
            self.action_log_tree.heading("timestamp", text=_("profile_action_log_timestamp_header"))
            self.action_log_tree.heading("action", text=_("profile_action_log_action_header"))
            self.action_log_tree.heading("performed_by", text=_("profile_action_log_performed_by_header"))

    def _load_action_log_tab(self, emp_id: str):
        """Loads action log for the selected employee into the Action Log tab."""
        # This method is now used for the Action Log tab in the main GUI,
        # as well as potentially in the separate EmployeeProfileWindow if kept.
        if not hasattr(self, 'action_log_tree') or not self.action_log_tree.winfo_exists(): return # Treeview not created/visible

        for item in self.action_log_tree.get_children():
            self.action_log_tree.delete(item)
        try:
            logs = db_queries.get_employee_action_log_db(emp_id) # Use the passed emp_id
            for log_entry in logs:
                timestamp_str = log_entry[COL_EAL_TIMESTAMP]
                try:
                    # Attempt to parse and reformat. If it's already a nice string, this might fail or be unnecessary.
                    timestamp_dt = datetime.fromisoformat(timestamp_str)
                    formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    formatted_timestamp = timestamp_str # Fallback to original if not ISO format
                self.action_log_tree.insert("", "end", values=(formatted_timestamp, log_entry[COL_EAL_ACTION_DESC], log_entry.get("performed_by_username", "System/Unknown")))
        except (DatabaseOperationError, EmployeeNotFoundError) as e:
            logger.error(f"Error loading action log for tab: {e}")
            # messagebox.showerror("Error Loading Action Log", str(e), parent=self) # Avoid modal dialog

    # Removed _load_action_log_to_tree as _load_action_log_tab serves the purpose
    def _create_employee_general_details_tab(self, parent_notebook, tab_text_key: str):
        """Creates the content for the 'General Info' tab."""
        tab_frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(tab_frame, text=_(tab_text_key))
        self._create_readonly_detail_widgets(tab_frame) # Reuse the readonly detail widgets creation

    def _create_employee_attendance_tab(self, parent_notebook, tab_text_key: str):
        """Creates the content for the 'Attendance' tab."""
        tab_frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(tab_frame, text=_(tab_text_key))

        # Reuse logic from AttendanceLogViewerWindow, but without the employee selection combo
        # The employee is already selected in the main treeview

        # --- Controls Frame (Date Range) ---
        controls_frame = ttk.Frame(tab_frame)
        controls_frame.pack(side="top", fill="x", pady=5)

        # TODO: Add translation keys for these labels
        ttk.Label(controls_frame, text="Period Start:").pack(side="left", padx=(0, 5))
        self.attendance_start_date_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.attendance_start_date_entry.date = dt_date.today().replace(day=1) # Default to start of month
        self.attendance_start_date_entry.pack(side="left", padx=5)

        ttk.Label(controls_frame, text="Period End (YYYY-MM-DD):").pack(side="left", padx=(10, 5))
        self.attendance_end_date_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.attendance_end_date_entry.date = dt_date.today() # Default to today
        self.attendance_end_date_entry.pack(side="left", padx=5)

        self.load_attendance_btn = ttk.Button(controls_frame, text="Load Attendance", command=self._refresh_attendance_log_for_selected_employee, bootstyle=db_schema.BS_VIEW_EDIT) # Corrected command
        self.load_attendance_btn.pack(side="left", padx=10)

        # --- Log Display Frame ---
        log_display_frame = ttk.LabelFrame(tab_frame, text="Attendance Records", padding="10")
        log_display_frame.pack(fill="both", expand=True, padx=0, pady=5) # No horizontal padding here

        self.attendance_log_tree_columns = ("date", "clock_in", "clock_out", "duration")
        self.attendance_log_tree = ttk.Treeview(log_display_frame, columns=self.attendance_log_tree_columns, show="headings")
        self.attendance_log_tree.heading("date", text="Date")
        self.attendance_log_tree.heading("clock_in", text="Clock In Time")
        self.attendance_log_tree.heading("clock_out", text="Clock Out Time")
        self.attendance_log_tree.heading("duration", text="Duration (Hours)")

        self.attendance_log_tree.column("date", anchor="w", width=100)
        self.attendance_log_tree.column("clock_in", anchor="center", width=150)
        self.attendance_log_tree.column("clock_out", anchor="center", width=150)
        self.attendance_log_tree.column("duration", anchor="e", width=120)
        self.attendance_log_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_display_frame, orient="vertical", command=self.attendance_log_tree.yview)
        self.attendance_log_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Summary Frame ---
        summary_frame = ttk.Frame(tab_frame, padding=(0, 5)) # No horizontal padding
        summary_frame.pack(side="bottom", fill="x", pady=(0, 5))
        self.attendance_total_hours_var = tk.StringVar(value="Total Hours Worked: N/A")
        ttk.Label(summary_frame, textvariable=self.attendance_total_hours_var).pack(side="left", padx=10)
        self.attendance_total_days_var = tk.StringVar(value="Total Days Present: N/A")
        ttk.Label(summary_frame, textvariable=self.attendance_total_days_var).pack(side="left", padx=10)

    def _create_employee_payroll_tab(self, parent_notebook, tab_text_key: str):
        """Creates the content for the 'Payroll' tab."""
        tab_frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(tab_frame, text=_(tab_text_key))
        # TODO: Add translation keys for LabelFrame and Treeview headers
        # Reuse logic from PayrollWindow, focusing on payslip viewing/history
        # Adding advances/rewards might remain in the separate PayrollWindow

        # --- Payslip History Treeview ---
        history_frame = ttk.LabelFrame(tab_frame, text="Payslip History", padding="10")
        history_frame.pack(fill="both", expand=True, padx=0, pady=5)

        self.payslip_history_tree_columns = (db_schema.COL_PAY_ID, db_schema.COL_PAY_PERIOD_START, db_schema.COL_PAY_PERIOD_END, db_schema.COL_PAY_NET_PAY, db_schema.COL_PAY_GENERATION_DATE)
        self.payslip_history_tree = ttk.Treeview(history_frame, columns=self.payslip_history_tree_columns, show="headings")
        self.payslip_history_tree.heading(db_schema.COL_PAY_ID, text="Payslip ID")
        self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_START, text="Period Start")
        self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_END, text="Period End")
        self.payslip_history_tree.heading(db_schema.COL_PAY_NET_PAY, text="Net Pay")
        self.payslip_history_tree.heading(db_schema.COL_PAY_GENERATION_DATE, text="Generated On")

        self.payslip_history_tree.column(db_schema.COL_PAY_ID, width=80, anchor="e", stretch=tk.NO)
        self.payslip_history_tree.column(db_schema.COL_PAY_PERIOD_START, width=100, anchor="center")
        self.payslip_history_tree.column(db_schema.COL_PAY_PERIOD_END, width=100, anchor="center")
        self.payslip_history_tree.column(db_schema.COL_PAY_NET_PAY, width=100, anchor="e")
        self.payslip_history_tree.column(db_schema.COL_PAY_GENERATION_DATE, width=120, anchor="center")

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.payslip_history_tree.yview)
        self.payslip_history_tree.configure(yscrollcommand=scrollbar.set)
        self.payslip_history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # TODO: Add button to view/export selected payslip PDF

    def _create_employee_documents_tab(self, parent_notebook, tab_text_key: str):
        """Creates the content for the 'Documents' tab."""
        tab_frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(tab_frame, text=_(tab_text_key))
        self._create_documents_section(tab_frame) # Reuse logic from EmployeeProfileWindow

    def _create_employee_action_log_tab(self, parent_notebook, tab_text_key: str):
        """Creates the content for the 'Action Log' tab."""
        tab_frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(tab_frame, text=_(tab_text_key))
        self._create_action_log_section(tab_frame) # Reuse logic from EmployeeProfileWindow

    def toggle_app_language(self):
        new_lang = "ar" if LANG_MANAGER.current_lang == "en" else "en"
        LANG_MANAGER.set_language(new_lang)
        
        
        # Trigger a full UI refresh for the new language
        self.refresh_ui_for_language()
        # Also refresh theme in case some language-specific theme elements exist
        if hasattr(self, 'style') and self.style: # Ensure style object exists
            self.apply_instance_theme(self.style)
    
    def _add_translatable_widget(self, widget, translation_key: str, attr: str = "text"):
        """Adds a widget and its translation key to the list for UI refresh."""
        # Store as a dictionary to include the attribute to be translated
        self.translatable_widgets.append({"widget": widget, "key": translation_key, "attr": attr})

    def _update_photo_preview(self, *args):
        """Loads and displays the employee photo preview."""
        filepath = self.photo_path_var.get()
        preview_width = 150  # Desired width for the preview
        preview_height = 150 # Desired height for the preview

        if filepath and os.path.exists(filepath):
            try:
                img = Image.open(filepath)
                
                # Calculate aspect ratio to resize without distortion
                img_width, img_height = img.size
                ratio = min(preview_width / img_width, preview_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                self._photo_image_ref = ImageTk.PhotoImage(img) # Keep a reference!
                self.photo_preview_label.config(image=self._photo_image_ref, text="") # Clear text
                self.photo_preview_label.image = self._photo_image_ref # Keep reference for label too
            except Exception as e:
                logger.error(f"Error loading image preview for {filepath}: {e}")
                self.photo_preview_label.config(image="", text="Invalid Image") # Clear image, show error
                self._photo_image_ref = None
        else:
            self.photo_preview_label.config(image="", text=self.default_preview_text) # Clear image, show default text
            self._photo_image_ref = None
        
        # Adjust label size if needed, or ensure it's large enough initially
        # self.photo_preview_label.config(width=preview_width, height=preview_height)
    def refresh_ui_for_language(self):
        """Update all translatable text elements in the GUI."""
        # Update main window title
        self.root.title(_("app_title"))
       # Update main notebook tab texts
        if hasattr(self, 'main_notebook') and self.main_notebook.winfo_exists():
            self.main_notebook.tab(self.employee_details_frame, text=_("main_tab_employees")) # Index 0
            # self.main_notebook.tab(self.dashboard_view_frame, text=_("main_tab_dashboard")) # REMOVED Dashboard Tab
            # self.main_notebook.tab(self.reports_view_frame, text=_("main_tab_reports")) # REMOVED Reports Tab
            # self.main_notebook.tab(self.payroll_view_frame, text=_("main_tab_payroll")) # REMOVED Payroll Tab
            # self.main_notebook.tab(self.alerts_view_frame, text=_("main_tab_alerts")) # REMOVED Alerts Tab # This line is correct
            self.main_notebook.tab(self.analytics_view_frame, text=_("main_tab_analytics")) # This line is correct
            # self.main_notebook.tab(self.user_admin_view_frame, text=_("main_tab_user_admin"))
            # self.main_notebook.tab(self.settings_view_frame, text=_("main_tab_settings")) # REMOVED Settings Tab
            self.main_notebook.tab(self.device_sync_view_frame, text=_("main_tab_device_sync"))
            # self.main_notebook.tab(self.employee_tasks_view_frame, text=_("main_tab_tasks")) # REMOVED Tasks Tab
            # self.main_notebook.tab(self.metrics_view_frame, text=_("main_tab_metrics")) # REMOVED Metrics Tab # This line is correct
            # self.main_notebook.tab(self.interview_scheduling_view_frame, text=_("main_tab_interview_scheduling")) # REMOVED Interview Scheduling Tab
            # self.main_notebook.tab(self.approvals_view_frame, text=_("main_tab_approvals")) # REMOVED Approvals Tab
            self.main_notebook.tab(self.fingerprint_analysis_tab, text=_("main_tab_fingerprint_analysis"))
        # Update internal employee details notebook tab texts
        # If they were, you'd need to store their keys and update them here.
        # Example (if tab texts were translatable):
        # if hasattr(self, 'employee_details_notebook') and self.employee_details_notebook.winfo_exists():
        #     self.employee_details_notebook.tab(0, text=_("employee_tab_general_info"))
        #     self.employee_details_notebook.tab(1, text=_("employee_tab_attendance"))
        #     self.employee_details_notebook.tab(2, text=_("employee_tab_payroll"))
        #     ... etc.
        if hasattr(self, 'employee_details_notebook') and self.employee_details_notebook.winfo_exists():
            # Assuming the order of tabs is fixed as created in _create_employee_details_tab_content
            self.employee_details_notebook.tab(0, text=_("emp_details_tab_general_info")) # General Info
            self.employee_details_notebook.tab(1, text=_("emp_details_tab_attendance"))   # Attendance
            self.employee_details_notebook.tab(2, text=_("emp_details_tab_payroll"))    # Payroll
            self.employee_details_notebook.tab(3, text=_("emp_details_tab_documents"))  # Documents
            self.employee_details_notebook.tab(4, text=_("emp_details_tab_action_log")) # Action Log

        for item_info in self.translatable_widgets:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text") # Default to "text" if not specified

            if widget.winfo_exists():
                # For LabelFrames, the 'text' option is used.
                # For Buttons and Labels, 'text' option is also used.
                try:
                    if attr_to_update == "title" and isinstance(widget, ttk.LabelFrame): # Special handling for LabelFrame title
                        widget.config(text=_(key))
                    else: # Default to 'text' attribute for other widgets
                        widget.config(text=_(key))
                except tk.TclError as e:
                    logger.warning(f"Could not set text for widget {widget} with key '{key}': {e}")

        # Update status bar initial text if needed (though it's mostly dynamic)
        if hasattr(self, 'status_var') and not self.tree.selection(): # If no employee selected
            self.status_var.set(_("status_bar_ready_text"))
        
        # Update Gender Filter Combobox values
        if hasattr(self, 'gender_filter_combo') and self.gender_filter_combo.winfo_exists():
            gender_options = [
                _("gender_option_all"), _("gender_option_male"), 
                _("gender_option_female"), _("gender_option_other")
            ]
            self.gender_filter_combo['values'] = gender_options
            if not self.gender_filter_var.get() or self.gender_filter_var.get() not in gender_options: # Set default if empty or invalid
                self.gender_filter_var.set(_("gender_option_all"))
        # Update stats summary labels if they are translatable
        if hasattr(self, 'total_employees_label') and hasattr(self, 'total_employees_var'):
             # The label text itself might be static, but the variable text is dynamic.
             # If the static label text needs translation:
             # self.total_employees_label.config(text=_("total_employees_label_text"))
             pass # Dynamic text handled by _update_stats_summary

        # Update attendance status label if it's translatable
        if hasattr(self, 'attendance_status_label') and hasattr(self, 'attendance_status_var'):
             # The text is dynamic via attendance_status_var, which is set using _() in _update_attendance_status_for_selected
             pass # Dynamic text handled by _update_attendance_status_for_selected

        # Update recommendations text widget if it exists
        if hasattr(self, 'recommendations_text') and self.recommendations_text.winfo_exists():
            palette = get_theme_palette_global(self.current_theme)
            _theme_text_widget_global(self.recommendations_text, palette)

        # Update readonly photo preview label text if no photo
        if hasattr(self, 'readonly_photo_preview_label') and self.readonly_photo_preview_label.cget("image") == "":
            self.readonly_photo_preview_label.config(text=_("no_photo_text"))

        # Update Toplevels, ensuring they exist and have the method
        for tl in self.active_toplevels:
            try:
                if tl.winfo_exists() and hasattr(tl, 'refresh_ui_for_language'):
                    tl.refresh_ui_for_language()
            except Exception as e_tl_refresh:
                logger.warning(f"Error refreshing language for toplevel {tl.title()}: {e_tl_refresh}")
        # Refresh treeview headers (example for main employee tree)
        if hasattr(self, 'tree') and self.tree.winfo_exists():
            self._update_main_tree_headers()
    
    def _populate_treeview(self, employees_to_display: List[Dict]):
        """Helper to clear and populate the treeview with given employees."""
        if not hasattr(self, 'tree') or not self.tree.winfo_exists(): # Ensure tree exists
            logger.error("_populate_treeview called but self.tree does not exist or is not visible.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)
        if not employees_to_display:
            return # Nothing to display
        for emp in employees_to_display:
            # --- Instant Status Assessment ---
            # Moved this logic into _populate_treeview
            status_data = attendance_utils.get_employee_attendance_status_today(emp[db_schema.COL_EMP_ID])
            today_status_display = status_data.get("status_message", _("status_not_available"))
            # --- End Instant Status Assessment ---

            department_display_name = emp.get("department_name", _("unassigned_department")) or _("unassigned_department")
            self.tree.insert("", "end", values=(
                emp.get(db_schema.COL_EMP_ID, ""),
                emp.get(db_schema.COL_EMP_NAME, ""),
                today_status_display, # Value for the new "today_status" column
                emp.get("department_name", "") or "Unassigned", # Use "department_name" key
                emp.get(db_schema.COL_EMP_POSITION, ""),
                f"{emp.get(db_schema.COL_EMP_SALARY, 0.0):.2f}",
                emp.get(db_schema.COL_EMP_STATUS, "N/A"),
                emp.get(db_schema.COL_EMP_TERMINATION_DATE, ""),
                "Yes" if emp.get("exclude_vacation_policy", 0) == 1 else "No"
            ))
            
    def _create_table_action_buttons(self, parent_frame):
        """Creates action buttons that appear below the employee table."""
        # parent_frame is a LabelFrame: "Employee Actions (Table)"

        buttons_to_create = [
            # (translation_key, command, bootstyle, initial_state, attribute_name)
            ("add_employee_btn", self.gui_add_employee, db_schema.BS_ADD, "normal", "add_btn_table", "➕ "), # Corrected
            ("update_selected_btn", self.gui_update_employee, db_schema.BS_VIEW_EDIT, "disabled", "update_btn_table"), # Corrected
            ("delete_selected_btn", self.gui_delete_employee, db_schema.BS_DELETE_FINISH, "disabled", "delete_btn_table", "🗑️ "), # Corrected
            ("view_full_profile_btn_text", self.gui_show_full_profile, db_schema.BS_VIEW_EDIT, "disabled", "view_profile_btn_table"), # Corrected
            ("print_btn_text", self.gui_print_selected_employee_details, db_schema.BS_NEUTRAL, "disabled", "print_btn_table", "🖨️ "), # Corrected
            ("clear_fields_btn", self.gui_clear_fields_and_selection, db_schema.BS_LIGHT, "normal", "clear_btn_table"), # Corrected
            ("terminate_employee_btn_text", self.gui_terminate_employee, db_schema.BS_DELETE_FINISH, "disabled", "terminate_btn_table"), # Corrected
            ("export_csv_btn_text", self.gui_export_to_csv, db_schema.BS_NEUTRAL, "normal", "export_csv_btn_table"), # Corrected
            ("import_csv_btn_text", self.gui_import_from_csv, db_schema.BS_ADD, "normal", "import_csv_btn_table"), # Corrected
            ("refresh_list_btn_text", self.gui_show_all_employees, db_schema.BS_VIEW_EDIT, "normal", "refresh_list_btn_table"), # Corrected

        ]

        for i, button_config in enumerate(buttons_to_create):
            key, command, style, initial_state, attr_name, *icon_tuple = button_config
            icon = icon_tuple[0] if icon_tuple else ""
            row, col = divmod(i, 2) # 2 buttons per row
            btn = ttk.Button(parent_frame, text=f"{icon}{_(key)}", command=command, bootstyle=style, state=initial_state)
            # Add specific tooltips
            if key == "add_employee_btn": ToolTip(btn, text=_("tooltip_add_employee"))
            elif key == "refresh_list_btn_text": ToolTip(btn, text=_("tooltip_refresh_list"))
            # TODO: Add more tooltips here if needed for other buttons

            btn.grid(row=row, column=col, padx=2, pady=3, sticky="ew")
            self._add_translatable_widget(btn, key) # Use the key directly
            setattr(self, attr_name, btn) # Store button reference directly as an attribute

        # Configure columns to have equal weight so buttons expand nicely
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.columnconfigure(1, weight=1)

    def _create_stats_summary_widgets(self, parent_frame):
        """Creates the miniature statistics display widgets."""
        # parent_frame is a LabelFrame: "Statistics Summary"
        
        # Use a frame for layout within the LabelFrame
        stats_inner_frame = ttk.Frame(parent_frame)
        stats_inner_frame.pack(fill="x", expand=True)

        # Labels for stats
        self.total_employees_var_stats = tk.StringVar(value="Total: N/A")
        self.total_employees_label = ttk.Label(stats_inner_frame, textvariable=self.total_employees_var_stats)
        self.total_employees_label.pack(side="left", padx=5)

        self.active_employees_var_stats = tk.StringVar(value="Active: N/A")
        self.active_employees_label = ttk.Label(stats_inner_frame, textvariable=self.active_employees_var_stats)
        self.active_employees_label.pack(side="left", padx=5)

        self.avg_salary_var_stats = tk.StringVar(value="Avg Salary: N/A")
        self.avg_salary_label = ttk.Label(stats_inner_frame, textvariable=self.avg_salary_var_stats)
        self.avg_salary_label.pack(side="left", padx=5)

    def gui_print_selected_employee_details(self):
        """Handles printing details of the selected employee."""
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showwarning(_("print_error_title"), _("no_employee_selected_for_print_warning"), parent=self.root)
            return
        
        messagebox.showinfo(_("print_employee_title"), _("printing_details_placeholder_message", emp_id=emp_id), parent=self.root)
        logger.info(f"Print action triggered for employee ID: {emp_id}")

    def gui_terminate_employee(self):
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showerror(_("termination_error_title"), _("no_employee_selected_error"), parent=self.root)
            return

        # Prompt for termination date
        termination_date_str = simpledialog.askstring(
            _("terminate_employee_dialog_title"), 
            _("terminate_employee_date_prompt", emp_id=emp_id),
            parent=self.root
        )
        if not termination_date_str: # User cancelled or entered empty string
            return
        try:
            datetime.strptime(termination_date_str, '%Y-%m-%d') # Validate date format
        except ValueError:
            messagebox.showerror(_("input_error_title"), _("invalid_date_format_yyyy_mm_dd_error"), parent=self.root)
            return

        reason = simpledialog.askstring(_("termination_reason_dialog_title"), _("termination_reason_prompt"), parent=self.root)
        # reason can be None if user cancels the reason dialog, which is fine.

        try:
            user_id_performing_action = self.parent_app.get_current_user_id()
            terminate_employee_db(emp_id, termination_date_str, reason, user_id_performing_action)
            messagebox.showinfo(_("success_title"), _("employee_terminated_success_message", emp_id=emp_id, date=termination_date_str), parent=self.root)
            self.gui_show_all_employees() # Refresh list
            self.clear_input_fields()     # Clear input fields
        except (EmployeeNotFoundError, InvalidInputError, DatabaseOperationError) as e:
            messagebox.showerror(_("termination_error_title"), str(e), parent=self.root)

    def gui_delete_employee(self):
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showerror(_("delete_error_title"), _("no_employee_selected_error"), parent=self.root)
            return

        if messagebox.askyesno(_("confirm_delete_title"), _("confirm_delete_employee_message", emp_id=emp_id), parent=self.root):
            try:
                user_id_performing_action = self.parent_app.get_current_user_id()
                db_queries.delete_employee_db(emp_id)
                messagebox.showinfo(_("success_title"), _("employee_deleted_message", emp_id=emp_id), parent=self.root)
                db_queries.log_employee_action(emp_id,
                                    f"Employee record deleted.", # Name might not be available if form is modal
                                    user_id_performing_action)

                self.gui_show_all_employees() # Refresh list
                self.clear_input_fields()     # Clear input fields
            except EmployeeNotFoundError as e: # pragma: no cover
                messagebox.showerror(_("db_error_title"), str(e), parent=self.root) # pragma: no cover
            except DatabaseOperationError as e: # pragma: no cover
                messagebox.showerror(_("db_error_title"), str(e), parent=self.root)
    
    def _create_search_controls(self, parent_frame):
        # parent_frame is a LabelFrame: "Search & Filter"
        
        # Using grid for better alignment
        search_field_lbl_key = "search_field_label"
        search_field_lbl = ttk.Label(parent_frame, text=_(search_field_lbl_key))
        search_field_lbl.grid(row=0, column=0, sticky="w", padx=(0,5), pady=(0,3))
        self._add_translatable_widget(search_field_lbl, search_field_lbl_key)

        self.search_field_var = tk.StringVar(value=db_schema.COL_EMP_NAME) # Default search field
        self.left_pane_search_field_combo = ttk.Combobox(parent_frame, textvariable=self.search_field_var, state="readonly",
                                               values=[db_schema.COL_EMP_ID, db_schema.COL_EMP_NAME, "department_name", db_schema.COL_EMP_POSITION, db_schema.COL_EMP_STATUS],
                                               width=20) # Adjust width as needed
        self.left_pane_search_field_combo.set(db_schema.COL_EMP_NAME)
        self.left_pane_search_field_combo.grid(row=0, column=1, sticky="ew", pady=(0,3))

        search_term_lbl_key = "search_term_label"
        search_term_lbl = ttk.Label(parent_frame, text=_(search_term_lbl_key))
        search_term_lbl.grid(row=1, column=0, sticky="w", padx=(0,5), pady=(0,3))
        self._add_translatable_widget(search_term_lbl, search_term_lbl_key)

        self.left_pane_search_term_entry = ttk.Entry(parent_frame) 
        self.left_pane_search_term_entry.bind("<Return>", lambda event: self.gui_search_employee())
        self.left_pane_search_term_entry.grid(row=1, column=1, sticky="ew", pady=(0,3))
        gender_lbl_key = "search_gender_label"
        gender_lbl = ttk.Label(parent_frame, text=_(gender_lbl_key))
        gender_lbl.grid(row=2, column=0, sticky="w", padx=(0,5), pady=(0,3))
        self._add_translatable_widget(gender_lbl, gender_lbl_key)

        self.gender_filter_var = tk.StringVar()
        self.gender_filter_combo = ttk.Combobox(parent_frame, textvariable=self.gender_filter_var, state="readonly", width=20)
        self.gender_filter_combo.grid(row=2, column=1, sticky="ew", pady=(0,3))
        # Values will be set in refresh_ui_for_language
        parent_frame.columnconfigure(1, weight=1) # Configure the column with the entry/combobox to expand

        search_button_row = ttk.Frame(parent_frame)
        search_button_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5,0)) # Moved to row 3

        search_btn_key = "search_button_text"
        self.left_pane_search_btn = ttk.Button(search_button_row, text=_(search_btn_key), command=self.gui_search_employee, bootstyle=db_schema.BS_PRIMARY_ACTION) # Corrected
        self.left_pane_search_btn.pack(side="left", expand=True, fill="x", padx=(0,2))
        self._add_translatable_widget(self.left_pane_search_btn, search_btn_key)

        show_all_btn_key = "show_all_button_text"
        self.left_pane_show_all_btn = ttk.Button(search_button_row, text=_(show_all_btn_key), command=self.gui_show_all_employees, bootstyle=db_schema.BS_LIGHT) # Corrected
        self.left_pane_show_all_btn.pack(side="left", expand=True, fill="x", padx=(2,0))
        self._add_translatable_widget(self.left_pane_show_all_btn, show_all_btn_key)

   
    def _handle_update_shortcut(self, event=None):
        """Handles the Ctrl+U shortcut for updating an employee."""
        if self.tree.selection(): # Check if an item is selected in the main employee tree
            self.gui_update_employee()
        else:
            messagebox.showwarning("Update Employee", "Please select an employee from the list to update.", parent=self.root)

    def _handle_delete_shortcut(self, event=None):
        """Handles the Delete key shortcut for deleting an employee."""
        if self.tree.selection(): # Check if an item is selected in the main employee tree
            self.gui_delete_employee() # This method already includes confirmation
        else:
            # Optionally, provide feedback if no employee is selected, or do nothing.
            # messagebox.showwarning("Delete Employee", "Please select an employee from the list to delete.", parent=self.root)
            pass
    def _bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda event: self.gui_add_employee())
        self.root.bind("<Control-u>", self._handle_update_shortcut)
        self.root.bind("<Control-l>", lambda event: self.gui_clear_fields_and_selection())
        self.root.bind("<Control-f>", lambda event: self.left_pane_search_term_entry.focus_set()) # Focus left pane search
        # self.left_pane_search_term_entry is already bound in _create_search_controls
        
        self.root.bind("<Control-Shift-C>", lambda event: self.gui_export_to_csv())
        self.root.bind("<Control-Shift-P>", lambda event: self.gui_export_to_pdf())
        self.root.bind("<Control-t>", self.toggle_theme)
        self.root.bind("<Control-r>", lambda event: self.gui_show_all_employees()) # Ctrl+R for Refresh
        self.root.bind("<F5>", lambda event: self.gui_show_all_employees())       # F5 for Refresh
        self.root.bind("<Delete>", self._handle_delete_shortcut)                  # Delete key
        self.root.bind("<F1>", lambda event: self.gui_show_about_dialog())        # F1 for About
        self.root.bind("<Control-q>", lambda event: self.root.quit())

        
    def _create_import_export_buttons(self, parent_frame):
        button_row_frame = ttk.Frame(parent_frame) # This frame is not strictly necessary if buttons pack directly
        button_row_frame.pack(fill="x", pady=2)

        self.export_csv_btn = ttk.Button(parent_frame, text="Export to CSV", command=self.gui_export_to_csv, bootstyle=BS_NEUTRAL)
        self.export_csv_btn.pack(in_=button_row_frame, side="left", expand=True, fill="x", padx=(0,1))
        self.export_pdf_btn = ttk.Button(parent_frame, text="Export to PDF", command=self.gui_export_to_pdf, bootstyle=BS_NEUTRAL)
        self.export_pdf_btn.pack(in_=button_row_frame, side="left", expand=True, fill="x", padx=1)
        self.import_csv_btn = ttk.Button(parent_frame, text="Import from CSV", command=self.gui_import_from_csv, bootstyle=BS_ADD)
        self.import_csv_btn.pack(in_=button_row_frame, side="left", expand=True, fill="x", padx=(1,0))
    
    def _create_attendance_controls(self, parent_frame):
        # parent_frame is a LabelFrame: "Selected Employee Actions"

        # Row 1: Clock In/Out buttons
        clock_button_row = ttk.Frame(parent_frame)
        clock_button_row.pack(fill="x", pady=(5, 2)) # Add some top padding

        clock_in_key = "clock_in_selected_btn_text"
        self.clock_in_btn = ttk.Button(clock_button_row, text=_(clock_in_key), command=self.gui_clock_in, bootstyle=db_schema.BS_VIEW_EDIT, state="disabled") # Corrected
        self.clock_in_btn.pack(side="left", expand=True, fill="x", padx=(0, 1))
        
        self._add_translatable_widget(self.clock_in_btn, clock_in_key)
        
        clock_out_key = "clock_out_selected_btn_text"
        self.clock_out_btn = ttk.Button(clock_button_row, text=_(clock_out_key), command=self.gui_clock_out, bootstyle=db_schema.BS_VIEW_EDIT, state="disabled") # Corrected
        self.clock_out_btn.pack(side="left", expand=True, fill="x", padx=(1, 0))
        self._add_translatable_widget(self.clock_out_btn, clock_out_key)


        # Row 2: View Attendance Log button
        view_log_key = "view_attendance_log_btn_text"
        self.view_attendance_btn = ttk.Button(parent_frame, text=_(view_log_key), command=self.gui_show_attendance_log_window, bootstyle=db_schema.BS_VIEW_EDIT, state="disabled") # Corrected
        self.view_attendance_btn.pack(fill="x", pady=(2, 5)) # Add some vertical padding
        self._add_translatable_widget(self.view_attendance_btn, view_log_key)


        # Row 3: Status label (optional, consider if needed with other UI feedback)
        # If keeping, ensure it has enough space and doesn't look cramped.
        self.attendance_status_var = tk.StringVar(value=_("status_select_employee"))
        self.attendance_status_label = ttk.Label(parent_frame, textvariable=self.attendance_status_var, wraplength=180, anchor="center") # anchor center
        # The text for attendance_status_label is dynamic via attendance_status_var, so no static key needed for the label itself.
        self.attendance_status_label.pack(fill="x", pady=(0, 5)) # Add some bottom padding

        # Tardiness Alert Label (initially empty)
        self.tardiness_alert_label = ttk.Label(parent_frame, text="", foreground="red", font=("Helvetica", 9, "bold"))
        self.tardiness_alert_label.pack(fill="x", pady=(0, 5)) # Below status label

    
    def _create_user_admin_widgets(self, parent_frame): # Changed parent_tab_frame to parent_frame
        # Frame for user list
        user_list_frame_key = "user_admin_list_frame_title" # Key needed
        user_list_frame = ttk.LabelFrame(parent_frame, text=_(user_list_frame_key), padding="5") # Reduced padding
        user_list_frame.pack(side="left", fill="both", expand=True, pady=5, padx=(0,5)) # Pack left
        self._add_translatable_widget(user_list_frame, user_list_frame_key, attr="title") # Corrected: Pass attr


        self.user_tree_cols = ("username", "role", db_schema.COL_USER_LINKED_EMP_ID)
        self.user_tree = ttk.Treeview(user_list_frame, columns=self.user_tree_cols, show="headings")
        self.user_tree.heading("username", text="Username")
        self.user_tree.heading("role", text="Role") # TODO: Add translation key
        self.user_tree.heading(db_schema.COL_USER_LINKED_EMP_ID, text="Linked Employee") # TODO: Key
        self.user_tree.column("username", width=150, anchor="w")
        self.user_tree.column("role", width=100, anchor="w")
        self.user_tree.column(db_schema.COL_USER_LINKED_EMP_ID, width=150, anchor="w") # New column
        self.user_tree.pack(side="left", fill="both", expand=True)
        user_scrollbar = ttk.Scrollbar(user_list_frame, orient="vertical", command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=user_scrollbar.set)
        user_scrollbar.pack(side="right", fill="y")
        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_tree_select)

        # Frame for user form (add/edit) - ensure this frame is correctly parented
        user_form_frame_key = "user_admin_details_frame_title" # Key needed
        user_form_frame = ttk.LabelFrame(parent_frame, text=_(user_form_frame_key), padding="10")
        user_form_frame.pack(side="right", fill="y", pady=5, padx=(5,0)) # Pack right        
        self._add_translatable_widget(user_form_frame, user_form_frame_key)

        username_lbl_key = "user_admin_username_label" # Key needed
        username_lbl = ttk.Label(user_form_frame, text=_(username_lbl_key))
        username_lbl.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget(username_lbl, username_lbl_key)
        self.ua_username_var = tk.StringVar()
        self.ua_username_entry = ttk.Entry(user_form_frame, textvariable=self.ua_username_var, width=25)
        self.ua_username_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        password_lbl_key = "user_admin_password_label" # Key needed
        password_lbl = ttk.Label(user_form_frame, text=_(password_lbl_key))
        password_lbl.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget(password_lbl, password_lbl_key)
        self.ua_password_var = tk.StringVar()
        self.ua_password_entry = ttk.Entry(user_form_frame, textvariable=self.ua_password_var, show="*", width=25)
        self.ua_password_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        password_hint_key = "user_admin_password_hint" # Key needed
        password_hint_lbl = ttk.Label(user_form_frame, text=_(password_hint_key))
        password_hint_lbl.grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self._add_translatable_widget(password_hint_lbl, password_hint_key)

        role_lbl_key = "user_admin_role_label" # Key needed
        role_lbl = ttk.Label(user_form_frame, text=_(role_lbl_key))
        role_lbl.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget(role_lbl, role_lbl_key)
        self.ua_role_var = tk.StringVar()
        self.ua_role_combo = ttk.Combobox(user_form_frame, textvariable=self.ua_role_var, values=db_schema.VALID_ROLES, state="readonly", width=23)
        self.ua_role_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        # Link to Employee ID
        ttk.Label(user_form_frame, text="Link to Employee:").grid(row=3, column=0, sticky="w", padx=5, pady=2) # TODO: Key
        self.ua_linked_emp_var = tk.StringVar()
        self.ua_linked_emp_combo = AutocompleteCombobox(user_form_frame, textvariable=self.ua_linked_emp_var, width=23) # Use AutocompleteCombobox from components
        populate_employee_combobox(self.ua_linked_emp_combo, db_queries.get_all_employees_db, include_active_only=False, empty_option_text="None")
        self.ua_linked_emp_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.ua_role_combo.set(db_schema.ROLE_EMPLOYEE) # Default role # Corrected

        user_form_frame.columnconfigure(1, weight=1)

        # Action buttons for user admin
        ua_buttons_frame = ttk.Frame(user_form_frame)
        ua_buttons_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky="ew") # Adjusted row

        clear_fields_btn_key = "user_admin_clear_btn" # Key needed
        self.ua_clear_btn = ttk.Button(ua_buttons_frame, text=_(clear_fields_btn_key), command=self._gui_ua_clear_fields, bootstyle=db_schema.BS_LIGHT)
        self.ua_clear_btn.pack(side="left", padx=2, fill="x", expand=True)
        self._add_translatable_widget(self.ua_clear_btn, clear_fields_btn_key)

        delete_user_btn_key = "user_admin_delete_btn" # Key needed
        self.ua_delete_user_btn = ttk.Button(ua_buttons_frame, text=_(delete_user_btn_key), command=self._gui_ua_delete_user, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH) # Corrected
        self.ua_delete_user_btn.pack(side="left", padx=2, fill="x", expand=True) # Was side="left", now right-aligned group
        self._add_translatable_widget(self.ua_delete_user_btn, delete_user_btn_key)

        save_changes_btn_key = "user_admin_save_changes_btn" # Changed key
        self.ua_save_user_changes_btn = ttk.Button(ua_buttons_frame, text=_(save_changes_btn_key), command=self._gui_ua_save_user_changes, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT) # Corrected
        self.ua_save_user_changes_btn.pack(side="left", padx=2, fill="x", expand=True)
        self._add_translatable_widget(self.ua_save_user_changes_btn, save_changes_btn_key)

        add_user_btn_key = "user_admin_add_btn" # Key needed
        self.ua_add_user_btn = ttk.Button(ua_buttons_frame, text=_(add_user_btn_key), command=self._gui_ua_add_user, bootstyle=db_schema.BS_ADD) # Corrected
        self.ua_add_user_btn.pack(side="left", padx=2, fill="x", expand=True) # This will be the rightmost due to pack order
        self._add_translatable_widget(self.ua_add_user_btn, add_user_btn_key)


        self._gui_ua_load_users() # Load users into tree
        
        
    def _create_user_admin_widgets(self, parent_frame):
        # This tab is now a placeholder.
        info_label = ttk.Label(parent_frame, text=_("user_admin_info_open_from_sidebar"), font=("Helvetica", 12), wraplength=350, justify="center") # Add new key
        info_label.pack(pady=20, padx=10, expand=True)
        self._add_translatable_widget(info_label, "user_admin_info_open_from_sidebar") # Use the new key

    def _create_employee_list_widgets(self, parent_frame):
        columns = (
            db_schema.COL_EMP_ID, # Corrected
            db_schema.COL_EMP_NAME, # Corrected
            "department_name", 
            db_schema.COL_EMP_POSITION, # Corrected
            db_schema.COL_EMP_SALARY, # Corrected
           # COL_EMP_GENDER, # Added Gender to columns (Index 4)
           # COL_EMP_PHONE, # Added Phone
           # COL_EMP_EMAIL, # Added Email
            # db_schema.COL_EMP_EMPLOYMENT_HISTORY, # Too long for main list, view in details # Corrected
            db_schema.COL_EMP_STATUS, # Corrected
            db_schema.COL_EMP_TERMINATION_DATE, # Corrected
            "exclude_vacation_policy") # New column
        self.tree = ttk.Treeview(parent_frame, columns=columns, show="headings")
        for col in columns:
            if col == db_schema.COL_EMP_EMPLOYMENT_HISTORY: continue # Skip for main tree view # Corrected

            self.tree.heading(col, text=col.replace("_", " ").title()) # Nicer headers (Title case)
            col_width = 120 if col in [db_schema.COL_EMP_EMAIL, db_schema.COL_EMP_PHONE] else 100 # Corrected
            self.tree.column(col, width=col_width, anchor="w", stretch=tk.YES) # Allow columns to stretch
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(parent_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.configure(xscrollcommand=h_scrollbar.set) # Corrected xscrollcommand
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x", before=self.tree) # Pack horizontal scrollbar below tree
        self._update_main_tree_headers() # Set initial headers

    def _update_main_tree_headers(self):
        """Updates the headers of the main employee treeview based on current language."""
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return
        header_map = {
            db_schema.COL_EMP_ID: _("header_emp_id"), db_schema.COL_EMP_NAME: _("header_emp_name"), # Corrected
            "department_name": _("header_emp_department"), db_schema.COL_EMP_POSITION: _("header_emp_position"), # Corrected
            db_schema.COL_EMP_SALARY: _("header_emp_salary"), db_schema.COL_EMP_STATUS: _("header_emp_status"), # Corrected
            db_schema.COL_EMP_TERMINATION_DATE: _("header_emp_termination_date"), # Corrected
            "exclude_vacation_policy": _("header_exclude_vacation_policy") # Corrected
        }
        for col_id in self.tree["columns"]:
            self.tree.heading(col_id, text=header_map.get(col_id, col_id.replace("_", " ").title()))
            
    def gui_show_all_employees(self):
        all_employees = db_queries.get_all_employees_db() # Corrected
        self._populate_treeview(all_employees)
        self.status_var.set(f"Displaying all {len(all_employees)} employees. Select one to see details.")
        self._reset_selection_dependent_ui()
        self._update_stats_summary() # Update stats after showing all


    def gui_clear_fields_and_selection(self, clear_id=True): # Added clear_id parameter
        self.clear_input_fields(clear_id=True) # Clear all fields including ID
        self._reset_selection_dependent_ui()

    def _reset_selection_dependent_ui(self):
        """Resets UI elements that depend on a tree selection."""
        # Buttons below the table
        if hasattr(self, 'update_btn_table'): self.update_btn_table.config(state="disabled")
        if hasattr(self, 'delete_btn_table'): self.delete_btn_table.config(state="disabled")
        if hasattr(self, 'view_profile_btn_table'): self.view_profile_btn_table.config(state="disabled")
        if hasattr(self, 'print_btn_table'): self.print_btn_table.config(state="disabled")
        if hasattr(self, 'terminate_btn_table'): self.terminate_btn_table.config(state="disabled") # Corrected attribute name

        # Buttons/Labels in the employee form or elsewhere that depend on selection
        if hasattr(self, 'show_qr_btn_form'): self.show_qr_btn_form.config(state="disabled") # QR button in form
        if hasattr(self, 'attendance_status_var'): self.attendance_status_var.set(_("status_select_employee"))
        
        # self._update_attendance_buttons_state(None) # If attendance buttons are separate
        # Deselecting the tree item here would prevent on_tree_select from working
        # if self.tree.selection(): # If there's a selection
        #     self.tree.selection_remove(self.tree.selection()) # Deselect tree item if any         
        # Disable buttons in "Selected Employee Actions" frame
        if hasattr(self, 'clock_in_btn'): self.clock_in_btn.config(state="disabled")
        if hasattr(self, 'clock_out_btn'): self.clock_out_btn.config(state="disabled")
        # Clear data in internal tabs
        
        self._clear_recommendations_section() # Clear recommendations
        self._clear_general_details_tab()
        self._clear_attendance_tab()
        self._clear_documents_tab()
        self._clear_payroll_tab()
        self._clear_documents_tab()
        self._clear_action_log_tab()

        if hasattr(self, 'view_attendance_btn'): self.view_attendance_btn.config(state="disabled")
        if hasattr(self, 'manage_vacations_btn_employee_view'): self.manage_vacations_btn_employee_view.config(state="disabled")

    
    def _clear_recommendations_section(self):
        """Clears the text in the Recommendations section."""
        if hasattr(self, 'recommendations_text') and self.recommendations_text.winfo_exists():
            self.recommendations_text.config(state="normal"); self.recommendations_text.delete("1.0", tk.END); self.recommendations_text.config(state="disabled")
        if hasattr(self, 'tardiness_alert_label'): self.tardiness_alert_label.config(text="") # Clear tardiness alert
        if hasattr(self, 'vacation_alert_label'): self.vacation_alert_label.config(text="") # Clear vacation alert # This line was duplicated
        if hasattr(self, 'attendance_total_hours_var'): self.attendance_total_hours_var.set("Total Hours Worked: N/A")
        if hasattr(self, 'attendance_total_days_var'): self.attendance_total_days_var.set("Total Days Present: N/A")

    def _clear_general_details_tab(self):
        """Clears the widgets in the General Info tab."""
        if hasattr(self, 'readonly_labels'):
            for key, var_instance in self.readonly_labels.items():
                var_instance.set("N/A")
        """Clears the widgets in the General Info tab."""
        if hasattr(self, 'readonly_labels'):
            for key, var_instance in self.readonly_labels.items():
                var_instance.set("N/A")
        if hasattr(self, 'readonly_employment_history_text') and self.readonly_employment_history_text.winfo_exists():
            self.readonly_employment_history_text.config(state="normal") # Enable to clear
            self.readonly_employment_history_text.delete("1.0", tk.END)
            self.readonly_employment_history_text.config(state="disabled")
        if hasattr(self, 'readonly_photo_preview_label'):
            self.readonly_photo_preview_label.config(image="", text=_("no_photo_text"))
            self._readonly_photo_image_ref = None
        if hasattr(self, 'tardiness_alert_label'): self.tardiness_alert_label.config(text="")
        if hasattr(self, 'vacation_alert_label'): self.vacation_alert_label.config(text="")

    def _clear_attendance_tab(self):
        """Clears the widgets in the Attendance tab."""
        if hasattr(self, 'attendance_log_tree') and self.attendance_log_tree.winfo_exists():
            for item in self.attendance_log_tree.get_children():
                self.attendance_log_tree.delete(item)
        if hasattr(self, 'attendance_total_hours_var'):
            self.attendance_total_hours_var.set(_("attendance_log_total_hours_default", default="Total Hours Worked: N/A"))
        if hasattr(self, 'attendance_total_days_var'):
            self.attendance_total_days_var.set(_("attendance_log_total_days_default", default="Total Days Present: N/A"))

    def _clear_payroll_tab(self):
        """Clears the widgets in the Payroll tab."""
        if hasattr(self, 'payslip_history_tree') and self.payslip_history_tree.winfo_exists():
            for item in self.payslip_history_tree.get_children():
                self.payslip_history_tree.delete(item)

    def _clear_documents_tab(self):
        """Clears the widgets in the Documents tab."""
        if hasattr(self, 'doc_tree') and self.doc_tree.winfo_exists():
            for item in self.doc_tree.get_children():
                self.doc_tree.delete(item)

    def _clear_action_log_tab(self):
        """Clears the widgets in the Action Log tab."""
        if hasattr(self, 'action_log_tree') and self.action_log_tree.winfo_exists():
            for item in self.action_log_tree.get_children():
                self.action_log_tree.delete(item)    
    
    def gui_add_employee(self):
        # This button now launches the modal for adding.
        self.parent_app._create_and_show_toplevel(
            EmployeeFormWindow, mode='add', 
            callback_on_save=self.gui_show_all_employees,
            tracker_attr_name="active_employee_form_window_add" # Use a distinct tracker for add mode
        )

    def _update_stats_summary(self):
        """Fetches and updates the miniature statistics display."""
        if not all(hasattr(self, var_name) for var_name in ['total_employees_var_stats', 'active_employees_var_stats', 'avg_salary_var_stats']):
            logger.warning("Statistics summary StringVars not initialized. Skipping update.")
            return
        try:
            total_employees = len(db_queries.get_all_employees_db(include_archived=True))
            active_employees_count = db_queries.get_total_employee_count_db() # Fetches active

            active_employees_list = [emp for emp in db_queries.get_all_employees_db() if emp.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE]
            salaries = [emp.get(db_schema.COL_EMP_SALARY, 0.0) for emp in active_employees_list if emp.get(db_schema.COL_EMP_SALARY) is not None]
            avg_salary = sum(salaries) / len(salaries) if salaries else 0.0

            self.total_employees_var_stats.set(f"{_('stats_total_employees_label')}: {total_employees}")
            self.active_employees_var_stats.set(f"{_('stats_active_employees_label')}: {active_employees_count}")
            self.avg_salary_var_stats.set(f"{_('stats_avg_salary_label')}: {avg_salary:,.2f}")

        except Exception as e:
            logger.error(f"Error updating stats summary: {e}")
            self.total_employees_var_stats.set(f"{_('stats_total_employees_label')}: Error")
            self.active_employees_var_stats.set(f"{_('stats_active_employees_label')}: Error")
            self.avg_salary_var_stats.set(f"{_('stats_avg_salary_label')}: Error")

    def gui_clock_in(self):
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showwarning("Clock In", "Please select an employee from the list.", parent=self.root)
            return
        
        try:
            # Ensure employee exists and is active before attempting clock-in
            employee_details = db_queries.get_employee_by_id_db(emp_id) # Corrected
            if not employee_details or employee_details.get(db_schema.COL_EMP_STATUS) != db_schema.STATUS_ACTIVE: # Corrected
                messagebox.showerror("Clock In Error", f"Employee {emp_id} is not active or not found.", parent=self.root)
                return
            
            user_id_performing_action = self.parent_app.get_current_user_id()
            db_queries.clock_in_employee(emp_id, performed_by_user_id=user_id_performing_action) # Call backend function
            messagebox.showinfo("Clock In", f"Employee {emp_id} clocked in successfully.", parent=self.root)
            self._set_employee_attendance_status_label(emp_id) # Update status label
        except (AlreadyClockedInError, EmployeeNotFoundError, DatabaseOperationError, AttendanceError) as e:
            messagebox.showerror("Clock In Error", str(e), parent=self.root)
        except Exception as e:
            logger.error(f"Unexpected error during clock-in for {emp_id}: {e}")
            messagebox.showerror("Clock In Error", f"An unexpected error occurred: {e}", parent=self.root)

    def gui_clock_out(self):
        emp_id = None
        selected_items = self.tree.selection()
        if selected_items:
            emp_id = self.tree.item(selected_items[0], "values")[0]
        if not emp_id:
            messagebox.showwarning("Clock Out", "Please select an employee from the list.", parent=self.root)
            return

        try:
            user_id_performing_action = self.parent_app.get_current_user_id()
            # Backend function clock_out_employee already checks if employee exists.
            db_queries.clock_out_employee(emp_id, performed_by_user_id=user_id_performing_action) # Call backend function
            messagebox.showinfo("Clock Out", f"Employee {emp_id} clocked out successfully.", parent=self.root)
            self._set_employee_attendance_status_label(emp_id) # Update status label
        except (NotClockedInError, EmployeeNotFoundError, DatabaseOperationError, AttendanceError) as e:
            # Catch specific errors from clock_out_employee
            messagebox.showerror("Clock Out Error", str(e), parent=self.root)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error during clock-out for {emp_id}: {e}")
            messagebox.showerror("Clock Out Error", f"An unexpected error occurred: {e}", parent=self.root)

    def on_tree_select(self, event):
        selected_item = self.tree.focus() # Get selected item
        if not selected_item:
            self._reset_selection_dependent_ui()
            return
        
        # --- Populate General Info Tab ---
        # Get employee ID from the tree values
        item_values = self.tree.item(selected_item, "values")
        # Assuming COL_EMP_ID is the first column in the tree as defined in _create_employee_list_widgets
        emp_id_from_tree = item_values[0] if item_values else None

        if not emp_id_from_tree:
            logger.warning("Could not get employee ID from tree selection.")
            self._reset_selection_dependent_ui()
            return

        # Fetch full employee details from the database
        try:
            full_employee_details = db_queries.get_employee_by_id_db(emp_id_from_tree) # Corrected
        except EmployeeNotFoundError:
            messagebox.showerror("Error", f"Could not retrieve details for employee ID {emp_id_from_tree}.", parent=self.root)
            self._reset_selection_dependent_ui()
            return

        # Populate the read-only display labels
        # These are in the General Info tab
        for key, var_instance in self.readonly_labels.items():
            value = full_employee_details.get(key, "N/A") # key is already a string like "id", "name"
            if key == db_schema.COL_EMP_SALARY: # Corrected
                value = f"${float(value):.2f}" if isinstance(value, (int, float)) else "$0.00"
            elif key == "exclude_vacation_policy":
                value = "Yes" if value == 1 else "No"
            elif key == "department_name" and not value: # Handle unassigned department (key is "department_name")
                value = "Unassigned"
            var_instance.set(str(value))

        # Populate multi-line employment history
        # This is in the General Info tab
        if hasattr(self, 'readonly_employment_history_text'):
            try:
                self.readonly_employment_history_text.config(state="normal")
                self.readonly_employment_history_text.delete("1.0", tk.END)
                
                history_text_content = full_employee_details.get(db_schema.COL_EMP_EMPLOYMENT_HISTORY, "N/A")
                # Ensure it's a string and handle None explicitly, though .get() default should cover None.
                history_text_content = str(history_text_content if history_text_content is not None else "N/A")
                
                # Replace null bytes as they can cause issues with C strings / Tcl.
                if '\0' in history_text_content:
                    logger.warning("Employment history contains null bytes. Replacing with [NULL] for display.")
                    history_text_content = history_text_content.replace('\0', '[NULL]') # Or replace with empty string

                self.readonly_employment_history_text.insert("1.0", history_text_content)
            except Exception as e_hist_insert:
                logger.error(f"Error inserting employment history: {e_hist_insert}", exc_info=True)
                self.readonly_employment_history_text.insert("1.0", "Error displaying history.")
            finally:
                if hasattr(self, 'readonly_employment_history_text') and self.readonly_employment_history_text.winfo_exists():
                    self.readonly_employment_history_text.config(state="disabled")

        # Update photo preview in read-only display
        # This is in the General Info tab
        if hasattr(self, 'readonly_photo_preview_label'):
            photo_path = full_employee_details.get(db_schema.COL_EMP_PHOTO_PATH) # Corrected
            if photo_path and image_utils.os.path.exists(photo_path): # Use image_utils.os
                try:
                    img = Image.open(photo_path)
                    img.thumbnail((150, 150), Image.Resampling.LANCZOS) # Resize for preview
                    self._readonly_photo_image_ref = ImageTk.PhotoImage(img)
                    self.readonly_photo_preview_label.config(image=self._readonly_photo_image_ref, text="")
                except Exception as e_img:
                    logger.error(f"Error loading photo for read-only preview: {e_img}")
                    self.readonly_photo_preview_label.config(image="", text=_("Invalid Photo")) # Consider key for "Invalid Photo"
                    self._readonly_photo_image_ref = None
            else:
                self.readonly_photo_preview_label.config(image="", text=_("no_photo_text"))
                self._readonly_photo_image_ref = None

        # Update status variable for attendance status label (if it exists)
        # Update status variable for attendance status label (in the left pane)
        status_val = full_employee_details.get(db_schema.COL_EMP_STATUS, "N/A") # Corrected
        if hasattr(self, 'attendance_status_var'): # Check if the status variable exists
            self._set_employee_attendance_status_label(emp_id_from_tree) # Use the correct method name
        
        # Update states of buttons in table_action_buttons_frame
        if hasattr(self, 'update_btn_table'): self.update_btn_table.config(state="normal")
        if hasattr(self, 'delete_btn_table'): self.delete_btn_table.config(state="normal")
        if hasattr(self, 'view_profile_btn_table'): self.view_profile_btn_table.config(state="normal") # This button is from table actions
        if hasattr(self, 'print_btn_table'): self.print_btn_table.config(state="normal")
        if hasattr(self, 'terminate_btn_table'):
            self.terminate_btn_table.config(state="normal" if full_employee_details.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE else "disabled") # Corrected

        # Update states of other selection-dependent UI elements
        # if hasattr(self, 'show_qr_btn_form'): self.show_qr_btn_form.config(state="normal") # QR button is now in modal
        # self._update_attendance_status_for_selected(emp_id_from_tree) # Already called above
        
        # Enable/disable buttons in "Selected Employee Actions" frame
        # These are in the left pane
        is_active_employee = (status_val == db_schema.STATUS_ACTIVE) # Corrected
        if hasattr(self, 'clock_in_btn'): self.clock_in_btn.config(state="normal" if is_active_employee else "disabled")
        if hasattr(self, 'clock_out_btn'): self.clock_out_btn.config(state="normal" if is_active_employee else "disabled")
        if hasattr(self, 'view_attendance_btn'): self.view_attendance_btn.config(state="normal") # Always enabled if selected
        if hasattr(self, 'manage_vacations_btn_employee_view'): self.manage_vacations_btn_employee_view.config(state="normal") # Always enabled if selected

        # Update recommendations and alerts section
        self._update_recommendations_for_selected(full_employee_details)

        # Load data for the currently selected internal tab
        self._on_employee_details_tab_changed()

    def _on_employee_details_tab_changed(self, event=None):
        """Loads data for the newly selected tab in the employee details notebook."""
        selected_item = self.tree.focus()
        if not selected_item: return # No employee selected

        emp_id = self.tree.item(selected_item, "values")[0]
        if not emp_id: return

        selected_tab_index = self.employee_details_notebook.index(self.employee_details_notebook.select())
        tab_text = self.employee_details_notebook.tab(selected_tab_index, "text")

        # Clear all tabs first (or just the one being loaded?)
        # Clearing all might be safer but less performant. Let's clear only the relevant one.

        if tab_text == "General Info":
            # Data is already loaded by on_tree_select
            pass
        elif tab_text == "Attendance":
            self._load_attendance_log_tab(emp_id)
        elif tab_text == "Payroll":
            self._load_payslip_history_tab(emp_id)
        elif tab_text == "Documents":
            self._load_documents_tab(emp_id)
        elif tab_text == "Action Log":
            self._load_action_log_tab(emp_id)

    def _update_recommendations_for_selected(self, employee_details: Dict):
        """Checks for missing data and low vacation balance and updates the recommendations text."""
        if not hasattr(self, 'recommendations_text') or not self.recommendations_text.winfo_exists(): return

        recommendations = []

        # Check for missing data
        missing_fields = []
        fields_to_check = { # Corrected
            db_schema.COL_EMP_PHOTO_PATH: "Photo",
            db_schema.COL_EMP_EMAIL: "Email Address",
            db_schema.COL_EMP_PHONE: "Phone Number",
            db_schema.COL_EMP_MARITAL_STATUS: "Marital Status",
            db_schema.COL_EMP_EDUCATION: "Educational Qualification",
            db_schema.COL_EMP_EMPLOYMENT_HISTORY: "Employment History",
            db_schema.COL_EMP_START_DATE: "Start Date",
            db_schema.COL_EMP_DEVICE_USER_ID: "Device User ID",
        }

        for key, label in fields_to_check.items():
            value = employee_details.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(label)

        if missing_fields:
            recommendations.append(f"Missing Data: {', '.join(missing_fields)}")

        # Check for low vacation balance
        try:
            vacation_balance = db_queries.get_employee_vacation_balance_db(employee_details[db_schema.COL_EMP_ID]) # Corrected
            # Check if balance is an integer (not "N/A (Excluded)")
            if isinstance(vacation_balance, int):
                low_balance_threshold = 5 # Define threshold
                if vacation_balance < low_balance_threshold:
                    recommendations.append(f"Low Vacation Balance: {vacation_balance} days remaining.")
                elif vacation_balance == 0:
                     recommendations.append("Vacation Balance: 0 days remaining.")
            # If balance is "N/A (Excluded)", no recommendation needed here
        except Exception as e:
            logger.error(f"Error checking vacation balance for recommendations: {e}")
            # Don't add a recommendation if there's an error fetching balance

        # Update the text widget
        self.recommendations_text.config(state="normal")
        self.recommendations_text.delete("1.0", tk.END)
        if recommendations:
            self.recommendations_text.insert("1.0", "Recommendations:\n- " + "\n- ".join(recommendations))
        else:
            self.recommendations_text.insert("1.0", "No recommendations or alerts for this employee.")
        self.recommendations_text.config(state="disabled")


    def _update_attendance_buttons_state(self, emp_id: Optional[str]):
        """Enable/disable attendance buttons based on whether an employee is selected."""
        # This method is largely superseded by logic in on_tree_select and _reset_selection_dependent_ui
        # Kept for reference or if specific separate logic is needed later.
        is_selected_and_active = False
        current_emp_id = emp_id or (self.tree.item(self.tree.selection()[0], "values")[0] if self.tree.selection() else None)
        if current_emp_id:
            emp_details = db_queries._find_employee_by_id(emp_id) # Corrected
            if emp_details and emp_details.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE: # Corrected
                is_selected_and_active = True

        state_to_set = "normal" if is_selected_and_active else "disabled"
        
        if hasattr(self, 'clock_in_btn'): self.clock_in_btn.config(state=state_to_set)
        if hasattr(self, 'clock_out_btn'): self.clock_out_btn.config(state=state_to_set)
        
        view_log_state = "normal" if current_emp_id else "disabled" # View log can be for any selected employee
        if hasattr(self, 'view_attendance_btn'): self.view_attendance_btn.config(state=view_log_state)
        
        if not current_emp_id and hasattr(self, 'attendance_status_var'):
            self.attendance_status_var.set(_("status_select_employee"))

    def _set_employee_attendance_status_label(self, emp_id: str):
        """Updates the attendance status label and checks for tardiness today."""
        if not hasattr(self, 'attendance_status_var') or not hasattr(self, 'tardiness_alert_label'):
            return # Widgets not created

        try:
            status_info = attendance_utils.get_employee_attendance_status_today(emp_id)
            
            # Use the comprehensive status message from attendance_utils
            self.attendance_status_var.set(status_info.get("status_message", _("status_not_available")))

            # Update tardiness alert label based on is_late from status_info
            if status_info.get("is_late") is True:
                lateness_detail = _("status_lateness_detail", minutes=status_info.get("lateness_minutes", 0))
                self.tardiness_alert_label.config(text=f"⏰ {_('status_late')} ({lateness_detail})")
            else:
                self.tardiness_alert_label.config(text="")

        except Exception as e:
            logger.error(f"Error fetching attendance status for {emp_id}: {e}")
            self.attendance_status_var.set("Status: Error fetching status")
            self.tardiness_alert_label.config(text="") # Clear alert on error
    
    def _refresh_attendance_log_for_selected_employee(self):
        """
        Helper method to refresh the attendance log tab for the
        currently selected employee in the main employee list.
        """
        selected_item = self.tree.focus() # Main employee list
        if not selected_item:
            logger.info("No employee selected to refresh attendance log.")
            # Optionally clear the attendance tree if no employee is selected
            if hasattr(self, 'emp_detail_attendance_tree'):
                for item in self.emp_detail_attendance_tree.get_children():
                    self.emp_detail_attendance_tree.delete(item)
            return

        try:
            emp_id = self.tree.item(selected_item, "values")[0]
            if emp_id:
                self._load_attendance_log_tab(emp_id)
            else: # Should not happen if tree is populated correctly
                logger.warning("Could not get emp_id for selected item to refresh attendance log.")
        except IndexError:
            logger.error("IndexError getting emp_id for refreshing attendance log.")

    def _load_attendance_log_tab(self, emp_id: str):
        """Loads attendance log data for the selected employee into the Attendance tab."""
        if not hasattr(self, 'attendance_log_tree') or not self.attendance_log_tree.winfo_exists(): return # Tab not created/visible

        for item in self.attendance_log_tree.get_children():
            self.attendance_log_tree.delete(item)
        self.attendance_total_hours_var.set("Total Hours Worked: 0.00")
        self.attendance_total_days_var.set("Total Days Present: 0")

        start_date_str = self.attendance_start_date_entry.entry.get()
        end_date_str = self.attendance_end_date_entry.entry.get()

        try:
            start_dt = dt_date.fromisoformat(start_date_str)
            end_dt = dt_date.fromisoformat(end_date_str)
            if start_dt > end_dt:
                messagebox.showerror("Input Error", "Start date cannot be after end date.", parent=self.root) # Use root as parent
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format. Please use YYYY-MM-DD for both dates.", parent=self.root) # Use root as parent
            return

        try:
            logs = db_queries.get_attendance_logs_for_employee_period(emp_id, start_date_str, end_date_str) # Corrected
            total_hours = 0.0
            present_days = set()

            if not logs:
                # messagebox.showinfo("No Records", "No attendance records found for the selected criteria.", parent=self.root) # Avoid modal dialog on tab change
                return

            for log in logs:
                clock_in_dt = datetime.strptime(log[db_schema.COL_ATT_CLOCK_IN], '%Y-%m-%d %H:%M:%S') # Corrected
                clock_out_dt_str = log.get(db_schema.COL_ATT_CLOCK_OUT) # Corrected
                clock_out_display = ""
                duration_str = "N/A (Open)"

                if clock_out_dt_str:
                    clock_out_dt = datetime.strptime(clock_out_dt_str, '%Y-%m-%d %H:%M:%S')
                    clock_out_display = clock_out_dt.strftime('%I:%M:%S %p')
                    duration = db_queries.calculate_worked_duration(log[db_schema.COL_ATT_CLOCK_IN], clock_out_dt_str) # Corrected
                    if duration is not None:
                        duration_str = f"{duration:.2f}"
                        total_hours += duration
                        present_days.add(log[db_schema.COL_ATT_LOG_DATE]) # Corrected
                
                self.attendance_log_tree.insert("", "end", values=(
                    log[db_schema.COL_ATT_LOG_DATE], # Corrected
                    clock_in_dt.strftime('%I:%M:%S %p'), # Format for display
                    clock_out_display,
                    duration_str
                ))
            
            self.attendance_total_hours_var.set(f"Total Hours Worked: {total_hours:.2f}")
            self.attendance_total_days_var.set(f"Total Days Present: {len(present_days)}")

        except (EmployeeNotFoundError, DatabaseOperationError) as e:
            logger.error(f"Error loading attendance log for tab: {e}")
            # messagebox.showerror("Error", str(e), parent=self.root) # Avoid modal dialog on tab change
        except Exception as e:
            logger.error(f"Unexpected error loading attendance log for tab: {e}")
            # messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self.root) # Avoid modal dialog

    def _load_payslip_history_tab(self, emp_id: str):
        """Loads payslip history for the selected employee into the Payroll tab."""
        if not hasattr(self, 'payslip_history_tree') or not self.payslip_history_tree.winfo_exists(): return # Tab not created/visible

        for item in self.payslip_history_tree.get_children():
            self.payslip_history_tree.delete(item)

        try:
            # Backend function get_payslips_for_employee_db is used
            payslips = db_queries.get_payslips_for_employee_db(emp_id) # Corrected

            if not payslips:
                # messagebox.showinfo("No Records", "No payslips found for this employee.", parent=self.root) # Avoid modal dialog
                return

            for payslip in payslips:
                self.payslip_history_tree.insert("", "end", values=( # Corrected
                    payslip[db_schema.COL_PAY_ID], # Corrected
                    payslip[db_schema.COL_PAY_PERIOD_START], # Corrected
                    payslip[db_schema.COL_PAY_PERIOD_END], # Corrected
                    f"${payslip[db_schema.COL_PAY_NET_PAY]:,.2f}", # Corrected
                    payslip[db_schema.COL_PAY_GENERATION_DATE] # Corrected
                ))

        except (EmployeeNotFoundError, DatabaseOperationError) as e:
            logger.error(f"Error loading payslip history for tab: {e}")
            # messagebox.showerror("Error", str(e), parent=self.root) # Avoid modal dialog
        except Exception as e:
            logger.error(f"Unexpected error loading payslip history for tab: {e}")
            # messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self.root) # Avoid modal dialog

    # Need to add get_payslips_for_employee_db backend function
    
    def _create_search_view_widgets(self, parent_frame):
        """Creates the UI for the dedicated Search view."""        
        info_label_key = "adv_search_info_open_from_sidebar_label" # New key
        info_label = ttk.Label(parent_frame, text=_(info_label_key), font=("Helvetica", 14), wraplength=400, justify="center")
        info_label.pack(pady=20, expand=True)
        self._add_translatable_widget(info_label, info_label_key)

        open_adv_search_btn_key = "adv_search_open_window_btn" # New key
        open_adv_search_btn = ttk.Button(parent_frame, text=_(open_adv_search_btn_key), command=self._gui_open_advanced_search_window, bootstyle=db_schema.BS_PRIMARY_ACTION)
        open_adv_search_btn.pack(pady=10)
        self._add_translatable_widget(open_adv_search_btn, open_adv_search_btn_key)

    def _gui_open_advanced_search_window(self):
        """Opens the AdvancedSearchWindow."""
        self.parent_app._create_and_show_toplevel(AdvancedSearchWindow, tracker_attr_name="active_advanced_search_window")

    def gui_search_employee(self):
        search_term = self.left_pane_search_term_entry.get().strip()
        search_field = self.search_field_var.get()
        gender_selection = self.gender_filter_var.get()

        gender_filter_value = None
        if gender_selection != _("gender_option_all"): # Check against the translated "All"
            # Map translated UI selection back to potential DB values if necessary,
            # or ensure DB stores "Male", "Female", "Other" directly.
            # For simplicity, assuming UI values match DB values for Male, Female, Other.
            if gender_selection == _("gender_option_male"): gender_filter_value = "Male"
            elif gender_selection == _("gender_option_female"): gender_filter_value = "Female"
            elif gender_selection == _("gender_option_other"): gender_filter_value = "Other"

        if not search_field: # Should be set by combobox default
            messagebox.showwarning("Search Error", "Please select a field to search by.")
            return
        results = db_queries.search_employees_db(search_term, search_field, gender_filter=gender_filter_value, include_archived=False)        
        self._populate_treeview(results)
        self._reset_selection_dependent_ui()
        self._update_stats_summary() # Update stats after search

        if not results:
            self.status_var.set(f"No employees found matching '{search_term}' in {search_field.replace('_', ' ').title()}.") # Corrected attribute name
            messagebox.showinfo("Search Result", f"No employees found matching '{search_term}' in {search_field.capitalize()}.")
        else:
            self.status_var.set(f"{len(results)} employees found matching '{search_term}'.")

    

    def gui_update_employee(self):
        # This button now launches the modal for editing.
        # Get selected employee ID from the tree.
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showerror(_("input_error_title"), _("no_employee_selected_error"), parent=self.root)
            return

        # If we reach here, an employee is selected
        emp_id = self.tree.item(selected_items[0], "values")[0]

        # Open the EmployeeFormWindow in 'edit' mode
        self.parent_app._create_and_show_toplevel(
            EmployeeFormWindow, mode='edit', employee_id=emp_id,
            callback_on_save=self.gui_show_all_employees,
            tracker_attr_name=f"active_employee_form_window_edit_{emp_id}" # Unique tracker for edit mode
        )
        
    def gui_export_to_csv(self):
        """Exports all employee data to a CSV file."""
        employees = db_queries.get_all_employees_db()
        if not employees:
            messagebox.showinfo("Export CSV", "No employee data to export.", parent=self.root)
            return

        filepath_to_save = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[(_("csv_file_type_label"), "*.csv"), (_("all_files_type_label"), "*.*")],
            title="Save Employees as CSV",
            parent=self.root
        )
        if not filepath_to_save:
            return

        fieldnames = [
            db_schema.COL_EMP_ID, db_schema.COL_EMP_NAME, "department_name", db_schema.COL_EMP_POSITION,
            db_schema.COL_EMP_SALARY, db_schema.COL_EMP_VACATION_DAYS, db_schema.COL_EMP_START_DATE,
            db_schema.COL_EMP_PHONE, db_schema.COL_EMP_EMAIL, db_schema.COL_EMP_GENDER,
            db_schema.COL_EMP_MARITAL_STATUS, db_schema.COL_EMP_EDUCATION,
            db_schema.COL_EMP_EMPLOYMENT_HISTORY, db_schema.COL_EMP_DEVICE_USER_ID,
            db_schema.COL_EMP_PHOTO_PATH, "exclude_vacation_policy",
            db_schema.COL_EMP_STATUS, db_schema.COL_EMP_TERMINATION_DATE
        ]
        try:
            with open(filepath_to_save, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for emp in employees:
                    writer.writerow(emp)
            messagebox.showinfo("Export CSV", f"Employee data successfully exported to\n{filepath_to_save}", parent=self.root)
            self.status_var.set(f"Data exported to CSV: {os.path.basename(filepath_to_save)}")
        except IOError as e:
            messagebox.showerror("Export Error", f"Failed to write CSV file: {e}", parent=self.root)

    def gui_export_to_pdf(self): # type: ignore
        employees = db_queries.get_all_employees_db() # Corrected
        """Exports all employee data to a PDF file."""
        if not employees:
            messagebox.showinfo("Export PDF", "No employee data to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[(_("pdf_file_type_label"), "*.pdf"), (_("all_files_type_label"), "*.*")],
            title="Save Employees as PDF"
        )
        if not filepath: # Check the original variable name
            return # User cancelled


        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph("Employee List", styles['h1']))
            elements.append(Spacer(1, 0.2*72)) # 0.2 inch space

            data = [[
                db_schema.COL_EMP_ID.capitalize(), # Corrected
                db_schema.COL_EMP_NAME.capitalize(), # Corrected
                "Department", # Use a generic "Department" as COL_EMP_DEPARTMENT is now department_name
                db_schema.COL_EMP_POSITION.capitalize(), # Corrected
                db_schema.COL_EMP_SALARY.capitalize(), # Corrected
                db_schema.COL_EMP_VACATION_DAYS.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_START_DATE.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_PHONE.capitalize(), # Corrected
                db_schema.COL_EMP_EMAIL.capitalize(), # Corrected
                db_schema.COL_EMP_GENDER.capitalize(), # Corrected
                db_schema.COL_EMP_MARITAL_STATUS.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_EDUCATION.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_EMPLOYMENT_HISTORY.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_PHOTO_PATH.capitalize().replace("_", " "), # Corrected
                db_schema.COL_EMP_DEVICE_USER_ID.capitalize().replace("_", " "), # Corrected
                "Exclude Vacation Policy", # New header
                db_schema.COL_EMP_STATUS.capitalize(), # Corrected
                db_schema.COL_EMP_TERMINATION_DATE.capitalize().replace("_", " ") # Corrected
            ]] # Header row
            for emp in employees:
                # --- Instant Status Assessment ---
                status_data = attendance_utils.get_employee_attendance_status_today(emp[db_schema.COL_EMP_ID])
                today_status_display = status_data.get("status_message", _("status_not_available")) 
                # status_not_available would be a new localization key e.g. "Status N/A"
                # --- End Instant Status Assessment ---

                data.append([
                    emp[db_schema.COL_EMP_ID], # Corrected
                    emp[db_schema.COL_EMP_NAME], # Corrected
                    emp.get("department_name", "Unassigned"), # Corrected: Use "department_name"
                    emp[db_schema.COL_EMP_POSITION], # Corrected
                    f"${emp[db_schema.COL_EMP_SALARY]:.2f}", # Corrected
                    emp.get(db_schema.COL_EMP_VACATION_DAYS, 0), # Corrected
                    emp.get(db_schema.COL_EMP_START_DATE, ""), # Corrected
                    emp.get(db_schema.COL_EMP_PHONE, ""), # Corrected
                    emp.get(db_schema.COL_EMP_EMAIL, ""), # Corrected
                    emp.get(db_schema.COL_EMP_GENDER, ""), # Corrected
                    emp.get(db_schema.COL_EMP_MARITAL_STATUS, ""), # Corrected
                    emp.get(db_schema.COL_EMP_EDUCATION, ""), # Corrected
                    emp.get(db_schema.COL_EMP_EMPLOYMENT_HISTORY, ""), # Corrected
                    emp.get(db_schema.COL_EMP_PHOTO_PATH, ""), # Corrected
                    "Yes" if emp.get("exclude_vacation_policy", 0) == 1 else "No", # Add exclusion status
                    emp.get(db_schema.COL_EMP_DEVICE_USER_ID, ""), # Corrected
                    emp.get(db_schema.COL_EMP_STATUS, "N/A"), # Corrected
                    emp.get(db_schema.COL_EMP_TERMINATION_DATE, "") # Corrected
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), reportlab_colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), reportlab_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), reportlab_colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, reportlab_colors.black) # Use reportlab_colors
            ]))
            elements.append(table)
            doc.build(elements)
            messagebox.showinfo("Export PDF", f"Employee data successfully exported to\n{filepath}")
            self.status_var.set(f"Data exported to PDF: {os.path.basename(filepath)}")
        except Exception as e: # Catching general exception for ReportLab
            logger.error(f"Error generating PDF report: {e}", exc_info=True)
            messagebox.showerror("Export PDF Error", f"Failed to export to PDF: {e}")

    def gui_import_from_csv(self):
        filepath = filedialog.askopenfilename(
            filetypes=[(_("csv_file_type_label"), "*.csv"), (_("all_files_type_label"), "*.*")],
            title="Import Employees from CSV"
        )
        if not filepath:
            return


        imported_count = 0
        error_count = 0
        db_conn_for_import = None # Initialize connection variable

        try:
            db_conn_for_import = sqlite3.connect(DATABASE_NAME)
            # Optionally, start a transaction explicitly if needed, though commit/rollback handles it.
            # db_conn_for_import.execute("BEGIN TRANSACTION")

            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                # Expected headers now include new fields
                for row_num, row_data in enumerate(reader, 1): # Use enumerate for better logging
                    try:
                        # For department, we expect department NAME in CSV, need to find its ID
                        dept_name_csv = row_data.get(db_schema.COL_EMP_DEPARTMENT) # Corrected # CSV provides department name
                        dept_id_for_import = None
                        if dept_name_csv:
                            dept_obj = get_department_by_name_db(dept_name_csv)
                            if dept_obj:
                                dept_id_for_import = dept_obj[COL_DEPT_ID]
                            else:
                                logger.warning(f"Department '{dept_name_csv}' not found for row {row_num}. Employee will be unassigned.")
                        name = row_data[db_schema.COL_EMP_NAME] # Corrected
                
                        pos = row_data[db_schema.COL_EMP_POSITION] # Corrected
                        salary = float(row_data[db_schema.COL_EMP_SALARY]) # Corrected
                        phone = row_data.get(COL_EMP_PHONE) # Optional
                        email = row_data.get(COL_EMP_EMAIL) # Optional
                        photo_path_csv = row_data.get(COL_EMP_PHOTO_PATH) # Optional
                        start_date_csv = row_data.get(COL_EMP_START_DATE) # Optional but recommended
                        marital_status_csv = row_data.get(COL_EMP_MARITAL_STATUS) # Optional
                        gender_csv = row_data.get(COL_EMP_GENDER) # Optional, ensure CSV header matches COL_EMP_GENDER
                        education_csv = row_data.get(COL_EMP_EDUCATION) # Optional
                        employment_history_csv = row_data.get(COL_EMP_EMPLOYMENT_HISTORY) # Optional
                        # Handle exclude_vacation_policy, default to 0 if missing or invalid
                        exclude_vacation_csv = int(row_data.get("exclude_vacation_policy", "0")) if row_data.get("exclude_vacation_policy", "0").isdigit() else 0
                        device_user_id_csv = row_data.get(COL_EMP_DEVICE_USER_ID) # Optional
                        # Handle vacation_days, default to 0 if missing or invalid in CSV
                        try:
                            vacation_days = int(row_data.get(COL_EMP_VACATION_DAYS, "0"))
                        except ValueError:
                            vacation_days = 0 # Default if conversion fails

                        # Pass the existing connection to add_employee
                        db_queries.add_employee_db(name, dept_id_for_import, pos, salary, vacation_days, 
                                     phone, email, photo_path_csv, 
                                     start_date_csv, marital_status_csv, gender_csv, education_csv, employment_history_csv,
                                     exclude_vacation_policy=exclude_vacation_csv, device_user_id=device_user_id_csv,
                                     existing_conn=db_conn_for_import)
                        imported_count += 1
                    except (InvalidInputError, DatabaseOperationError) as add_err:
                        logger.warning(f"Skipping row {row_num} during CSV import due to error: {row_data} - {add_err}")
                        error_count +=1
                    except KeyError as ke: # Missing column in CSV
                        logger.warning(f"Skipping row {row_num} due to missing column '{ke}': {row_data}")
                        error_count += 1
                    except ValueError as ve: # Bad salary format
                        logger.warning(f"Skipping row {row_num} due to invalid salary format: {row_data} - {ve}")
                        error_count += 1
            
            db_conn_for_import.commit() # Commit all successful inserts at once
            logger.info(f"CSV Import: Committed {imported_count} new employees.")

        except sqlite3.Error as db_e: # Catch errors related to the connection or final commit
            if db_conn_for_import:
                db_conn_for_import.rollback() # Rollback if commit failed or other DB error
            logger.error(f"Database error during CSV import transaction: {db_e}")
            messagebox.showerror("Import Error", f"A database error occurred during import: {db_e}")
            # Potentially update error_count or set imported_count to 0 if the whole transaction failed
        except IOError as e:
            messagebox.showerror("Import Error", f"Failed to read CSV file: {e}")
        except Exception as e: # Catch other potential errors during processing
            if db_conn_for_import:
                db_conn_for_import.rollback()
            logger.error(f"An unexpected error occurred during CSV import: {e}")
            messagebox.showerror("Import Error", f"An unexpected error occurred during import: {e}")
        finally:
            if db_conn_for_import:
                db_conn_for_import.close()

        self.gui_show_all_employees()
        summary_message = f"Import complete.\nSuccessfully imported: {imported_count}\nRows with errors: {error_count}"
        self.status_var.set(f"CSV Import: {imported_count} imported, {error_count} errors.")
        messagebox.showinfo("Import CSV", summary_message)
  
    @staticmethod
    def get_theme_palette(theme_name="light"):
        return get_theme_palette_global(theme_name) # Use global helper

    @staticmethod
    def apply_theme_globally(root_tk_instance, app_theme_name_str: str, style_obj: tkb.Style): # app_theme_name_str is "light" or "dark"
        """
        Applies the ttkbootstrap theme globally.
        Args:
            root_tk_instance: The main Tk root window.
            app_theme_name_str: The application's logical theme name ("light" or "dark").
            style_obj: The ttkbootstrap.Style instance.
        """
        if not style_obj:
            logger.error("apply_theme_globally: style_obj is None. Cannot apply theme.")
            return

        # Map app's logical theme ("light"/"dark") to specific ttkbootstrap theme names
        ttk_bootstrap_theme_to_apply = "cosmo" if app_theme_name_str == "light" else "darkly"
        palette = get_theme_palette_global(app_theme_name_str)

        # --- Critical Check: Ensure style_obj.theme is not None before calling theme_use ---
        # This is vital because style_obj.theme_use() itself will raise an AttributeError if style_obj.theme is None.
        initial_style_theme_name = "None"
        if not root_tk_instance.winfo_exists(): # Prevent operations on destroyed root
            logger.warning(f"apply_theme_globally called on a destroyed root window: {root_tk_instance}")
            return

        # Force Tk to process all pending events, including window destruction/creation,
        # before attempting to change the theme, which iterates over existing widgets.
        if root_tk_instance.winfo_exists():
            root_tk_instance.update()

        palette = get_theme_palette_global(app_theme_name_str) # Use global helper
        # DO NOT create a new Style object here. Use the passed one.
        original_theme_name_for_style_object = style_obj.theme.name if style_obj.theme else "Unknown (style.theme was None)"
        logger.info(f"Before theme_use('{ttk_bootstrap_theme_to_apply}'): style_obj.theme.name = {original_theme_name_for_style_object}")

        if style_obj.theme is None:
            logger.error(f"Style object's theme is None before attempting to apply '{ttk_bootstrap_theme_to_apply}'. Trying to recover by loading 'clam'.")
            try:
                style_obj.load_theme("clam") # Attempt to load 'clam' directly into the Style object
                if style_obj.theme and style_obj.theme.name:
                    style_obj.tk.call("ttk::style", "theme", "use", style_obj.theme.name) # Apply it to Tk
                    logger.info(f"Recovered Style object by loading and applying '{style_obj.theme.name}'.")
                    # If recovery was needed, we might stick to 'clam' for this run or re-evaluate.
                    # For now, if 'clam' loaded, let's use it as the theme_to_apply.
                    ttk_bootstrap_theme_to_apply = style_obj.theme.name 
                else:
                    logger.critical("Recovery by loading 'clam' failed. Style object theme remains None. Aborting theme application.")
                    return # Cannot proceed if style_obj.theme is still None
            except Exception as e_recover:
                logger.critical(f"Exception during Style object recovery with 'clam': {e_recover}. Aborting theme application.")
                return
        try:
            if root_tk_instance.winfo_exists():
                style_obj.theme_use(ttk_bootstrap_theme_to_apply) # This might raise AttributeError if style_obj.theme was None
                logger.info(f"Applied ttkbootstrap theme: {ttk_bootstrap_theme_to_apply}")
        except tk.TclError as e:
            logger.error(f"TclError applying primary theme '{ttk_bootstrap_theme_to_apply}': {e}. Attempting fallback ttkbootstrap theme.")
            if root_tk_instance.winfo_exists(): # Good check
                try:
                    fallback_bootstrap_theme = "litera" # Default light ttkbootstrap theme
                    logger.info(f"Attempting to apply fallback ttkbootstrap theme: {fallback_bootstrap_theme}")
                    style_obj.theme_use(fallback_bootstrap_theme) 
                    logger.info(f"Successfully applied ttkbootstrap fallback theme: {fallback_bootstrap_theme}.")
                    # Note: If this fallback is applied, self.current_theme ("light"/"dark") might be out of sync
                    # with the actual ttkbootstrap theme ("litera"). This might need further handling if precise
                    # logical theme state is critical after a fallback.
                except Exception as e_fallback: # Catch any error during fallback attempt
                    logger.critical(f"Fallback ttkbootstrap theme '{fallback_bootstrap_theme}' also failed: {e_fallback}.")
        except AttributeError as ae: # Catch AttributeError if style.theme.name was accessed when style.theme is None
            logger.error(f"AttributeError during theme_use for '{ttk_bootstrap_theme_to_apply}': {ae}. This usually means style_obj.theme was None when theme_use was called.")
            # This path indicates a more severe issue with style_obj itself or its .theme attribute.
            # Attempting another theme_use might also fail.
            try:
                # Try a very basic ttk theme as a last resort if ttkbootstrap ones fail catastrophically
                style_obj.theme_use("litera") # Or another default ttkbootstrap theme
                current_theme_name_after_attr_clam = "Unknown (style.theme is None)"
                try:
                    if style_obj.theme and hasattr(style_obj.theme, 'name') and style_obj.theme.name:
                        current_theme_name_after_attr_clam = style_obj.theme.name
                    elif style_obj.theme:
                        current_theme_name_after_attr_clam = f"Unnamed (Type: {type(style_obj.theme).__name__})"
                    else:
                        current_theme_name_after_attr_clam = "None (theme is None)"
                except Exception as e_get_name:
                    logger.debug(f"Could not get theme name after clam fallback (AttributeError path): {e_get_name}")
                    current_theme_name_after_attr_clam = "None (theme is None)"

                logger.info(f"Successfully applied ttkbootstrap fallback theme: clam (after AttributeError). New style.theme.name: {current_theme_name_after_attr_clam}")
            except Exception as e_fallback_attr:
                 logger.critical(f"Fallback theme 'litera' after AttributeError also failed: {e_fallback_attr}")
        except Exception as ex: # Catch any other unexpected error during primary theme application
            current_theme_name_after_other_fail = "Unknown (style.theme is None)"
            try:
                if style_obj.theme and hasattr(style_obj.theme, 'name') and style_obj.theme.name:
                    current_theme_name_after_other_fail = style_obj.theme.name
                elif style_obj.theme:
                    current_theme_name_after_other_fail = f"Unnamed (Type: {type(style_obj.theme).__name__})"
                else:
                    current_theme_name_after_other_fail = "None (theme is None)"
            except Exception as e_get_name:
                logger.debug(f"Could not get theme name after primary theme other failure: {e_get_name}")
                current_theme_name_after_other_fail = "None (theme is None)"

            logger.error(f"Unexpected error applying primary theme '{ttk_bootstrap_theme_to_apply}': {ex}. Current style.theme.name: {current_theme_name_after_other_fail}")
        if root_tk_instance.winfo_exists():
            root_tk_instance.config(bg=palette['bg_main'])
        # ttkbootstrap themes handle most ttk widget styling.
        # Manual configuration for TFrame, TLabel, TButton, TEntry, TCombobox, Treeview,
        # Treeview.Heading, TLabelframe, TNotebook is largely handled by style.theme_use().
        # We might only need to style non-ttk widgets or apply very specific overrides.

        # Example: If you still need to style standard tk.Label differently
        # (though ttk.Label is preferred with ttkbootstrap)
        # for child in root_tk_instance.winfo_children():
        #     if isinstance(child, tk.Label) and not isinstance(child, ttk.Label):
        #         child.config(bg=palette['bg_secondary'], fg=palette['fg_primary'])

        # Styling for tk.Text (as it's not a ttk widget)
        # This can be done via option_add or by iterating and configuring.
        # ThemedToplevel._theme_text_widget will handle tk.Text inside Toplevels.
        # For tk.Text directly in HRAppGUI (if any), they'd need explicit styling.
        # The existing option_add lines are generally good for tk.Text.
        try:
            root_tk_instance.option_add("*Text.background", palette['entry_bg'])
            root_tk_instance.option_add("*Text.foreground", palette['entry_fg'])
            root_tk_instance.option_add("*Text.insertBackground", palette['entry_fg']) # Cursor color
            root_tk_instance.option_add("*Text.selectBackground", palette['tree_selected_bg'])
            root_tk_instance.option_add("*Text.selectForeground", palette['tree_selected_fg'])
        except tk.TclError as e_option_add:
            logger.warning(f"TclError during root.option_add for Text theming: {e_option_add}")


        # ttkbootstrap themes usually style TScrollbar and TNotebook well.
        # If specific overrides are needed for TScrollbar or TNotebook.Tab, they can be added here,
        # but it's best to rely on the ttkbootstrap theme first.
        # Example (if needed, but likely not with ttkbootstrap):
        # style.configure("Vertical.TScrollbar", background=palette['button_bg'], troughcolor=palette['bg_secondary'], arrowcolor=palette['fg_primary'])
        # style.configure("TNotebook.Tab", background=palette['bg_secondary'], foreground=palette['fg_primary']) # pragma: no cover
        # style.map("TNotebook.Tab", background=[("selected", palette['button_bg'])]) # pragma: no cover

    def _recursive_update_idletasks(self, widget):
        try:
            if widget.winfo_exists():
                widget.update_idletasks()
        except Exception as e:
            logger.debug(f"Error during recursive update_idletasks for {widget}: {e}")
        if hasattr(widget, 'winfo_children'): # Check if widget can have children
            for child in widget.winfo_children():
                self._recursive_update_idletasks(child)

    def apply_instance_theme(self, style_obj: tkb.Style): # Accept style_obj
        grabbed_toplevels = [] # Initialize grabbed_toplevels here
        
        # Phase 1: Ensure all widgets are known to Tcl by processing pending tasks
        if self.root.winfo_exists():
            self.root.update_idletasks() # Process main window first

        # Process all active Toplevels to ensure their widgets are registered
        for tl_window in list(self.active_toplevels): 
            try:
                if tl_window.winfo_exists():
                    self._recursive_update_idletasks(tl_window) # Ensure all widgets in Toplevel are processed
            except Exception as e:
                logger.warning(f"Error in _recursive_update_idletasks for {tl_window.title()} during pre-theme update: {e}")
        
        # Temporarily release grab from active modal toplevels
        for tl_window in list(self.active_toplevels):
            try:
                if tl_window.winfo_exists() and hasattr(tl_window, 'grab_status') and tl_window.grab_status():
                    logger.debug(f"Temporarily releasing grab from {tl_window.title()}")
                    tl_window.grab_release()
                    grabbed_toplevels.append(tl_window)
            except tk.TclError as e_grab_release:
                logger.warning(f"TclError releasing grab from {tl_window.title()}: {e_grab_release}")
            except Exception as e_other_release: # pragma: no cover
                logger.error(f"Unexpected error releasing grab from {tl_window.title()}: {e_other_release}")

        # Apply the theme globally using ttkbootstrap
        HRAppGUI.apply_theme_globally(self.root, self.current_theme, style_obj)

        # Update theme toggle button text
        if hasattr(self, 'theme_toggle_btn') and self.theme_toggle_btn.winfo_exists():
            self.theme_toggle_btn.config(text=_("toggle_light_mode_btn_text") if self.current_theme == "dark" else _("toggle_dark_mode_btn_text"))

        palette = get_theme_palette_global(self.current_theme) # Use global helper
        # The photo_preview_label in HRAppGUI is part of EmployeeFormWindow, not directly in HRAppGUI.
        # Theming of specific non-ttk widgets within Toplevels is handled by their update_local_theme_elements.

        # Instruct active Toplevels to update their local, non-ttk elements
        for tl_window in list(self.active_toplevels):
            try:
                if tl_window.winfo_exists():
                    # Recursively update idletasks for the toplevel and its children
                    self._recursive_update_idletasks(tl_window)
                    # Now call their specific method to update non-ttk elements based on the new theme
                    if hasattr(tl_window, 'update_local_theme_elements'):
                        tl_window.update_local_theme_elements()
            except tk.TclError as e_tl_update:
                logger.warning(f"TclError updating theme for toplevel {tl_window.title()}: {e_tl_update}")
            except Exception as e_other_tl_update: # pragma: no cover
                logger.error(f"Unexpected error updating theme for toplevel {tl_window.title()}: {e_other_tl_update}")

        # Re-apply grab to toplevels that had it
        for tl_window in grabbed_toplevels:
            try:
                if tl_window.winfo_exists():
                    logger.debug(f"Re-applying grab to {tl_window.title()}")
                    tl_window.grab_set()
            except tk.TclError as e_grab_set: # pragma: no cover
                logger.warning(f"TclError re-applying grab to {tl_window.title()}: {e_grab_set}")
            except Exception as e_other_set: # pragma: no cover
                logger.error(f"Unexpected error re-applying grab to {tl_window.title()}: {e_other_set}")

        # Specific update for photo_preview_label if it exists (as it's a ttk.Label but might need explicit bg)
        # This was likely for the main GUI's photo preview, which is now inside EmployeeFormWindow.
        # If there are other such labels directly in HRAppGUI, they can be handled here.
        if hasattr(self, 'photo_preview_label') and self.photo_preview_label.winfo_exists():
            self.photo_preview_label.configure(background=palette['entry_bg'], foreground=palette['fg_secondary'])

    def _apply_role_permissions(self):
        if not self.parent_app or not hasattr(self.parent_app, 'current_user_role'):
            logger.warning("Cannot apply role permissions: user role not available.")
            # Disable almost everything if role is unknown for safety
            # This state should ideally not be reached if login flow is correct.
            for child in self.root.winfo_children(): # A bit aggressive, refine later
                if isinstance(child, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Treeview)):
                    try: child.config(state="disabled")
                    except tk.TclError: pass # Some widgets might not support state
            return

        role = self.parent_app.current_user_role
        is_admin = (role == db_schema.ROLE_ADMIN)
        # is_manager = (role == ROLE_DEPT_MANAGER) # For future use
        # is_employee = (role == ROLE_EMPLOYEE)   # For future use

        # --- Enable/Disable widgets based on role ---
        # Admin-only buttons/features
        admin_only_widgets_names = [
            'add_btn', 'import_csv_btn', 'import_fp_logs_btn',
            'export_db_btn', 'restore_db_btn', # Data Ops # pragma: no cover
            'ua_add_user_btn', 'ua_update_role_btn', 'ua_delete_user_btn' # User admin buttons
        ]
        # Update button: more complex logic, for now, admin can update.
        # Employees might update their own, managers their dept.
        if hasattr(self, 'update_btn'):
            self.update_btn.config(state=tk.NORMAL if is_admin else tk.DISABLED) # pragma: no cover

        for widget_name in admin_only_widgets_names:
            if hasattr(self, widget_name):
                getattr(self, widget_name).config(state=tk.NORMAL if is_admin else tk.DISABLED)

        # --- Enable/Disable Top Bar Buttons based on Role ---
        # Iterate through the stored nav buttons and manage their state
        # We need to store references to these buttons when they are created.
        # A simple way is to add them to a list or dictionary in _create_top_bar_navigation.
        # For now, let's assume we can find them by text or a stored reference.
        # A more robust approach would be to store buttons in a dict like self.nav_buttons = {}

        # Find the User Admin button and set its state
        user_admin_button = None
        current_role = self.parent_app.current_user_role
        
        for key, button in self.nav_buttons.items():
            allowed_roles = self.nav_button_permissions.get(key, [])
            if current_role in allowed_roles:
                button.config(state=tk.NORMAL)
            else:
                button.config(state=tk.DISABLED)
    def update_status_bar_user(self, username: Optional[str], role: Optional[str]):
        """Updates the status bar with the current user's information."""
        if hasattr(self, 'status_var') and self.status_var:
            if username and role: # Corrected
                user_info = _("status_bar_logged_in_as", username=username, role=role)
                self.status_var.set(user_info)
            else:
                self.status_var.set(_("status_bar_not_logged_in")) # Corrected

    def update_ui_for_role(self, role: Optional[str]):
        """Updates the UI elements based on the current user's role."""
        self._apply_role_permissions() # This method already handles UI changes based on role

    def _create_and_show_toplevel(self, window_class, *args, tracker_attr_name: Optional[str] = None, **kwargs):
        """Helper to create, track, and show a Toplevel window."""
        # Pass the ApplicationController instance (self.parent_app) to the Toplevel
        # Check if it's EmployeeFormWindow and if one is already active
        if window_class == EmployeeFormWindow:
            # Ensure parent_app and active_employee_form_window are valid before accessing methods
            if self.parent_app and hasattr(self.parent_app, 'active_employee_form_window'):
                active_form = self.parent_app.active_employee_form_window
                if active_form and active_form.winfo_exists():
                    active_form.lift()
                    active_form.focus_set()
                    # No messagebox here, just bring to front. Messagebox can be annoying. # pragma: no cover
                    return None # Don't create a new one
        elif tracker_attr_name and self.parent_app: # Check for other tracked windows
            active_window = getattr(self.parent_app, tracker_attr_name, None)
            if active_window and active_window.winfo_exists():
                active_window.lift()
                active_window.focus_set()
                # No messagebox here, just bring to front.
                # messagebox.showinfo("Window Active", f"The '{active_window.title()}' window is already open.", parent=active_window)
                return None
        win = window_class(self.root, self.parent_app, *args, **kwargs) # Pass ApplicationController as app_instance
        # After win is created and its __init__ has run (including its own update_idletasks if added):
        if win.winfo_exists(): # Check if window was successfully created
            win.update_idletasks() # Process any pending tasks for the new Toplevel

        self.active_toplevels.append(win)
        if tracker_attr_name and self.parent_app:
            setattr(self.parent_app, tracker_attr_name, win)
            logger.debug(f"Registered {win.title()} with controller attribute {tracker_attr_name}")
        
        return win

    def _perform_zk_sync_threaded(self, ip: str, port: int, q_comm: queue.Queue):
        """Worker function to run ZKTeco sync in a separate thread."""
        # Pass the queue to sync_attendance_from_zkteco for progress updates
        try:
            # Pass q_comm to the sync function
            summary = sync_attendance_from_zkteco(ip, port, q_comm=q_comm)
            q_comm.put({"type": "summary", "data": summary})
        except Exception as e: # Catch any exception from the sync process
            q_comm.put({"type": "error", "data": e}) # Put the exception object itself into the queue

    def _check_zk_sync_status(self):
        """Checks the queue for ZKTeco sync results and updates GUI."""
        if not hasattr(self, 'sync_progressbar'): # Ensure progressbar exists
            logger.warning("Sync progressbar not found, cannot update status.")
            return # pragma: no cover
        # Cancel previous after call if it exists
        if self.zk_sync_after_id:
            self.root.after_cancel(self.zk_sync_after_id)
            self.zk_sync_after_id = None
        try:
            result = self.task_queue.get_nowait() # Check for result from the thread

            # Task finished, process result
            self.root.config(cursor="")
            if hasattr(self, 'resync_btn'): self.resync_btn.config(state="normal")
            if hasattr(self, 'test_conn_btn'): self.test_conn_btn.config(state="normal")
            if hasattr(self, 'sync_progressbar'):
                self.sync_progressbar.stop() # Stop indeterminate mode
                self.sync_progressbar.config(mode="determinate", value=0) # Reset

            # Handle different result types from ZK sync thread
            if result.get("type") == "error":
                error_obj = result["data"]
                error_type_name = type(error_obj).__name__
                err_msg = f"Sync failed: {error_type_name} - {str(error_obj)[:100]}"
                # Provide more specific status icon based on error type
                status_icon = "🔌 Error" if isinstance(error_obj, (ConnectionError, TimeoutError, ConnectionRefusedError)) else "❌ Error"
                
                self._update_sync_status_display(status=status_icon, message=err_msg)
                self._add_to_sync_log("❌", err_msg)
                if isinstance(error_obj, ConnectionError):
                    messagebox.showerror("Device Connection Error", f"Could not connect to ZKTeco device: {error_obj}", parent=self.root)
                elif isinstance(error_obj, (DatabaseOperationError, InvalidInputError)):
                    messagebox.showerror("Sync Error", f"Error during sync: {error_obj}", parent=self.root)
                else: # Other unexpected exceptions
                    logger.error(f"Unexpected error during ZKTeco sync thread: {error_obj}")
                    messagebox.showerror("Sync Error", f"An unexpected error occurred: {error_obj}", parent=self.root)
            elif result.get("type") == "summary": # Success
                summary = result["data"]
                success_msg = f"Sync successful. Processed: {summary.get('processed_device_logs',0)} logs."
                self._update_sync_status_display(status="✅ Online", last_sync_time=datetime.now().strftime("%Y-%m-%d %I:%M %p"), message=success_msg)
                self._add_to_sync_log("✅", success_msg)
               # db_queries.clock_in_employee(self.selected_employee_id, performed_by_user_id=user_id) # This line seems out of place here
                messagebox.showinfo("ZKTeco Sync Complete",
                                    f"Sync Summary:\nProcessed from device: {summary.get('processed_device_logs',0)}\n"
                                    f"Clock-Ins Added to DB: {summary.get('db_clock_ins',0)}\n"
                                    f"Clock-Outs Updated in DB: {summary.get('db_clock_outs',0)}\n"
                                    f"DB/Processing Errors: {summary.get('errors',0)}\n"
                                    f"Unknown Device User IDs: {summary.get('unknown_user_id',0)}",
                                    parent=self.root)
                
                self.gui_show_all_employees() # Refresh view
                if self.tree.selection(): # If an employee is selected, update their attendance status
                    selected_emp_id = self.tree.item(self.tree.selection()[0], "values")[0]
                    if selected_emp_id: self._update_attendance_status_for_selected(selected_emp_id)
                elif result.get("type") == "test_connection":
                    status_msg = result.get("message", "Test finished.")
                    device_status_icon = "✅ Online" if result.get("success") else "❌ Offline"
                    self._update_sync_status_display(status=device_status_icon, message=status_msg)
                    self._add_to_sync_log("🧪" if result.get("success") else "⚠️", status_msg)
                    messagebox.showinfo("Connection Test", status_msg, parent=self.root)
            elif result.get("type") == "progress_init":
                if hasattr(self, 'sync_progressbar'):
                    self.sync_progressbar.config(mode="determinate", maximum=result["total"], value=0)
                self.zk_sync_after_id = self.root.after(100, self._check_zk_sync_status) # Continue polling for updates
                return # Don't stop polling yet
            elif result.get("type") == "progress_update":
                if hasattr(self, 'sync_progressbar'):
                    self.sync_progressbar.config(value=result["current"])
                self.zk_sync_after_id = self.root.after(100, self._check_zk_sync_status) # Continue polling
                return # Don't stop polling yet

        except queue.Empty: # Queue is empty, task still running
            if hasattr(self, 'sync_progressbar') and self.sync_progressbar.cget("mode") == "indeterminate":
                self.sync_progressbar.step(5) # Increment progress if indeterminate
            self.zk_sync_after_id = self.root.after(200, self._check_zk_sync_status) # Check again after 200ms

    
        if self.zk_sync_after_id:
            self.root.after_cancel(self.zk_sync_after_id)
            self.zk_sync_after_id = None
            logger.debug("Cancelled ZK sync status check.")
        if self.csv_export_after_id:
            self.root.after_cancel(self.csv_export_after_id)
            self.csv_export_after_id = None
            logger.debug("Cancelled CSV export status check.")

    def _cancel_all_recurring_tasks(self):
        """Cancels all recurring 'after' tasks managed by HRAppGUI."""
        logger.info("HRAppGUI: Cancelling all recurring tasks.")
        # Add cancellation for other specific timers if they exist

    def toggle_theme(self, event=None):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        # HRAppGUI.apply_theme_globally(self.root, self.current_theme, self.style) # Pass self.style
        self.apply_instance_theme(self.style) # Use the instance method

    def gui_show_reports_window(self):
        self._create_and_show_toplevel(ReportsWindow, tracker_attr_name="active_reports_window")
        

    def gui_show_about_dialog(self):
        self._create_and_show_toplevel(AboutDialog, tracker_attr_name="active_about_dialog")

    def gui_show_attendance_log_window(self):
        self._create_and_show_toplevel(AttendanceLogViewerWindow, tracker_attr_name="active_attendance_log_viewer_window")
        
    def gui_show_vacation_management_window(self): # Added missing method
        self._create_and_show_toplevel(VacationManagementWindow, tracker_attr_name="active_vacation_management_window")

    
    def gui_show_payroll_window(self):
        self._create_and_show_toplevel(PayrollWindow, tracker_attr_name="active_payroll_window") # pragma: no cover

    def show_dashboard_view(self): # Added missing method
        self.gui_show_dashboard_window()

    def show_alerts_view(self):
        self.gui_show_alerts_window()
        
    def gui_show_alerts_window(self):
        self._create_and_show_toplevel(AlertsWindow, tracker_attr_name="active_alerts_window")
        

    def gui_show_dashboard_window(self):
        self._create_and_show_toplevel(DashboardWindow, tracker_attr_name="active_dashboard_window")

    

    def gui_show_app_settings_window(self):
        """Opens the Application Settings window."""
        self._create_and_show_toplevel(SettingsWindow, tracker_attr_name="active_settings_window")

    def gui_show_approvals_window(self): # pragma: no cover
        # Delegate to ApplicationController
        self.parent_app._create_and_show_toplevel(
            ApprovalsWindow, 
            tracker_attr_name="active_approvals_window"
        )

    def gui_show_interview_scheduling_window(self):
        """Opens the Interview Scheduling window."""
        self._create_and_show_toplevel(InterviewSchedulerWindow, tracker_attr_name="active_interview_scheduling_window")

    def gui_show_metrics_dashboard_window(self):
        """Opens the Metrics Dashboard window."""
        self._create_and_show_toplevel(MetricsDashboardWindow, tracker_attr_name="active_metrics_dashboard_window")

    def show_user_admin_view(self): # Added missing method
        """Opens the User Management window."""
        self.parent_app._create_and_show_toplevel(UserManagementWindow, tracker_attr_name="active_user_management_window")

    def gui_show_department_management_window(self):
        """Opens the Department Management window."""
        self.parent_app._create_and_show_toplevel(DepartmentManagementWindow, tracker_attr_name="active_department_management_window")

    def gui_show_training_course_management_window(self):
        """Opens the Training Course Management window."""
        self.parent_app._create_and_show_toplevel(TrainingCourseManagementWindow, tracker_attr_name="active_training_course_mgt_window")

    def gui_show_skill_management_window(self):
        """Opens the Skill Catalog Management window."""
        self.parent_app._create_and_show_toplevel(SkillManagementWindow, tracker_attr_name="active_skill_mgt_window")

    def _create_fingerprint_analysis_tab_content(self, parent_frame):
        """Creates the UI for the Fingerprint Analysis tab."""
        import_btn_key = "fp_analysis_import_btn"
        import_button = ttk.Button(parent_frame, text=_(import_btn_key), command=self._gui_import_fingerprint_log, bootstyle=db_schema.BS_ADD)
        import_button.pack(pady=10, padx=10, anchor="w")
        self._add_translatable_widget(import_button, import_btn_key)

        results_lf_key = "fp_analysis_results_frame_title"
        results_frame = ttk.LabelFrame(parent_frame, text=_(results_lf_key), padding="10")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self._add_translatable_widget(results_frame, results_lf_key, attr="title")

        self.fp_log_tree_cols = ("emp_id", "timestamp", "event_type", "device_id")
        self.fp_log_tree = ttk.Treeview(results_frame, columns=self.fp_log_tree_cols, show="headings")
        self._update_fp_log_tree_headers() # Set initial headers

        self.fp_log_tree.column("emp_id", width=100, anchor="w")
        self.fp_log_tree.column("timestamp", width=150, anchor="center")
        self.fp_log_tree.column("event_type", width=120, anchor="w")
        self.fp_log_tree.column("device_id", width=120, anchor="w", stretch=tk.YES)

        fp_scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.fp_log_tree.yview)
        self.fp_log_tree.configure(yscrollcommand=fp_scrollbar_y.set)
        fp_scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.fp_log_tree.xview)
        self.fp_log_tree.configure(xscrollcommand=fp_scrollbar_x.set)

        self.fp_log_tree.pack(side="left", fill="both", expand=True)
        fp_scrollbar_y.pack(side="right", fill="y")
        fp_scrollbar_x.pack(side="bottom", fill="x")

    def _update_fp_log_tree_headers(self):
        """Updates headers for the fingerprint log treeview."""
        if hasattr(self, 'fp_log_tree') and self.fp_log_tree.winfo_exists():
            self.fp_log_tree.heading("emp_id", text=_("fp_header_emp_id"))
            self.fp_log_tree.heading("timestamp", text=_("fp_header_timestamp"))
            self.fp_log_tree.heading("event_type", text=_("fp_header_event_type"))
            self.fp_log_tree.heading("device_id", text=_("fp_header_device_id"))

    def _gui_import_fingerprint_log(self):
        filepath = filedialog.askopenfilename(
            title=_("fp_analysis_import_btn"), # Reusing button text as title
            filetypes=[(_("csv_file_type_label"), "*.csv"), (_("all_files_type_label"), "*.*")],
            parent=self.root
        )
        if not filepath: return

        try:
            with self.parent_app.BusyContextManager(self.root): # Use BusyContextManager
                parsed_logs = fingerprint_log_processor.parse_fingerprint_csv(filepath)
            
            for item in self.fp_log_tree.get_children():
                self.fp_log_tree.delete(item)
            
            for log_entry in parsed_logs:
                self.fp_log_tree.insert("", "end", values=(
                    log_entry["employee_id"],
                    log_entry["timestamp_str"],
                    log_entry["event_type_display"],
                    log_entry["device_id"]
                ))
            messagebox.showinfo(_("success_title"), f"Successfully imported and displayed {len(parsed_logs)} fingerprint log entries.", parent=self.root)
        except ValueError as ve: # Catch specific error from parser for bad headers
            messagebox.showerror(_("input_error_title"), str(ve), parent=self.root)
        except Exception as e:
            logger.error(f"Error importing fingerprint log: {e}", exc_info=True)
            messagebox.showerror(_("error_title"), f"Failed to import fingerprint log: {e}", parent=self.root)

    def gui_sync_from_zkteco(self):
        # Use IP and Port from db_schema (database settings)
        ip = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_IP, config.ZKTECO_DEVICE_IP)
        port_str = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_PORT, str(config.ZKTECO_DEVICE_PORT))
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Configuration Error", 
                                 f"Invalid ZKTeco port configured in settings: '{port_str}'. Please correct it in App Settings.", parent=self.root)
            return

        if not ip or ip == "192.168.1.201" or not port: # Check for default/missing config
            messagebox.showwarning("ZKTeco Sync", 
                                   f"ZKTeco device IP/Port not configured or using default placeholder.\n"
                                   f"Current IP: {ip}, Port: {port}\n"
                                   "Please configure in settings.ini or via Application Settings if available.", 
                                   parent=self.root)
            return

        # Disable buttons in the Device Sync tab if they exist
        if hasattr(self, 'zk_resync_btn_tab'): self.zk_resync_btn_tab.config(state="disabled")
        if hasattr(self, 'zk_test_conn_btn_tab'): self.zk_test_conn_btn_tab.config(state="disabled")
        if hasattr(self, 'zk_sync_progressbar_tab'): self.zk_sync_progressbar_tab.start()
        self.root.config(cursor="watch")
        self.sync_message_var.set("Attempting to sync from ZKTeco device... Please wait.") # Use tab's var
        self.root.update_idletasks()

        # Start the sync in a new thread
        # Pass self.task_queue to the threaded function
        thread = threading.Thread(target=self._perform_zk_sync_threaded, args=(ip, port, self.task_queue), daemon=True)
        thread.daemon = True # So it exits when main app exits
        thread.start()

        # Start polling the queue for completion
        self._check_zk_sync_status()
        
    # --- New Device Sync Section Method ---
    def _perform_zk_test_connection_threaded(self, ip: str, port: int, q_comm: queue.Queue):
        """Worker function to test ZKTeco connection in a separate thread."""
        conn_test = None
        try:
            conn_test = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
            conn_test.connect()
            device_time = conn_test.get_time() # Simple command to test
            q_comm.put({"type": "test_connection", "success": True, "message": f"Successfully connected. Device time: {device_time}"})
        except Exception as e:
            q_comm.put({"type": "test_connection", "success": False, "message": f"Connection failed: {e}"})
        finally:
            if conn_test and conn_test.is_connect:
                conn_test.disconnect()

    def _gui_test_zk_connection(self): # Corrected
        ip = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_IP, config.ZKTECO_DEVICE_IP)
        port_str = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_PORT, str(config.ZKTECO_DEVICE_PORT))
        try: port = int(port_str)
        except ValueError:
            messagebox.showerror("Config Error", f"Invalid ZKTeco port: {port_str}", parent=self.root); return # type: ignore

        if hasattr(self, 'zk_resync_btn_tab'): self.zk_resync_btn_tab.config(state="disabled")
        if hasattr(self, 'zk_test_conn_btn_tab'): self.zk_test_conn_btn_tab.config(state="disabled")
        if hasattr(self, 'zk_sync_progressbar_tab'): self.zk_sync_progressbar_tab.start()
        self.root.config(cursor="watch")
        self._update_sync_status_display(message="Testing connection...")

        thread = threading.Thread(target=self._perform_zk_test_connection_threaded, args=(ip, port, self.task_queue))
        thread.daemon = True
        thread.start()
        self._check_zk_sync_status() # Start polling

    def _create_device_sync_section(self, parent_frame):
        """Creates the UI for the Device Sync tab."""
        # Main container frame for the panel
        panel_container = ttk.Frame(parent_frame, padding="15")
        panel_container.pack(expand=True, fill="both")

        # Device Info Section for the tab
        info_frame_key = "device_sync_info_frame_title" # Key needed
        info_frame = ttk.LabelFrame(panel_container, text=_(info_frame_key), padding="10")
        info_frame.pack(fill="x", pady=(0, 10))
        info_frame.columnconfigure(1, weight=1) # Make value column expand
        self._add_translatable_widget(info_frame, info_frame_key, attr="title")

        row_idx = 0
        assoc_device_lbl_key = "device_sync_assoc_device_label" # Key needed
        assoc_device_lbl = ttk.Label(info_frame, text=_(assoc_device_lbl_key))
        assoc_device_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(assoc_device_lbl, assoc_device_lbl_key)
        ttk.Label(info_frame, textvariable=self.device_name_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # Uses self.device_name_var
        row_idx += 1

        last_sync_lbl_key = "device_sync_last_sync_label" # Key needed
        last_sync_lbl = ttk.Label(info_frame, text=_(last_sync_lbl_key))
        last_sync_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(last_sync_lbl, last_sync_lbl_key)
        ttk.Label(info_frame, textvariable=self.last_sync_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # Uses self.last_sync_var
        row_idx += 1

        status_lbl_key = "device_sync_status_label" # Key needed
        status_lbl = ttk.Label(info_frame, text=_(status_lbl_key))
        status_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(status_lbl, status_lbl_key)
        ttk.Label(info_frame, textvariable=self.device_status_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # Uses self.device_status_var
        row_idx += 1

        # Action Buttons
        actions_frame = ttk.Frame(info_frame)
        actions_frame.grid(row=row_idx, column=0, columnspan=2, pady=10, sticky="ew")

        test_conn_btn_key_tab = "device_sync_test_conn_btn"
        self.zk_test_conn_btn_tab = ttk.Button(actions_frame, text=_(test_conn_btn_key_tab), command=self._gui_test_zk_connection, bootstyle=db_schema.BS_VIEW_EDIT)
        self.zk_test_conn_btn_tab.pack(side="left", padx=5)
        self._add_translatable_widget(self.zk_test_conn_btn_tab, test_conn_btn_key_tab)

        resync_btn_key_tab = "device_sync_resync_btn"
        self.zk_resync_btn_tab = ttk.Button(actions_frame, text=_(resync_btn_key_tab), command=self.gui_sync_from_zkteco, bootstyle=db_schema.BS_ADD)
        ToolTip(self.zk_resync_btn_tab, text="Fetch new attendance logs from the ZKTeco device.") # TODO: Translate tooltip
        self.zk_resync_btn_tab.pack(side="left", padx=5)
        self._add_translatable_widget(self.zk_resync_btn_tab, resync_btn_key_tab)


        # Auto Sync Toggle (Placeholder functionality)
        auto_sync_key = "device_sync_auto_sync_toggle" # Key needed
        self.toggle_auto_sync_btn = ttk.Checkbutton(actions_frame, text=_(auto_sync_key), variable=self.auto_sync_enabled_var, bootstyle="round-toggle", command=self._gui_toggle_auto_sync)
        self.toggle_auto_sync_btn.pack(side="left", padx=15)
        self._add_translatable_widget(self.toggle_auto_sync_btn, auto_sync_key) # Uses self.auto_sync_enabled_var

        # Progress and Status Messages
        progress_status_frame = ttk.Frame(panel_container)
        progress_status_frame.pack(fill="x", pady=5)

        self.zk_sync_progressbar_tab = ttk.Progressbar(progress_status_frame, mode="determinate", length=300)
        self.zk_sync_progressbar_tab.pack(side="left", padx=5, expand=True, fill="x")
        
        self.zk_sync_message_label_tab = ttk.Label(progress_status_frame, textvariable=self.sync_message_var, width=40, anchor="w") # Uses self.sync_message_var
        self.zk_sync_message_label_tab.pack(side="left", padx=5)

        # Sync Log Section
        log_frame_key = "device_sync_log_frame_title" # Key needed
        log_frame = ttk.LabelFrame(panel_container, text=_(log_frame_key), padding="10")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self._add_translatable_widget(log_frame, log_frame_key, attr="title")

        self.zk_sync_log_tree_tab = ttk.Treeview(log_frame, columns=("timestamp", "status", "message"), show="headings", height=5)
        self._update_zk_log_tree_headers_tab() # Call specific header update for this tree

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.zk_sync_log_tree_tab.yview)
        self.zk_sync_log_tree_tab.configure(yscrollcommand=log_scrollbar.set)
        
        self.zk_sync_log_tree_tab.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        self._update_zk_log_tree_headers_tab() # Call specific header update for this tree

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.zk_sync_log_tree_tab.yview)
        self.zk_sync_log_tree_tab.configure(yscrollcommand=log_scrollbar.set)
        
        self.zk_sync_log_tree_tab.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        self._update_sync_status_display() # Initial update

    def _gui_toggle_auto_sync(self):
        # Placeholder for auto-sync logic
        if self.auto_sync_enabled_var.get():
            messagebox.showinfo("Auto Sync", "Automatic synchronization enabled (feature pending).", parent=self.root)
            # Here you would typically save this setting and start a scheduler
        else:
            messagebox.showinfo("Auto Sync", "Automatic synchronization disabled.", parent=self.root)
            # Save setting and stop scheduler

    def _update_sync_status_display(self, status: Optional[str] = None, last_sync_time: Optional[str] = None, message: Optional[str] = None):
        """Updates the device sync status labels."""
        if status: self.device_status_var.set(status)
        if last_sync_time: self.last_sync_var.set(last_sync_time)
        if message: self.sync_message_var.set(message)

    def _add_to_sync_log(self, status_icon: str, message: str):
        """Adds an entry to the sync log display, keeping only the last 5."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.sync_log_data.insert(0, (timestamp, status_icon, message))
        if len(self.sync_log_data) > 5:
            self.sync_log_data.pop() # Keep only last 5
        # Refresh treeview
        for item in self.zk_sync_log_tree_tab.get_children(): # Use tab-specific tree
            self.zk_sync_log_tree_tab.delete(item)
        # Insert newest at the top of the tree
        for log_entry in self.sync_log_data: 
            self.zk_sync_log_tree_tab.insert("", 0, values=log_entry) # Use tab-specific tree
    
    def _update_zk_log_tree_headers_tab(self):
        """Updates the headers for the ZK sync log tree in the Device Sync tab."""
        if hasattr(self, 'zk_sync_log_tree_tab') and self.zk_sync_log_tree_tab.winfo_exists():
            self.zk_sync_log_tree_tab.heading("timestamp", text=_("zk_log_header_timestamp"))
            self.zk_sync_log_tree_tab.heading("status", text=_("zk_log_header_status"))
            self.zk_sync_log_tree_tab.heading("message", text=_("zk_log_header_details"))
  
    def _create_dashboard_view_widgets(self, parent_frame):
        # This tab is now a placeholder.
        # For consistency, we can add an informational label.
        ttk.Label(parent_frame, text=_("dashboard_info_open_from_sidebar"), font=("Helvetica", 12)).pack(pady=20, padx=10) # Add new key
    def _create_reports_view_widgets(self, parent_frame):
        # This tab is now a placeholder.
        ttk.Label(parent_frame, text=_("reports_info_open_from_sidebar"), font=("Helvetica", 12)).pack(pady=20, padx=10) # Add new key


    def _create_payroll_view_widgets(self, parent_frame):
        # This tab is now a placeholder.
        ttk.Label(parent_frame, text=_("payroll_info_open_from_sidebar"), font=("Helvetica", 12)).pack(pady=20, padx=10) # Add new key


    def _create_alerts_view_widgets(self, parent_frame):
        # This tab is now a placeholder.
        ttk.Label(parent_frame, text=_("alerts_info_open_from_sidebar"), font=("Helvetica", 12)).pack(pady=20, padx=10) # Add new key


    def _create_analytics_view_widgets(self, parent_frame):
        # Analytics UI creation logic remains here.
        title_key = "analytics_placeholder_title"
        title_lbl = ttk.Label(parent_frame, text=_(title_key), font=("Helvetica", 16, "bold"))
        title_lbl.pack(pady=15)
        self._add_translatable_widget(title_lbl, title_key)

        train_btn_key = "analytics_train_attrition_btn"
        train_attrition_btn = ttk.Button(parent_frame, text=_(train_btn_key), 
                                         command=self._gui_train_attrition_model, bootstyle=db_schema.BS_ADD) # Corrected
        train_attrition_btn.pack(pady=10, fill="x", padx=50) # Corrected
        self._add_translatable_widget(train_attrition_btn, train_btn_key)

        # Placeholder for displaying predictions or reports
        self.attrition_predictions_text = tk.Text(parent_frame, height=15, width=80, relief="solid", borderwidth=1)
        self.attrition_predictions_text.pack(pady=10, fill="both", expand=True, padx=20)
        self.attrition_predictions_text.insert(tk.END, "Attrition model status and predictions will appear here...\n")
        self.attrition_predictions_text.config(state="disabled")
    
        # Apply theme to the Text widget using the instance method for palette and global helper for widget
        # This needs to be called when the theme changes as well, or handled by ThemedToplevel if it's a child.
        # For now, apply it once at creation.
        palette = get_theme_palette_global(self.current_theme) # Use global helper
        _theme_text_widget_global(self.attrition_predictions_text, palette)

    def _create_settings_view_widgets(self, parent_frame):
        # This tab is now a placeholder.
        info_label = ttk.Label(parent_frame, text=_("settings_info_open_from_sidebar"), font=("Helvetica", 12), wraplength=350, justify="center")
        info_label.pack(pady=20, padx=10, expand=True)
        self._add_translatable_widget(info_label, "settings_info_open_from_sidebar")


    def _create_interview_scheduling_view_widgets(self, parent_frame):
        """Placeholder for the Interview Scheduling tab content. The main functionality will be in a Toplevel window."""
        lbl_key = "interview_scheduling_placeholder_label"
        lbl = ttk.Label(parent_frame, text=_(lbl_key), font=("Helvetica", 14), wraplength=400, justify="center")
        lbl.pack(pady=20)
        self._add_translatable_widget(lbl, lbl_key)
        btn_key = "interview_scheduling_open_window_btn"
        btn = ttk.Button(parent_frame, text=_(btn_key), command=self.gui_show_interview_scheduling_window, bootstyle=db_schema.BS_VIEW_EDIT) # Corrected
        btn.pack()
        self._add_translatable_widget(btn, btn_key)
    
    def _create_approvals_view_widgets(self, parent_frame):
        """Creates the UI for the Approvals tab."""
        # This tab is now a placeholder.
        info_label = ttk.Label(parent_frame, text=_("approvals_info_open_from_sidebar"), font=("Helvetica", 12), wraplength=350, justify="center")
        info_label.pack(pady=20, padx=10, expand=True)
        self._add_translatable_widget(info_label, "approvals_info_open_from_sidebar")

    def _gui_ap_load_pending_approvals(self):
        for item in self.ap_pending_tree.get_children():
            self.ap_pending_tree.delete(item)
        # self._gui_ap_clear_details_pane() # This method is part of ApprovalsWindow

        if not self.parent_app.current_user_details: return
        current_user_id = self.parent_app.current_user_details.get(db_schema.COL_USER_ID)
        if not current_user_id: return

        try:
            pending_leaves = get_pending_leave_approvals_for_user_db(current_user_id)
            for leave in pending_leaves: # type: ignore
                summary = f"{leave[COL_LR_LEAVE_TYPE]} from {leave[COL_LR_START_DATE]} to {leave[COL_LR_END_DATE]}"
                self.ap_pending_tree.insert("", "end", iid=leave[COL_LR_ID], values=(
                    leave[COL_LR_ID], "Leave Request", leave.get("employee_name", "N/A"),
                    leave[COL_LR_REQUEST_DATE], summary
                ))

            # TODO: Add other types of approvals (e.g., contracts) here
            # Fetch and add pending contract approvals
            pending_contracts = get_pending_contract_approvals_for_user_db(current_user_id)
            for contract in pending_contracts: # type: ignore
                contract_summary = f"Type: {contract[COL_CONTRACT_TYPE]}, Start: {contract[COL_CONTRACT_START_DATE]}"
                self.ap_pending_tree.insert("", "end", iid=contract[COL_CONTRACT_ID], values=(
                    contract[COL_CONTRACT_ID], "Contract Approval", contract.get("employee_name", "N/A"),
                    contract[COL_CONTRACT_CREATED_AT].split("T")[0], # Show only date part of created_at
                    contract_summary
                ))
        except DatabaseOperationError as e:
            messagebox.showerror("Error", f"Could not load pending approvals: {e}", parent=self.root)

    def _gui_ap_on_approval_select(self, event=None):
        selected_item_iid = self.ap_pending_tree.focus()
        item_values = self.ap_pending_tree.item(selected_item_iid, "values") if selected_item_iid else None
        if not selected_item_iid:
            # self._gui_ap_clear_details_pane() # This method is part of ApprovalsWindow
            return

        request_id = int(selected_item_iid)
        # For now, assuming it's a leave request. Need to check item_type if multiple types.
        leave_request = next((lr for lr in get_leave_requests_for_employee_db(self.ap_pending_tree.item(selected_item_iid, "values")[2].split('(')[-1].split(')')[0]) if lr[COL_LR_ID] == request_id), None) # Simplified fetch
        item_type = item_values[1] if item_values else None

        self.ap_details_text.config(state="normal")
        self.ap_details_text.delete("1.0", tk.END)
        if item_type == "Leave Request":
            leave_request = next((lr for lr in get_leave_requests_for_employee_db(item_values[2].split('(')[-1].split(')')[0]) if lr[COL_LR_ID] == request_id), None) # Simplified fetch
            if leave_request:
                details_str = f"Leave Request ID: {leave_request[COL_LR_ID]}\n"
                details_str += f"Employee: {leave_request.get('employee_name', 'N/A')} (ID: {leave_request[COL_LR_EMP_ID]})\n"
                details_str += f"Type: {leave_request[COL_LR_LEAVE_TYPE]}\n"
                details_str += f"Period: {leave_request[COL_LR_START_DATE]} to {leave_request[COL_LR_END_DATE]}\n"
                details_str += f"Reason: {leave_request.get(COL_LR_REASON, 'N/A')}\n"
                details_str += f"Requested On: {leave_request[COL_LR_REQUEST_DATE]}\n"
                self.ap_details_text.insert("1.0", details_str)
        elif item_type == "Contract Approval":
            contract_details = get_contract_details_by_id_db(request_id) # New backend function
            if contract_details:
                details_str = f"Contract ID: {contract_details[COL_CONTRACT_ID]}\n"
                details_str += f"Employee: {contract_details.get('employee_name', 'N/A')} (ID: {contract_details[COL_CONTRACT_EMP_ID]})\n"
                details_str += f"Type: {contract_details[COL_CONTRACT_TYPE]}\n"
                details_str += f"Start Date: {contract_details[COL_CONTRACT_START_DATE]}\n"
                details_str += f"End Date: {contract_details[COL_CONTRACT_CURRENT_END_DATE]}\n"
                details_str += f"Initial Duration: {contract_details.get(COL_CONTRACT_INITIAL_DURATION_YEARS, 'N/A')} years\n"
                details_str += f"Auto-Renewable: {'Yes' if contract_details.get(COL_CONTRACT_IS_AUTO_RENEWABLE) else 'No'}\n"
                if contract_details.get(COL_CONTRACT_IS_AUTO_RENEWABLE):
                    details_str += f"Renewal Term: {contract_details.get(COL_CONTRACT_RENEWAL_TERM_YEARS, 'N/A')} years\n"
                details_str += f"Submitted On: {contract_details[COL_CONTRACT_CREATED_AT].split('T')[0]}\n"
                self.ap_details_text.insert("1.0", details_str)

        self.ap_details_text.config(state="disabled")
        self.ap_approve_btn.config(state="normal")
        self.ap_reject_btn.config(state="normal")

    def _gui_ap_clear_details_pane(self):
        if hasattr(self, 'ap_details_text'): self.ap_details_text.config(state="normal"); self.ap_details_text.delete("1.0", tk.END); self.ap_details_text.config(state="disabled")
        if hasattr(self, 'ap_comments_text'): self.ap_comments_text.delete("1.0", tk.END)
        if hasattr(self, 'ap_approve_btn'): self.ap_approve_btn.config(state="disabled")
        if hasattr(self, 'ap_reject_btn'): self.ap_reject_btn.config(state="disabled")

    def _gui_ap_process_approval(self, new_status: str):
        selected_item_iid = self.ap_pending_tree.focus()
        if not selected_item_iid:
            messagebox.showwarning("Approval Error", "Please select an item to process.", parent=self.root)
            return

        request_id = int(selected_item_iid)
        comments = self.ap_comments_text.get("1.0", tk.END).strip()
        current_user_id = self.parent_app.current_user_details.get(COL_USER_ID)

        if not current_user_id:
            messagebox.showerror("Error", "User session not found. Cannot process approval.", parent=self.root)
            return

        try:
            # For now, only handling leave requests
            update_leave_request_approval_status_db(request_id, new_status, comments, current_user_id)
            messagebox.showinfo("Success", f"Leave request {request_id} has been {new_status.lower()}.", parent=self.root)
            self._gui_ap_load_pending_approvals() # Refresh the list
        except (InvalidInputError, HRException, DatabaseOperationError) as e:
            messagebox.showerror("Approval Error", str(e), parent=self.root)
        # Determine item type from tree (assuming it's stored or can be inferred)
        item_type = self.ap_pending_tree.item(selected_item_iid, "values")[1] # Assuming type is 2nd column

        if item_type == "Leave Request":
            # ... (existing leave approval logic) ...
            pass # Existing logic for leave
        elif item_type == "Contract Approval":
            update_contract_approval_status_db(request_id, new_status, comments, current_user_id)
            messagebox.showinfo("Success", f"Contract {request_id} has been {new_status.lower()}.", parent=self.root)
    
    
    
    def _create_metrics_view_widgets(self, parent_frame):
            # This tab is now a placeholder.
            info_label = ttk.Label(parent_frame, text=_("metrics_info_open_from_sidebar"), font=("Helvetica", 12), wraplength=350, justify="center")
            info_label.pack(pady=20, padx=10, expand=True)
            self._add_translatable_widget(info_label, "metrics_info_open_from_sidebar")
    
        
    def _gui_et_clear_details(self):
        """Clears the selected task details display area."""
        for key, var in self.et_detail_vars.items():
            var.set("N/A")
        for key, widget in self.et_detail_widgets.items():
            if isinstance(widget, tk.Text):
                widget.config(state="normal")
                widget.delete("1.0", tk.END)
                widget.config(state="disabled")

    def _gui_et_on_task_select(self, event=None):
        selected_item_iid = self.et_task_tree.focus()
        if not selected_item_iid:
            self._gui_et_clear_details() # Clear details if nothing is selected
            self.et_edit_task_btn.config(state="disabled")
            self.et_delete_task_btn.config(state="disabled")
            return

        task_id = int(selected_item_iid)
        self.et_edit_task_btn.config(state="normal")
        self.et_delete_task_btn.config(state="normal")

    def _gui_et_load_tasks(self):
        # This method's logic is now in TaskManagementWindow
        pass

    def _gui_et_on_task_select(self, event=None):
        # This method's logic is now in TaskManagementWindow
        pass
    
    def _gui_et_add_task(self):
        # This method's logic is now in TaskManagementWindow
        pass

    def _gui_et_edit_selected_task(self, event=None): # event=None for double-click
        # This method's logic is now in TaskManagementWindow
        pass
    def _gui_et_delete_selected_task(self):
        # This method's logic is now in TaskManagementWindow
        pass
      
    

    def _handle_toplevel_close(self, window_instance: ThemedToplevel, tracker_name: Optional[str]):
        """Handles closing of a Toplevel window managed by the controller."""
        logger.debug(f"Handling close for Toplevel: {window_instance.title()} (Tracker: {tracker_name})")
        if tracker_name and self.active_windows.get(tracker_name) == window_instance:
            self.active_windows.pop(tracker_name, None)
            logger.debug(f"Unregistered {window_instance.title()} from active_windows using tracker: {tracker_name}")
        if hasattr(window_instance, '_cancel_all_after_jobs'): # From ThemedToplevel
            window_instance._cancel_all_after_jobs()
        if window_instance.winfo_exists():
            window_instance.destroy()
    
    def _gui_approve_leave_request(self):
        request_id_str = self.pending_leaves_tree.focus()
        if not request_id_str:
            
            messagebox.showwarning(_("selection_needed_title"), _("no_leave_request_selected_message"), parent=self.root)
            return
        request_id = int(request_id_str)

                # Fetch leave request details to check its type
        try:
            leave_request_details = db_queries.get_leave_request_details_db(request_id)
            if not leave_request_details:
                messagebox.showerror(_("error_title"), _("leave_request_not_found_message", request_id=request_id), parent=self.root)
                return
        except Exception as e:
            logger.error(f"Error fetching leave request details for ID {request_id}: {e}")
            messagebox.showerror(_("db_error_title"), _("error_fetching_leave_details_message"), parent=self.root)
            return

        leave_type = leave_request_details.get(db_schema.COL_LT_NAME)

        # Rule: Only HR Manager can approve Unpaid Leave # type: ignore
        if leave_type == db_schema.LEAVE_TYPE_UNPAID and self.parent_app.get_current_user_role() != db_schema.ROLE_HR_MANAGER:
            messagebox.showerror(_("auth_error_title"), _("unpaid_leave_hr_approval_only_message"), parent=self.root)
            return
        
        employee_id_of_request = leave_request_details.get(db_schema.COL_LR_EMP_ID)
        user_id_performing_action = self.parent_app.get_current_user_id()

        try:
            db_queries.update_leave_request_status_db(request_id, db_schema.STATUS_LEAVE_APPROVED, user_id_performing_action)
            messagebox.showinfo(_("success_title"), _("leave_request_approved_message", request_id=request_id), parent=self.root)
            if employee_id_of_request and user_id_performing_action is not None:
                db_queries.log_employee_action(employee_id_of_request, f"Leave request ID {request_id} approved.", user_id_performing_action)
            self._load_pending_leaves_to_tree()
            self._update_stats_summary()
        except (db_queries.HRException, db_queries.DatabaseOperationError) as e: # Corrected
            messagebox.showerror(_("error_title"), str(e), parent=self.root)

    def _gui_reject_leave_request(self):
        request_id_str = self.pending_leaves_tree.focus()
        if not request_id_str:
            
            messagebox.showwarning(_("selection_needed_title"), _("no_leave_request_selected_message"), parent=self.root)
            return
        request_id = int(request_id_str)

        

        leave_request_details = None # Initialize
        # Fetch leave request details to check its current status
        try:
            leave_request_details = db_queries.get_leave_request_details_db(request_id)
            if not leave_request_details: # Should not happen if selected from tree
                messagebox.showerror(_("error_title"), _("leave_request_not_found_message", request_id=request_id), parent=self.root)
                return
            
            # Rule: Prevent non-HR from rejecting leaves pending HR approval
            if leave_request_details.get(db_schema.COL_LR_STATUS) == db_schema.STATUS_LEAVE_PENDING_HR_APPROVAL and \
               self.parent_app.get_current_user_role() != db_schema.ROLE_HR_MANAGER:
                messagebox.showerror(_("auth_error_title"), _("cannot_reject_pending_hr_approval_message"), parent=self.root)
                return
        except Exception as e:
            logger.error(f"Error fetching leave request details for rejection check (ID {request_id}): {e}")
            # Decide if to proceed or block. For now, let's allow proceeding if details fetch fails.

        employee_id_of_request = None
        if leave_request_details: # Check if details were fetched
            employee_id_of_request = leave_request_details.get(db_schema.COL_LR_EMP_ID)
        
        user_id_performing_action = self.parent_app.get_current_user_id()

        try:
            rejection_reason = simpledialog.askstring(
                _("rejection_reason_dialog_title"),
                _("rejection_reason_prompt"),
                
                parent=self.root
            )
            if rejection_reason is None: # User cancelled the reason dialog
                return

            
            db_queries.update_leave_request_status_db(request_id, db_schema.STATUS_LEAVE_REJECTED, user_id_performing_action, approver_comments=rejection_reason)
            messagebox.showinfo(_("success_title"), _("leave_request_rejected_message", request_id=request_id), parent=self.root)
            if employee_id_of_request and user_id_performing_action is not None:
                db_queries.log_employee_action(employee_id_of_request, f"Leave request ID {request_id} rejected. Reason: {rejection_reason}", user_id_performing_action)
            self._load_pending_leaves_to_tree() # Refresh the list
            self._update_stats_summary() # Update dashboard stats
        except (db_queries.HRException, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(_("error_title"), str(e), parent=self.app_instance.root)
            self._update_stats_summary()
        except (db_queries.HRException, db_queries.DatabaseOperationError) as e: # Corrected
            messagebox.showerror(_("error_title"), str(e), parent=self.root)

    def _gui_cancel_leave_request(self):
        request_id_str = self.pending_leaves_tree.focus()
        if not request_id_str:
            messagebox.showwarning(_("selection_needed_title"), _("no_leave_request_selected_message"), parent=self.root)
            return
        request_id = int(request_id_str)
        # TODO: Add logic to check if the current user is allowed to cancel this request (e.g., only their own, or if admin/manager)
        if messagebox.askyesno(_("confirm_cancel_title"), _("confirm_cancel_leave_message", request_id=request_id), parent=self.root, icon='warning'): # Add keys
            try:
                db_queries.update_leave_request_status_db(request_id, db_schema.STATUS_LEAVE_CANCELLED, self.parent_app.get_current_user_id(), approver_comments="Cancelled by user.") # Add key
                messagebox.showinfo(_("success_title"), _("leave_request_cancelled_message", request_id=request_id), parent=self.root) # Add key
                self._load_pending_leaves_to_tree()
            except (db_queries.HRException, db_queries.DatabaseOperationError) as e:
                messagebox.showerror(_("error_title"), str(e), parent=self.root)