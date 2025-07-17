# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\attendance_log_viewer_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
from typing import Optional, List, Dict, Any # Added List, Dict, Any
import logging
from datetime import datetime, date as dt_date, timedelta

# --- Project-specific imports ---
from data import database as db_schema # For COL_ATT_... constants
from data import queries as db_queries # For get_attendance_logs_for_employee_period, list_all_employees
from utils import localization
from utils.localization import _ # Import _ directly
from utils.exceptions import EmployeeNotFoundError, DatabaseOperationError # Import custom exceptions
from utils.gui_utils import extract_id_from_combobox_selection, populate_employee_combobox
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class AttendanceLogViewerWindow(ThemedToplevel):
    TRACKER_NAME = "active_attendance_log_viewer_window" # Define tracker name

    def __init__(self, parent, app_instance, default_emp_id: Optional[str] = None, view_mode: Optional[str] = None, manager_id: Optional[str] = None):
        # Corrected super call to match ThemedToplevel's expected signature
        super().__init__(parent, app_instance)
        self.default_emp_id = default_emp_id
        self.view_mode = view_mode # e.g., "manager_team"
        self.manager_id = manager_id # For manager_team view
        self.translatable_widgets_att_log = [] # For this window's translatable widgets
        self.selected_employee_id: Optional[str] = None # To store the currently selected employee ID
        self.employee_combobox_map: Dict[str, str] = {} # To map display names to emp_ids

        self.title(localization._("attendance_log_viewer_title_key")) # Set title after super()
        self.geometry("950x650") # Adjusted size

        self._create_filter_frame()
        self._create_log_display_frame()
        self._create_summary_frame()

        self._populate_employee_combobox() # Call after all widgets are created
        self.refresh_ui_for_language() # Initial translation

    def _add_translatable_widget(self, widget, key, attr="text"):
        """Helper to register translatable widgets for this window."""
        self.translatable_widgets_att_log.append({"widget": widget, "key": key, "attr": attr})

    def _create_filter_frame(self):
        filter_lf_key = "attendance_log_filter_frame_title"
        self.filter_frame = ttk.LabelFrame(self, text=_(filter_lf_key), padding="10")
        self.filter_frame.pack(side="top", fill="x", padx=10, pady=5)
        self._add_translatable_widget(self.filter_frame, filter_lf_key, attr="title")

        # Employee Selection
        emp_lbl_key = "employee_label_key" # Reusing key
        self.employee_label = ttk.Label(self.filter_frame, text=_(emp_lbl_key))
        self.employee_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget(self.employee_label, emp_lbl_key)

        self.employee_combobox = ttk.Combobox(self.filter_frame, state="readonly", width=30, style="Custom.TCombobox")
        self.employee_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.employee_combobox.bind("<<ComboboxSelected>>", self._on_employee_selected)

        # Date Range
        from_date_lbl_key = "from_date_label_key" # Reusing key
        self.from_date_label = ttk.Label(self.filter_frame, text=_(from_date_lbl_key))
        self.from_date_label.grid(row=0, column=2, sticky="w", padx=(10, 5), pady=5)
        self._add_translatable_widget(self.from_date_label, from_date_lbl_key)

        self.start_date_entry = DateEntry(self.filter_frame, width=12, dateformat='%Y-%m-%d')
        self.start_date_entry.date = dt_date.today().replace(day=1) # Default to start of month
        self.start_date_entry.grid(row=0, column=3, padx=5, pady=5)

        to_date_lbl_key = "to_date_label_key" # Reusing key
        self.to_date_label = ttk.Label(self.filter_frame, text=_(to_date_lbl_key))
        self.to_date_label.grid(row=0, column=4, sticky="w", padx=(10, 5), pady=5)
        self._add_translatable_widget(self.to_date_label, to_date_lbl_key)

        self.end_date_entry = DateEntry(self.filter_frame, width=12, dateformat='%Y-%m-%d')
        self.end_date_entry.date = dt_date.today() # Default to today
        self.end_date_entry.grid(row=0, column=5, padx=5, pady=5)

        # Load Button
        load_btn_key = "attendance_log_load_button"
        self.load_button = ttk.Button(self.filter_frame, text=_(load_btn_key), command=self._load_attendance_logs, bootstyle=db_schema.BS_PRIMARY_ACTION)
        self.load_button.grid(row=0, column=6, padx=10, pady=5)
        self._add_translatable_widget(self.load_button, load_btn_key)

        self.filter_frame.columnconfigure(1, weight=1) # Allow employee combobox to expand

    def _create_log_display_frame(self):
        log_display_lf_key = "attendance_log_records_frame_title"
        log_display_frame = ttk.LabelFrame(self, text=_(log_display_lf_key), padding="10")
        log_display_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self._add_translatable_widget(log_display_frame, log_display_lf_key, attr="title")

        self.log_tree_columns_config = {
            "date": {"header_key": "attendance_log_header_date", "width": 100, "anchor": "w"},
            "clock_in": {"header_key": "attendance_log_header_clock_in", "width": 150, "anchor": "center"},
            "clock_out": {"header_key": "attendance_log_header_clock_out", "width": 150, "anchor": "center"},
            "duration": {"header_key": "attendance_log_header_duration", "width": 120, "anchor": "e"}
        }
        self.log_tree = ttk.Treeview(log_display_frame, columns=list(self.log_tree_columns_config.keys()), show="headings")
        self._update_log_tree_headers() # Set initial headers

        self.log_tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_display_frame, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _create_summary_frame(self):
        summary_frame = ttk.Frame(self, padding="10")
        summary_frame.pack(side="bottom", fill="x", pady=5)

        self.total_hours_var = tk.StringVar(value=_("attendance_log_total_hours_default")) # Add key
        self.total_hours_label = ttk.Label(summary_frame, textvariable=self.total_hours_var)
        self.total_hours_label.pack(side="left", padx=10)
        # No need to add to translatable_widgets if text is dynamic via var

        self.total_days_var = tk.StringVar(value=_("attendance_log_total_days_default")) # Add key
        self.total_days_label = ttk.Label(summary_frame, textvariable=self.total_days_var)
        self.total_days_label.pack(side="left", padx=10)


        # --- Controls Frame ---
        controls_frame = ttk.Frame(self, padding="10")
        controls_frame.pack(side="top", fill="x", pady=5)

        ttk.Label(controls_frame, text="Employee:").pack(side="left", padx=(0, 5))
        self.employee_var = tk.StringVar()
        self.employee_combo = ttk.Combobox(controls_frame, textvariable=self.employee_var, state="readonly", width=30)
        self.employee_combo.pack(side="left", padx=5)

        ttk.Label(controls_frame, text="Start Date (YYYY-MM-DD):").pack(side="left", padx=(10, 5))
        # self.start_date_var = tk.StringVar(value=dt_date.today().replace(day=1).isoformat()) # DateEntry manages its own var
        self.start_date_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.start_date_entry.date = dt_date.today().replace(day=1) # Default to start of month
        self.start_date_entry.pack(side="left", padx=5)

        ttk.Label(controls_frame, text="End Date (YYYY-MM-DD):").pack(side="left", padx=(10, 5))
        self.end_date_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.end_date_entry.date = dt_date.today() # Default to today
        self.end_date_entry.pack(side="left", padx=5)

        self.view_log_btn = ttk.Button(controls_frame, text="View Log", command=self._load_attendance_logs, bootstyle=db_schema.BS_VIEW_EDIT)
        self.view_log_btn.pack(side="left", padx=10)

        # --- Log Display Frame ---
        log_display_frame = ttk.LabelFrame(self, text="Attendance Records", padding="10")
        log_display_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_tree_columns = ("date", "clock_in", "clock_out", "duration")
        self.log_tree = ttk.Treeview(log_display_frame, columns=self.log_tree_columns, show="headings")
        self.log_tree.heading("date", text="Date")
        self.log_tree.heading("clock_in", text="Clock In Time")
        self.log_tree.heading("clock_out", text="Clock Out Time")
        self.log_tree.heading("duration", text="Duration (Hours)")

        self.log_tree.column("date", anchor="w", width=100)
        self.log_tree.column("clock_in", anchor="center", width=150)
        self.log_tree.column("clock_out", anchor="center", width=150)
        self.log_tree.column("duration", anchor="e", width=120)
        self.log_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_display_frame, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Summary Frame ---
        summary_frame = ttk.Frame(self, padding="10")
        summary_frame.pack(side="bottom", fill="x", pady=5)
        self.total_hours_var = tk.StringVar(value="Total Hours Worked: N/A")
        ttk.Label(summary_frame, textvariable=self.total_hours_var).pack(side="left", padx=10)
        self.total_days_var = tk.StringVar(value="Total Days Present: N/A")
        ttk.Label(summary_frame, textvariable=self.total_days_var).pack(side="left", padx=10)

    def _update_log_tree_headers(self):
        """Updates the headers of the log treeview based on current language."""
        if hasattr(self, 'log_tree') and self.log_tree.winfo_exists():
            for col_id, config_dict in self.log_tree_columns_config.items():
                header_text = _(config_dict["header_key"])
                self.log_tree.heading(col_id, text=header_text, anchor=config_dict.get("anchor", "w"))
                self.log_tree.column(col_id, width=config_dict.get("width", 100), anchor=config_dict.get("anchor", "w"), stretch=config_dict.get("stretch", tk.NO))

    def refresh_ui_for_language(self): # pragma: no cover
        super().refresh_ui_for_language() # Call parent's method
        self.title(_("attendance_log_viewer_title_key"))
        self._update_log_tree_headers()

        for item_info in self.translatable_widgets_att_log:
            widget = item_info["widget"]
            key = item_info["key"]
            attr = item_info.get("attr", "text")
            if widget.winfo_exists():
                try:
                    if attr == "text": widget.config(text=_(key))
                    elif attr == "title": widget.config(text=_(key)) # For LabelFrames
                except tk.TclError: pass
        
        # Update summary label default texts if they are based on keys
        self.total_hours_var.set(_("attendance_log_total_hours_default"))
        self.total_days_var.set(_("attendance_log_total_days_default"))

        # Repopulate employee combobox if its "All" or default option is translatable
        # This might require storing the current selection and trying to reapply it.
        # For simplicity, we might just repopulate and let it default.
        self._populate_employee_combobox()

    def _populate_employee_dropdown(self):
        populate_employee_combobox(self.employee_combo, db_queries.get_all_employees_db, default_to_first=True)
        if self.employee_var.get(): # If an employee is selected by the utility
            self._load_attendance_log() # Load log for default selection


    def _populate_employee_combobox(self):
        try:
            self.employee_combobox_map.clear() # Clear map before repopulating
            if self.default_emp_id:
                employee = db_queries.get_employee_by_id_db(self.default_emp_id)
                if employee:
                    display_name = f"{employee[db_schema.COL_EMP_NAME]} ({employee[db_schema.COL_EMP_ID]})"
                    self.employee_combobox['values'] = [display_name]
                    self.employee_combobox.set(display_name)
                    self.employee_combobox.config(state="disabled")
                    self.selected_employee_id = self.default_emp_id
                    self._load_attendance_logs()
                else:
                    logger.warning(f"Default employee ID {self.default_emp_id} not found.")
                    self.employee_combobox['values'] = []
            elif self.view_mode == "manager_team" and self.manager_id:
                # TODO: Implement db_queries.get_employees_by_manager(self.manager_id)
                logger.info(f"Manager view mode for manager ID {self.manager_id} - populating with team (placeholder).")
                team_employees_dicts = db_queries.get_employees_by_manager_db(self.manager_id)
                populate_employee_combobox(self.employee_combobox, lambda: team_employees_dicts, default_to_first=True) # Removed combo_map_dict

            else: # Normal mode, load all employees
                populate_employee_combobox(self.employee_combobox, db_queries.get_all_employees_db, default_to_first=True) # Changed to get_all_employees_db, removed combo_map_dict

            # Build the map after combobox is populated
            for display_name_val in self.employee_combobox.cget('values'):
                emp_id_from_display = extract_id_from_combobox_selection(display_name_val)
                if emp_id_from_display:
                    self.employee_combobox_map[display_name_val] = emp_id_from_display
            
            # If a value is set by populate_employee_combobox (due to default_to_first=True), trigger selection
            if self.employee_combobox.get():
                self._on_employee_selected()

        except Exception as e:
            logger.error(f"Failed to populate employee combobox: {e}", exc_info=True)
            messagebox.showerror(_("db_error_title"), _("error_loading_employees_message"), parent=self)

    def _on_employee_selected(self, event=None):
        self.selected_employee_id = extract_id_from_combobox_selection(self.employee_combobox.get())
        if self.selected_employee_id:
            self._load_attendance_logs()

    def _load_attendance_logs(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        self.total_hours_var.set("Total Hours Worked: 0.00")
        self.total_days_var.set("Total Days Present: 0")

        emp_id = self._get_selected_employee_id()
        start_date_str = self.start_date_entry.entry.get() # Get from DateEntry's internal entry
        end_date_str = self.end_date_entry.entry.get()
        emp_id_to_load = self.selected_employee_id

        if not emp_id_to_load:
            messagebox.showwarning("Input Error", "Please select an employee.", parent=self)
            return
# Parent should be self
        try: # Validate dates
            start_dt = dt_date.fromisoformat(start_date_str)
            end_dt = dt_date.fromisoformat(end_date_str)
            if start_dt > end_dt:
                messagebox.showerror("Input Error", "Start date cannot be after end date.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format. Please use YYYY-MM-DD for both dates.", parent=self) # Parent should be self
            return

        try:
            logs = db_queries.get_attendance_logs_for_employee_period(emp_id_to_load, start_date_str, end_date_str)
            total_hours = 0.0
            present_days = set()

            if not logs:
                messagebox.showinfo("No Records", "No attendance records found for the selected criteria.", parent=self) # Parent should be self
                return

            for log in logs:
                clock_in_dt = datetime.strptime(log[db_schema.COL_ATT_CLOCK_IN], '%Y-%m-%d %H:%M:%S')
                clock_out_dt_str = log.get(db_schema.COL_ATT_CLOCK_OUT)
                clock_out_display = ""
                duration_str = "N/A (Open)"

                if clock_out_dt_str:
                    clock_out_dt = datetime.strptime(clock_out_dt_str, '%Y-%m-%d %H:%M:%S')
                    clock_out_display = clock_out_dt.strftime('%I:%M:%S %p')
                    # Assuming calculate_worked_duration is available (e.g., in db_queries or utils)
                    duration = db_queries.calculate_worked_duration(log[db_schema.COL_ATT_CLOCK_IN], clock_out_dt_str)
                    if duration is not None:
                        duration_str = f"{duration:.2f}"
                        total_hours += duration
                        present_days.add(log[db_schema.COL_ATT_LOG_DATE]) # Add date to set of present days
                
                self.log_tree.insert("", "end", values=(
                    log[db_schema.COL_ATT_LOG_DATE],
                    clock_in_dt.strftime('%I:%M:%S %p'), # Format for display
                    clock_out_display,
                    duration_str
                ))
            
            self.total_hours_var.set(_("attendance_log_total_hours_format", hours=f"{total_hours:.2f}")) # Add key
            self.total_days_var.set(_("attendance_log_total_days_format", days=len(present_days))) # Add key

        except (EmployeeNotFoundError, DatabaseOperationError) as e:
            messagebox.showerror("Error", str(e), parent=self) # Parent should be self
        except Exception as e:
            logger.error(f"Unexpected error loading attendance log: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)

    def _get_selected_employee_id(self) -> Optional[str]:
        """Gets the employee ID from the combobox selection."""
        return self.selected_employee_id