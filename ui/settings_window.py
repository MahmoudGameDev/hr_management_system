# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\settings_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # If used for date settings
import logging
import queue # If GDrive sync uses it
import threading # Added missing import for datetime
from datetime import datetime, timedelta, date as dt_date
from typing import Optional, Dict, Any # Add this import
from ttkbootstrap.tooltip import ToolTip # Added import for ToolTip
# --- Project-specific imports ---
import config # For default config values
from data import database as db_schema # For SETTING_... constants
from data import queries as db_queries # For database operations
from utils.localization import _, LANG_MANAGER # Import _ and LANG_MANAGER directly
from utils import telegram_notifier # Import the new notifier
from utils.cloud_sync import GoogleDriveSync, CREDENTIALS_PATH # If GDrive is managed here
from utils.gui_utils import extract_id_from_combobox_selection, populate_user_combobox # Import gui_utils helpers
from utils.calendar_sync import GoogleCalendarSync # Import for Calendar Sync
from .themed_toplevel import ThemedToplevel
from .components import AutocompleteCombobox # Import AutocompleteCombobox
from utils.exceptions import DatabaseOperationError, InvalidInputError # Import custom exceptions

logger = logging.getLogger(__name__)

class SettingsWindow(ThemedToplevel):
    # Moved method definition before __init__ to ensure availability
    # Override the base class method to ensure consistency and call super()
    def _add_translatable_widget(self, widget, key: str, attr: str = "text", is_title: bool = False, is_menu: bool = False, menu_index: Optional[int] = None, is_notebook_tab: bool = False, tab_id: Optional[Any] = None):
        """Helper to register translatable widgets for SettingsWindow."""
        # Call the base class method to add to the generic list
        super()._add_translatable_widget(widget, key, attr=attr, is_title=is_title, is_menu=is_menu, menu_index=menu_index, is_notebook_tab=is_notebook_tab, tab_id=tab_id)
        # If you needed a separate list *only* for SettingsWindow, you would add here too:
        # self.translatable_widgets_settings.append(...)

    def __init__(self, parent, app_instance):

        super().__init__(parent, app_instance)
        self.title(_("settings_window_title"))
        self.resizable(False, False)
        self.geometry("950x700") # Adjusted size
        self.translatable_widgets_settings = [] # For AppSettingsWindow specific translatable widgets

        self.settings_vars = {} # To store tk.StringVar/BooleanVar for each setting
        self.settings_widgets = {} # To store direct widget references, e.g., for buttons (initialized once)

        self.gcal_sync = GoogleCalendarSync() # Instance for Google Calendar
        # Initialize GoogleDriveSync instance and queue for async operations
        self.gdrive_sync = GoogleDriveSync()
        self.gdrive_auth_queue = queue.Queue() # Queue for GDrive auth thread communication


        # --- Notebook for Tabs ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=(10,0)) # Pad top, no bottom for buttons

        # --- Create Tab Frames ---
        self.tab_general_appearance = self._create_scrollable_tab_frame(self.notebook, "settings_tab_general_appearance")
        self.tab_integrations = self._create_scrollable_tab_frame(self.notebook, "settings_tab_integrations")
        self.tab_data_management = self._create_scrollable_tab_frame(self.notebook, "settings_tab_data_management")
        self.tab_policies_rules = self._create_scrollable_tab_frame(self.notebook, "settings_tab_policies_rules")
        self.tab_calendar_sync = self._create_scrollable_tab_frame(self.notebook, "settings_tab_calendar_integration") # New Tab


        # Define settings layout with group information (group_title, label_text, setting_key, widget_type, options_dict, tooltip_text (optional))
        # Format: (group_title_key, label_text_key, setting_key, widget_type, options_dict, tooltip_text_key (optional))
        settings_layout = [
            # General & Appearance Tab
            ("settings_group_general_appearance", "settings_default_lang_label", db_schema.SETTING_DEFAULT_LANGUAGE, "combobox", {"values": ["en", "ar"], "state": "readonly"}, "settings_default_lang_tooltip", self.tab_general_appearance.scrollable_frame), # type: ignore
            ("settings_group_general_appearance", "settings_default_theme_label", db_schema.SETTING_DEFAULT_THEME, "combobox", {"values": ["light", "dark"], "state": "readonly"}, "settings_default_theme_tooltip", self.tab_general_appearance.scrollable_frame), # type: ignore

            # Integrations & Notifications Tab
            ("settings_group_telegram", "settings_telegram_token_label", db_schema.SETTING_TELEGRAM_BOT_TOKEN, "entry", {"width": 40}, "settings_telegram_token_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_telegram", "settings_telegram_chat_id_label", db_schema.SETTING_TELEGRAM_CHAT_ID, "entry", {"width": 40}, "settings_telegram_chat_id_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_zkteco", "settings_zkteco_ip_label", db_schema.SETTING_ZKTECO_DEVICE_IP, "entry", {"width": 20}, "settings_zkteco_ip_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_zkteco", "settings_zkteco_port_label", db_schema.SETTING_ZKTECO_DEVICE_PORT, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_zkteco_port_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_zkteco", "settings_zkteco_timeout_label", db_schema.SETTING_ZKTECO_TIMEOUT, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_zkteco_timeout_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_auto_reports", "settings_enable_weekly_stats_label", db_schema.SETTING_AUTO_WEEKLY_STATS_ENABLED, "checkbutton", {}, "settings_enable_weekly_stats_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_auto_reports", "settings_report_day_label", db_schema.SETTING_AUTO_WEEKLY_STATS_DAY, "combobox", {"values": db_schema.DAYS_OF_WEEK, "state": "readonly", "width": 15}, "settings_report_day_tooltip", self.tab_integrations.scrollable_frame),
            ("settings_group_auto_reports", "settings_report_time_label", db_schema.SETTING_AUTO_WEEKLY_STATS_TIME, "entry", {"width": 10}, "settings_report_time_tooltip", self.tab_integrations.scrollable_frame),

            # Data Management Tab
             # Cloud Backup Group
            ("settings_group_cloud_backup", "settings_gdrive_status_label", "gdrive_auth_status", "readonly_label", {"text": _("settings_gdrive_status_checking")}, None, self.tab_data_management.scrollable_frame), # type: ignore
            ("settings_group_cloud_backup", "", "gdrive_auth_button", "button", {"text_key": "settings_gdrive_auth_button_text", "command": self._gui_gdrive_authenticate}, "settings_gdrive_auth_button_tooltip", self.tab_data_management.scrollable_frame), # type: ignore
            ("settings_group_cloud_backup", "", "gdrive_backup_now_button", "button", {"text_key": "settings_gdrive_backup_now_button_text", "command": self._gui_gdrive_backup_now, "state": "disabled"}, "settings_gdrive_backup_now_button_tooltip", self.tab_data_management.scrollable_frame), # type: ignore
            # Backup & Recovery Group (Moved Auto Backup here)
            ("settings_group_backup_recovery", "settings_auto_backup_label", db_schema.SETTING_AUTO_BACKUP_ENABLED, "checkbutton", {}, "settings_auto_backup_tooltip", self.tab_data_management.scrollable_frame), # type: ignore
            ("settings_group_backup_recovery", "settings_auto_backup_freq_label", db_schema.SETTING_AUTO_BACKUP_FREQUENCY, "combobox", {"values": ["Daily", "Weekly", "Monthly"], "state": "readonly"}, "settings_auto_backup_freq_tooltip", self.tab_data_management.scrollable_frame), # type: ignore

            # Data Management Group
            ("settings_group_data_management", "settings_archive_cutoff_label", "archive_cutoff_date", "date_entry_button", {"button_text_key": "settings_archive_button_text"}, "settings_archive_cutoff_tooltip", self.tab_data_management.scrollable_frame), # type: ignore
            
            # Policies & Rules Tab
            # Policies & Rules Group
            ("settings_group_work_schedule", "settings_std_work_start_time_label", db_schema.SETTING_STANDARD_START_TIME, "entry", {"width": 10}, "settings_std_work_start_time_tooltip", self.tab_policies_rules.scrollable_frame), # New
            ("settings_group_work_schedule", "settings_std_work_end_time_label", db_schema.SETTING_STANDARD_END_TIME, "entry", {"width": 10}, "settings_std_work_end_time_tooltip", self.tab_policies_rules.scrollable_frame), # New Setting
            ("settings_group_work_schedule", "settings_std_work_hours_label", db_schema.SETTING_STANDARD_WORK_HOURS_PER_DAY, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_std_work_hours_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_work_schedule", "settings_work_days_indices_label", db_schema.SETTING_WORK_DAYS_INDICES, "entry", {"width": 20}, "settings_work_days_indices_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_work_schedule", "settings_std_lunch_break_label", db_schema.SETTING_STANDARD_LUNCH_BREAK_MINUTES, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_std_lunch_break_tooltip", self.tab_policies_rules.scrollable_frame), # New

            ("settings_group_late_arrival", "settings_late_arrival_allowed_minutes_label", db_schema.SETTING_LATE_ARRIVAL_ALLOWED_MINUTES, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_late_arrival_allowed_minutes_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_late_arrival", "settings_late_arrival_penalty_type_label", db_schema.SETTING_LATE_ARRIVAL_PENALTY_TYPE, "combobox", {"values": ["None", "Fixed Amount", "Percentage of Daily Rate"], "state": "readonly", "width": 25}, "settings_late_arrival_penalty_type_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_late_arrival", "settings_late_arrival_penalty_amount_label", db_schema.SETTING_LATE_ARRIVAL_PENALTY_AMOUNT, "entry", {"width": 10, "validate": "key", "validatecommand_type": "numeric"}, "settings_late_arrival_penalty_amount_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_late_arrival", "settings_late_arrival_notification_time_label", db_schema.SETTING_LATE_ARRIVAL_NOTIFICATION_TIME, "entry", {"width": 15}, "settings_late_arrival_notification_time_tooltip", self.tab_policies_rules.scrollable_frame), # Renamed label key

            ("settings_group_absence_policy", "settings_min_unexcused_absence_days_label", db_schema.SETTING_MIN_UNEXCUSED_ABSENCE_DAYS_FOR_ALERT, "entry", {"width":10, "validate":"key", "validatecommand_type":"numeric"}, "settings_min_unexcused_absence_days_tooltip", self.tab_policies_rules.scrollable_frame), # New
            
            ("settings_group_vacation_policies", "settings_default_annual_leave_days_label", db_schema.SETTING_DEFAULT_ANNUAL_LEAVE_DAYS, "entry", {"width":10, "validate":"key", "validatecommand_type":"numeric"}, "settings_default_annual_leave_days_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_vacation_policies", "settings_vacation_accumulation_policy_label", db_schema.SETTING_VACATION_ACCUMULATION_POLICY, "entry", {"width":25}, "settings_vacation_accumulation_policy_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_vacation_policies", "settings_max_vacation_carry_over_label", db_schema.SETTING_MAX_VACATION_CARRY_OVER_DAYS, "entry", {"width":10, "validate":"key", "validatecommand_type":"numeric"}, "settings_max_vacation_carry_over_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_vacation_policies", "settings_vacation_calculation_method_label", db_schema.SETTING_VACATION_CALCULATION_METHOD, "combobox", {"values": ["Fixed Annual Allocation", "Monthly Accrual"], "state":"readonly", "width":25}, "settings_vacation_calculation_method_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_leave_management", "settings_leave_busy_threshold_label", db_schema.SETTING_LEAVE_BUSY_THRESHOLD_PERCENT_DEPT, "spinbox", {"from_": 0, "to": 100, "width": 5}, "settings_leave_busy_threshold_tooltip", self.tab_policies_rules.scrollable_frame), # type: ignore
            ("settings_group_policies_rules", "settings_public_holidays_label", db_schema.SETTING_PUBLIC_HOLIDAYS_LIST, "text", {"height": 3, "width": 40}, "settings_public_holidays_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_policies_rules", "settings_default_leave_approver_label", db_schema.SETTING_DEFAULT_LEAVE_APPROVER_USER_ID, "combobox_user", {"width": 30}, "settings_default_leave_approver_tooltip", self.tab_policies_rules.scrollable_frame),
            ("settings_group_policies_rules", "settings_default_contract_approver_label", db_schema.SETTING_DEFAULT_CONTRACT_APPROVER_USER_ID, "combobox_user", {"width": 30}, "settings_default_contract_approver_tooltip", self.tab_policies_rules.scrollable_frame),
        ]
        # Calendar Sync Tab Layout (New)
        calendar_sync_layout = [
            ("settings_group_google_calendar", "settings_gcal_status_label", "gcal_status_display", "readonly_label", {"text": _("settings_gcal_status_not_connected")}, None, self.tab_calendar_sync.scrollable_frame),
            ("settings_group_google_calendar", "", "gcal_connect_button", "button", {"text_key": "settings_gcal_connect_button_text", "command": self._gui_gcal_connect_disconnect}, None, self.tab_calendar_sync.scrollable_frame),
            ("settings_group_google_calendar", "settings_gcal_sync_interviews_label", db_schema.SETTING_GCAL_SYNC_INTERVIEWS, "checkbutton", {}, "settings_gcal_sync_interviews_tooltip", self.tab_calendar_sync.scrollable_frame), # Add SETTING_GCAL_SYNC_INTERVIEWS to db_schema
            ("settings_group_google_calendar", "settings_gcal_sync_vacations_label", db_schema.SETTING_GCAL_SYNC_VACATIONS, "checkbutton", {}, "settings_gcal_sync_vacations_tooltip", self.tab_calendar_sync.scrollable_frame), # Add SETTING_GCAL_SYNC_VACATIONS to db_schema
        ]
 # Build the settings UI dynamically based on the layout configuration
        current_group_frame = None
        current_group_title = None
        row_in_group = 0

        # Added type hint for the unpacked tuple
        for group_title_key, label_text, key, widget_type, options, *tooltip_args_and_tab_frame in (settings_layout + calendar_sync_layout): # type: ignore
             # group_title and label_text are translation keys
            tooltip_text_key = tooltip_args_and_tab_frame[0] if tooltip_args_and_tab_frame else None
            tooltip_text = _(tooltip_text_key) if tooltip_text_key else None

            target_scrollable_frame = tooltip_args_and_tab_frame[1] # The last element is the target scrollable_frame

            if group_title_key != current_group_title: # Check against the key
                current_group_frame = ttk.LabelFrame(target_scrollable_frame, text=_(group_title_key), padding="10")
                self._add_translatable_widget(current_group_frame, group_title_key, attr="title") # Register LabelFrame title
                current_group_frame.pack(fill="x", pady=10, padx=5)  
                current_group_title = group_title_key
                row_in_group = 0
            # Create and grid the label for the current setting
            if not current_group_frame: # Should not happen if layout is correct
                logger.error("Settings layout error: current_group_frame is None.") # pragma: no cover
                continue

            label_widget = ttk.Label(current_group_frame, text=_(label_text) if label_text else "") # Translate label
            if label_text: self._add_translatable_widget(label_widget, label_text) # Register label for translation

            if tooltip_text:
                ToolTip(label_widget, text=tooltip_text, bootstyle="info") # Tooltip on the label
            
            var = None
            widget = None

            if widget_type == "entry":
                var = tk.StringVar() # Use StringVar for entry
                widget = ttk.Entry(current_group_frame, textvariable=var, width=options.get("width", 25))
                if options.get("validatecommand_type") == "numeric":
                    vcmd = (self.register(self._validate_numeric_input), '%P')
                    widget.config(validate='key', validatecommand=vcmd)
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type}

            elif widget_type == "readonly_label": # Handler for readonly_label
                var = tk.StringVar(value=options.get("text", "")) # Initialize StringVar with default text from options
                widget = ttk.Label(current_group_frame, textvariable=var, width=options.get("width", 40)) # Use textvariable
                # No need to store widget in self.settings_widgets unless specifically needed for other direct manipulation
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type}

            elif widget_type == "combobox":
                var = tk.StringVar()
                widget = ttk.Combobox(current_group_frame, textvariable=var, values=options.get("values", []), state=options.get("state", "normal"), width=options.get("width", 23))
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type} # Store var

            elif widget_type == "combobox_user": # Custom type for user selection combobox
                var = tk.StringVar()
                widget = AutocompleteCombobox(current_group_frame, textvariable=var, width=options.get("width", 30))
                self._populate_user_combobox(widget) # Populate with users
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type}

            elif widget_type == "checkbutton":
                var = tk.BooleanVar()
                widget = ttk.Checkbutton(current_group_frame, variable=var)
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type}

            elif widget_type == "spinbox":
                var = tk.StringVar() # Spinbox uses StringVar
                widget = ttk.Spinbox(current_group_frame, from_=options.get("from_"), to=options.get("to"), textvariable=var, width=options.get("width", 5), wrap=False)
                self.settings_vars[key] = {"var": var, "widget": widget, "type": widget_type}

            elif widget_type == "button": # pragma: no cover
                button_text_key = options.get("text_key", "")
                button_text_val = _(button_text_key) if button_text_key else options.get("text", "Button")
                
                widget = ttk.Button(current_group_frame, text=button_text_val, command=options.get("command"))
                if "state" in options:
                    widget.config(state=options["state"]) # pragma: no cover
                # Store button reference directly for state changes
                self.settings_widgets[key] = widget
                self.settings_vars[key] = {"widget": widget, "type": widget_type} # Store type and widget

            elif widget_type == "text": # pragma: no cover
                # Text widget doesn't use a StringVar directly for its main content
                widget = tk.Text(current_group_frame, height=options.get("height", 3), width=options.get("width", 30), relief="solid", borderwidth=1)
                self.settings_vars[key] = {"widget": widget, "type": widget_type} # Store type and widget

            elif widget_type == "date_entry_button": # Custom type for date entry + button
                date_button_frame = ttk.Frame(current_group_frame) # Create a frame to hold the DateEntry and Button
                date_entry_widget = DateEntry(date_button_frame, width=12, dateformat='%Y-%m-%d')
                date_entry_widget.pack(side="left", padx=(0, 5))
                date_entry_widget.date = dt_date.today() - timedelta(days=365) # Set default on date_entry_widget # Ensure dt_date is imported
                button_text_val = _(options.get("button_text_key")) if options.get("button_text_key") else options.get("button_text", "Execute")
                archive_btn = ttk.Button(date_button_frame, text=button_text_val,
                                         command=lambda k=key, w=date_entry_widget: self._handle_data_management_action(k, w.entry.get())) # Pass key and DateEntry widget
                archive_btn.pack(side="left")
                
            # Grid the label and the main widget (or its container)
            label_widget.grid(row=row_in_group, column=0, sticky="w", padx=5, pady=5)
            if widget: # Ensure widget was created and is not the date_entry_button frame
                 widget.grid(row=row_in_group, column=1, sticky="ew", padx=5, pady=5)

            # Increment row counter for the next item in this group
            row_in_group += 1
        # Add tooltip to the main widget if specified and not already added to label
            if tooltip_text and widget and widget_type not in ["checkbutton", "text", "button", "date_entry_button", "combobox_user"]: # Avoid double tooltips or applying to containers/text
                 ToolTip(widget, text=tooltip_text, bootstyle="info") # pragma: no cover

        # --- Action Buttons --- (These are outside the scrollable frame, at the bottom of the Toplevel)
        buttons_frame = ttk.Frame(self) # Parent should be self
        buttons_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.save_settings_btn = ttk.Button(buttons_frame, text=_("settings_button_save"), command=self._save_settings, bootstyle=db_schema.BS_ADD)
        self.save_settings_btn.pack(side="right", padx=5); self._add_translatable_widget(self.save_settings_btn, "settings_button_save")
        self.cancel_btn = ttk.Button(buttons_frame, text=_("settings_button_close"), command=self.destroy, bootstyle=db_schema.BS_LIGHT)
        self.cancel_btn.pack(side="right", padx=5); self._add_translatable_widget(self.cancel_btn, "settings_button_close")

        self.update_idletasks()
        self._load_settings()
        self._check_initial_gdrive_status() # Check GDrive status on open
        self._update_gcal_status_ui() # Check GCal status on open
    
    def _populate_user_combobox(self, combo_widget):
        """Populates the given user combobox with users from the database."""
        try:
            # Use the utility function from gui_utils
            populate_user_combobox(combo_widget, db_queries.get_all_users_db, empty_option_text=_("user_no_linked_employee_option"))
        except Exception as e:
            logger.error(f"Error populating user combobox in settings: {e}")
            messagebox.showerror(_("db_error_title"), _("user_admin_load_users_error", error=e), parent=self)

    def _create_scrollable_tab_frame(self, notebook: ttk.Notebook, tab_title_key: str) -> ttk.Frame:
        """Creates a new tab with a scrollable frame inside it."""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text=_(tab_title_key))
        self._add_translatable_widget(notebook, tab_title_key, attr="tab", tab_id=tab_frame)

        canvas = tk.Canvas(tab_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_inner_frame = ttk.Frame(canvas, padding="10")

        scrollable_inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tab_frame.scrollable_frame = scrollable_inner_frame # Attach for easy access
        return tab_frame
    
    def _validate_numeric_input(self, P):
        """Validates that the input P is numeric or empty."""
        return P.isdigit() or P == ""

    def _load_settings(self):
        for key, item_dict in self.settings_vars.items():
            # Safely get 'var', it might not exist for all widget types (e.g., date_entry_button, button)
            # Also skip button types and date_entry_button as they don't load a setting value into a simple var
            var = item_dict.get("var") 
            widget = item_dict["widget"]
            widget_type = item_dict["type"]
            
            db_value = db_schema.get_app_setting_db(key) # Corrected: Use db_schema
            if db_value is None: # If setting not in DB, try from config.py (for initial setup)
                # This part needs careful mapping from SETTING_KEY to config.VARIABLE_NAME
                # For simplicity, we assume defaults are handled by get_app_setting_db or are in DB.
                db_value = "" # Default to empty if not found

            if widget_type == "checkbutton" and isinstance(var, tk.BooleanVar):
                var.set(db_value.lower() == "true" if db_value else False)
            elif widget_type == "text" and isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", db_value if db_value else "")
            elif widget_type == "button":
                continue # Buttons don't load setting values
            elif widget_type == "date_entry_button": # pragma: no cover
                pass # Handled by _handle_data_management_action
            elif widget_type == "combobox_user":
                # For user combobox, load the value but also set the display text
                if var and db_value:
                # There's no separate setting value to load into it; its default is set at creation.
                    pass # No value to load for this control itself, it's an action trigger
            elif var: # For Entry, Combobox, Spinbox
                var.set(db_value if db_value else "")

    def _save_settings(self):
        restart_required_settings = [db_schema.SETTING_DEFAULT_LANGUAGE] # Add other keys if they need restart
        theme_changed = False # Initialize theme_changed
        language_changed = False
        original_lang = LANG_MANAGER.current_lang

        try:
            for key, item_dict in self.settings_vars.items():
                widget = item_dict["widget"]
                widget_type = item_dict["type"]
                var = item_dict.get("var") # Safely get 'var', it might be None
                new_value = ""

                if widget_type == "checkbutton":
                    if isinstance(var, tk.BooleanVar):
                        new_value = "true" if var.get() else "false"
                    else:
                        logger.warning(f"Misconfigured checkbutton for setting '{key}', var is not BooleanVar.")
                        continue
                elif widget_type == "text":
                    if isinstance(widget, tk.Text):
                        new_value = widget.get("1.0", tk.END).strip()
                    else:
                        logger.warning(f"Misconfigured text setting '{key}', widget is not tk.Text.")
                        continue
                elif widget_type in ["entry", "combobox", "spinbox"]:
                    if var and hasattr(var, 'get'):
                        if widget_type == "spinbox":
                            # Validate spinbox value as integer
                            try: new_value = str(int(var.get())) # Ensure it's a valid integer string
                            except ValueError: # pragma: no cover # Corrected
                                messagebox.showerror(_("input_error_title"), _("invalid_integer_format_error", field=key), parent=self); return
                        # For combobox_user, extract the ID

                        new_value = var.get()
                    else:
                        logger.warning(f"Misconfigured setting '{key}' of type '{widget_type}', var is missing or invalid.")
                        continue
                elif widget_type == "combobox_user":
                    if var and hasattr(var, 'get'):
                        new_value = extract_id_from_combobox_selection(var.get()) # Extract ID
                        if new_value is None and var.get().strip() != _("user_no_linked_employee_option"): # If text is not empty option but no ID found
                            logger.warning(f"Could not extract ID for combobox_user setting '{key}'. Value: '{var.get()}'. Skipping save for this key.")
                            continue
                elif widget_type in ["button", "date_entry_button", "readonly_label"]:
                    # These types don't have values to save in this loop, or are display-only
                    continue
                else:
                    logger.warning(f"Unhandled widget type '{widget_type}' for setting '{key}' during save.")
                    continue

                # Validate port if it's the ZKTeco port setting
                if key == db_schema.SETTING_ZKTECO_DEVICE_PORT:
                    if not new_value.isdigit() or not (0 < int(new_value) < 65536): # pragma: no cover
                        messagebox.showerror(_("input_error_title"), _("invalid_zkteco_port_number_error", port=new_value), parent=self)
                        return

                current_db_value = db_schema.get_app_setting_db(key) # Corrected: Use db_schema
                if new_value != current_db_value: # Corrected: Use db_schema
                    db_schema.set_app_setting_db(key, new_value)
                    # If any of the weekly stats settings changed, reschedule
                    if key in [db_schema.SETTING_AUTO_WEEKLY_STATS_ENABLED,
                               db_schema.SETTING_AUTO_WEEKLY_STATS_DAY,
                               db_schema.SETTING_AUTO_WEEKLY_STATS_TIME] and self.parent_app:
                        self.parent_app.reschedule_weekly_stats()

                    if key == db_schema.SETTING_DEFAULT_THEME:
                        theme_changed = True
                    if key == db_schema.SETTING_DEFAULT_LANGUAGE:
                        language_changed = True
            
            messagebox.showinfo(_("settings_saved_title"), _("settings_saved_success_message"), parent=self)

            if theme_changed and self.parent_app and hasattr(self.parent_app, 'hr_app_gui') and self.parent_app.hr_app_gui: # Corrected: Use db_schema
                new_theme = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_THEME, "light")
                self.parent_app.hr_app_gui.current_theme = new_theme # type: ignore
                self.parent_app.hr_app_gui.apply_instance_theme(self.parent_app.hr_app_gui.style) # type: ignore
                self.update_local_theme_elements() # Update self
            # Corrected: Use db_schema
            if language_changed and self.parent_app and hasattr(self.parent_app, 'hr_app_gui') and self.parent_app.hr_app_gui: # Corrected: Use db_schema
                new_lang = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_LANGUAGE, "en")
                if LANG_MANAGER.set_language(new_lang):
                    self.parent_app.hr_app_gui.refresh_ui_for_language() # type: ignore
                    # Update this window's UI elements if it has translatable text
                    self.refresh_ui_for_language() 
                if new_lang != original_lang: # If language actually changed
                     messagebox.showinfo(_("language_change_title"), _("language_change_restart_info_message"), parent=self)

            # Inform about restart for certain settings
            # This logic can be expanded if more settings require restart.
            # For now, language change is the main one.

        except db_schema.DatabaseOperationError as e: # Corrected: Use db_schema
            messagebox.showerror(_("save_error_title"), _("failed_to_save_settings_error", error=e), parent=self)
        except Exception as e_save:
            logger.error(f"Unexpected error saving settings: {e_save}")
            messagebox.showerror("Save Error", f"An unexpected error occurred: {e_save}", parent=self) # pragma: no cover
    def _handle_data_management_action(self, action_key: str, value: Optional[str]):
        if action_key == "archive_cutoff_date":
            if not value:
                messagebox.showerror(_("input_error_title"), _("select_cutoff_date_archiving_error"), parent=self)
                return
            if messagebox.askyesno(_("confirm_archival_title"),
                                   _("confirm_archive_employees_message", date=value),
                                   parent=self, icon='warning'):
                try:
                    archived_count = db_queries.archive_terminated_employees_db(value) # Pass the date string
                    messagebox.showinfo(_("archival_complete_title"), _("employees_archived_success_message", count=archived_count), parent=self)
                    # Optionally, refresh main employee list if it's visible and affected
                    if self.parent_app and hasattr(self.parent_app, 'hr_app_gui'):
                        self.parent_app.hr_app_gui.gui_show_all_employees() # type: ignore
                except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
                    messagebox.showerror(_("archival_error_title"), str(e), parent=self)
    def _gui_gdrive_authenticate(self):
        """Starts the Google Drive authentication process in a thread."""
        try:
            users = db_queries.list_all_users_db() # Use db_queries alias
            user_display_list = [f"{user[COL_USER_USERNAME]} (ID: {user[COL_USER_ID]})" for user in users]
            # Find all combobox_user widgets and update their values
            for key, item_dict in self.settings_vars.items():
                if item_dict["type"] == "combobox_user" and hasattr(item_dict["widget"], 'set_completion_list'):
                    item_dict["widget"].set_completion_list([""] + user_display_list) # Allow empty selection
        except Exception as e:
            logger.error(f"Error populating user comboboxes in settings: {e}")

        if not self.parent_app.active_operation_lock.acquire(blocking=False):
            messagebox.showwarning("Operation in Progress", "Another operation is currently running. Please wait.", parent=self)
            return

        auth_button = self.settings_widgets.get("gdrive_auth_button")
        backup_button = self.settings_widgets.get("gdrive_backup_now_button")
        status_label_item = self.settings_vars.get("gdrive_auth_status")

        if not auth_button or not backup_button or not status_label_item or not status_label_item.get("var"):
            logger.error("Google Drive settings widgets not found.")
            self.parent_app.active_operation_lock.release()
            return # pragma: no cover

        auth_button.config(state="disabled")
        backup_button.config(state="disabled")
        status_label_item["var"].set(_("gdrive_authenticating_status"))
        self.config(cursor="watch")

        # Run authentication in a thread
        thread = threading.Thread(target=self._perform_gdrive_auth_threaded, args=(self.gdrive_auth_queue,)) # Pass the queue
        thread.daemon = True
        thread.start()

        # Start polling the queue for results
        self._check_gdrive_auth_status()

    def _perform_gdrive_auth_threaded(self, q_comm: queue.Queue):
        """Worker function for Google Drive authentication."""
        try:
            # The authenticate method handles loading/refreshing/running the flow
            success = self.gdrive_sync.authenticate()
            q_comm.put({"type": "auth_result", "success": success})
        except FileNotFoundError:
              q_comm.put({"type": "auth_error", "message": _("gdrive_credentials_not_found_error", path=CREDENTIALS_PATH)})
        except ConnectionError as ce:
             q_comm.put({"type": "auth_error", "message": _("gdrive_auth_failed_network_error", error=ce)})
        except Exception as e: # pragma: no cover
            logger.error(f"Unexpected error during Google Drive authentication: {e}", exc_info=True)
            q_comm.put({"type": "auth_error", "message": f"An unexpected error occurred: {e}"})

    def _check_gdrive_auth_status(self):
        """Checks the queue for Google Drive auth results."""
        try:
            result = self.gdrive_auth_queue.get_nowait()
            
            auth_button = self.settings_widgets.get("gdrive_auth_button")
            backup_button = self.settings_widgets.get("gdrive_backup_now_button")
            status_label_item = self.settings_vars.get("gdrive_auth_status")
            status_var = status_label_item.get("var") if status_label_item else None

            self.config(cursor="")
            self.parent_app.active_operation_lock.release()

            if result.get("type") == "auth_result":
                if result["success"]:
                    status_var.set(_("gdrive_status_authenticated"))
                    auth_button.config(state="disabled") # Disable auth button once authenticated
                    backup_button.config(state="normal") # Enable backup button
                    messagebox.showinfo(_("google_drive_title"), _("gdrive_auth_success_message"), parent=self)
                else:
                    status_var.set(_("gdrive_status_auth_failed"))
                    auth_button.config(state="normal") # Re-enable auth button
                    backup_button.config(state="disabled")
                    messagebox.showerror(_("google_drive_auth_error_title"), _("gdrive_auth_failed_check_logs_message"), parent=self)
            elif result.get("type") == "auth_error":
                 status_var.set(_("gdrive_status_auth_error"))
                 auth_button.config(state="normal") # Re-enable auth button
                 backup_button.config(state="disabled")
                 messagebox.showerror(_("google_drive_auth_error_title"), result["message"], parent=self)

        except queue.Empty:
            # Keep polling until result is available
            self.after(200, self._check_gdrive_auth_status)
        except Exception as e: # pragma: no cover
            logger.error(f"Error in _check_gdrive_auth_status: {e}", exc_info=True)
            status_label_item = self.settings_vars.get("gdrive_auth_status")
            if status_label_item and status_label_item.get("var"):
                 status_label_item["var"].set("Error checking status.")
            auth_button = self.settings_widgets.get("gdrive_auth_button")
            backup_button = self.settings_widgets.get("gdrive_backup_now_button")
            if auth_button: auth_button.config(state="normal")
            if backup_button: backup_button.config(state="disabled")
            self.config(cursor="")
            self.parent_app.active_operation_lock.release()

    def _gui_gdrive_backup_now(self):
        """Placeholder for triggering backup and upload."""
        messagebox.showinfo(_("google_drive_backup_title"), _("gdrive_backup_not_implemented_message"), parent=self)
        # TODO: Implement actual backup creation and call self.gdrive_sync.upload_file in a thread

    # Add a method to check initial auth status when window opens
    def _check_initial_gdrive_status(self):
        """Checks if already authenticated and updates UI on window open."""
        auth_button = self.settings_widgets.get("gdrive_auth_button")
        backup_button = self.settings_widgets.get("gdrive_backup_now_button")
        status_label_item = self.settings_vars.get("gdrive_auth_status")
        status_var = status_label_item.get("var") if status_label_item else None # type: ignore

        if auth_button and backup_button and status_var:
            if self.gdrive_sync.is_authenticated():
                status_var.set(_("gdrive_status_authenticated"))
                auth_button.config(state="disabled")
                backup_button.config(state="normal")
            else:
                status_var.set(_("gdrive_status_not_authenticated"))
                auth_button.config(state="normal")
                backup_button.config(state="disabled")

    # --- Google Calendar Sync Methods ---
    def _update_gcal_status_ui(self):
        """Updates the Google Calendar status label and connect/disconnect button."""
        connect_button = self.settings_widgets.get("gcal_connect_button")
        status_label_item = self.settings_vars.get("gcal_status_display")
        status_var = status_label_item.get("var") if status_label_item else None

        if not connect_button or not status_var:
            logger.warning("Google Calendar UI elements not found for status update.")
            return

        if self.gcal_sync.is_authenticated():
            email = self.gcal_sync.get_user_email()
            status_var.set(_("settings_gcal_status_connected_as", email=email if email else "Unknown User"))
            connect_button.config(text=_("settings_gcal_disconnect_button_text"))
        else:
            status_var.set(_("settings_gcal_status_not_connected"))
            connect_button.config(text=_("settings_gcal_connect_button_text"))

    def _gui_gcal_connect_disconnect(self):
        """Handles connect/disconnect for Google Calendar."""
        if self.gcal_sync.is_authenticated():
            # Disconnect
            self.gcal_sync.disconnect()
            self._update_gcal_status_ui()
            messagebox.showinfo(_("google_calendar_title"), _("settings_gcal_disconnected_message"), parent=self)
        else:
            # Connect (Authenticate)
            status_label_item = self.settings_vars.get("gcal_status_display")
            status_var = status_label_item.get("var") if status_label_item else None
            if status_var: status_var.set(_("settings_gcal_status_authenticating"))
            self.config(cursor="watch")
            
            # Run authentication in a thread to avoid freezing UI
            auth_thread = threading.Thread(target=self._perform_gcal_auth_threaded, daemon=True)
            auth_thread.start()

    def _perform_gcal_auth_threaded(self):
        """Worker function for Google Calendar authentication."""
        try:
            success = self.gcal_sync.authenticate()
            if success:
                email = self.gcal_sync.get_user_email()
                self.after(0, lambda: messagebox.showinfo(_("google_calendar_title"), _("settings_gcal_auth_success_message", email=email if email else ""), parent=self))
            else:
                self.after(0, lambda: messagebox.showerror(_("google_calendar_auth_error_title"), _("settings_gcal_auth_failed_message", error="Authentication flow did not complete."), parent=self))
        except FileNotFoundError as fnf: # Catch specific error for missing credentials.json
            self.after(0, lambda: messagebox.showerror(_("google_calendar_auth_error_title"), str(fnf), parent=self))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(_("google_calendar_auth_error_title"), _("settings_gcal_auth_failed_message", error=str(e)), parent=self))
        finally:
            self.after(0, self._update_gcal_status_ui)
            self.after(0, lambda: self.config(cursor=""))

    def refresh_ui_for_language(self): # pragma: no cover
        """Refreshes translatable UI elements in the SettingsWindow."""
        # Call the base class refresh method first
        super().refresh_ui_for_language()
        # Add any SettingsWindow specific refresh logic here if needed
        # (e.g., updating combobox values that are translated strings)
        for item_info in self.translatable_widgets_settings: # This list is now empty if _add_translatable_widget calls super
            widget = item_info["widget"]
            key = item_info["key"]
            if widget.winfo_exists():
                try:
                    if attr == "tab" and isinstance(widget, ttk.Notebook):
                        tab_id = item_info.get("tab_id")
                        if tab_id:
                            widget.tab(tab_id, text=_(key))
                    elif attr == "text":
                        widget.config(text=_(key))
                    elif attr == "title": # For LabelFrames, though now handled by 'text' in _add_translatable_widget
                        widget.config(text=_(key))
                except tk.TclError: pass # Widget might not support the attribute
        self._update_gcal_status_ui() # Refresh GCal status text as it might contain translated parts
                
    def _gui_send_test_telegram_notification(self):
        """Sends a test notification to the configured Telegram chat."""
        # Token and Chat ID will be read from DB by the send_telegram_notification function
        test_message = f"🔔 This is a test notification from the HR Management System.\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if telegram_notifier.send_telegram_notification(test_message): # Use the notifier # Corrected
            messagebox.showinfo(_("telegram_test_success_title"), _("telegram_test_success_message"), parent=self)

        # Optionally increment a counter for test notifications
        else:
            messagebox.showerror(_("telegram_test_failed_title"), _("telegram_test_failed_message"), parent=self)

    def upload_file(self, local_filepath: str, drive_folder_name: str = "HRAppBackups") -> Optional[str]:
        
        """Uploads a file to a specific folder in Google Drive.""" # This method is part of GoogleDriveSync class
        if not self.is_authenticated():
            logger.error("Not authenticated with Google Drive. Please authenticate first.")
            # In a GUI, you might trigger the auth flow here or prompt the user.
