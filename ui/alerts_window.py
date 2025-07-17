# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\alerts_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from datetime import datetime, date as dt_date, timedelta
import logging

# --- Project-specific imports ---
# Assuming these are the correct relative paths from ui/alerts_window.py
from data import database as db_schema # For constants if needed by AlertsWindow directly
from utils.localization import _ # Import the translation function
from data import queries as db_queries # For backend functions like generate_hr_alerts_report # Corrected
from utils.gui_utils import populate_employee_combobox # If needed for filters
import config # For default work days, start time etc.

from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class AlertsWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("alerts_window_title")) # Use translation key
        self.geometry("1000x800")
        self.translatable_widgets_alerts = [] # For AlertsWindow specific translatable widgets

        # --- Parameters Frame ---
        params_outer_frame = ttk.LabelFrame(self, text=_("alerts_params_frame_title"), padding="10")
        params_outer_frame.pack(side="top", fill="x", padx=10, pady=10)
        self._add_translatable_widget_alerts(params_outer_frame, "alerts_params_frame_title")


        params_grid_frame = ttk.Frame(params_outer_frame) # Inner frame for grid layout
        params_grid_frame.pack(fill="x")

        # Date Range
        start_lbl = ttk.Label(params_grid_frame, text=_("alerts_period_start_label")); start_lbl.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(start_lbl, "alerts_period_start_label")
        self.alert_period_start_entry = DateEntry(params_grid_frame, width=12, dateformat='%Y-%m-%d')
        self.alert_period_start_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.alert_period_start_entry.date = dt_date.today() - timedelta(days=30)

        end_lbl = ttk.Label(params_grid_frame, text=_("alerts_period_end_label")); end_lbl.grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(end_lbl, "alerts_period_end_label")
        self.alert_period_end_entry = DateEntry(params_grid_frame, width=12, dateformat='%Y-%m-%d')
        self.alert_period_end_entry.grid(row=0, column=3, sticky="ew", padx=5, pady=2)
        self.alert_period_end_entry.date = dt_date.today()

        # Thresholds
        abs_thresh_lbl = ttk.Label(params_grid_frame, text=_("alerts_absence_threshold_label")); abs_thresh_lbl.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(abs_thresh_lbl, "alerts_absence_threshold_label")
        self.absence_threshold_var = tk.StringVar(value="2") # Default to 2
        self.absence_threshold_spin = ttk.Spinbox(params_grid_frame, from_=1, to=30, textvariable=self.absence_threshold_var, width=5)
        self.absence_threshold_spin.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        tardy_thresh_lbl = ttk.Label(params_grid_frame, text=_("alerts_tardiness_threshold_label")); tardy_thresh_lbl.grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(tardy_thresh_lbl, "alerts_tardiness_threshold_label")
        self.tardy_threshold_var = tk.StringVar(value="5")
        self.tardy_threshold_spin = ttk.Spinbox(params_grid_frame, from_=1, to=30, textvariable=self.tardy_threshold_var, width=5)
        self.tardy_threshold_spin.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        # Standard Start Time
        std_start_lbl = ttk.Label(params_grid_frame, text=_("alerts_std_start_time_label")); std_start_lbl.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(std_start_lbl, "alerts_std_start_time_label")
        self.std_start_time_var = tk.StringVar(value=config.STANDARD_START_TIME_CONFIG_DEFAULT)
        self.std_start_time_entry = ttk.Entry(params_grid_frame, textvariable=self.std_start_time_var, width=12)
        self.std_start_time_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Work Days Selection
        work_days_lbl = ttk.Label(params_grid_frame, text=_("alerts_expected_work_days_label")); work_days_lbl.grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self._add_translatable_widget_alerts(work_days_lbl, "alerts_expected_work_days_label")
        work_days_frame = ttk.Frame(params_grid_frame)
        work_days_frame.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=2)

        self.work_day_vars = [tk.BooleanVar() for _ in range(7)] # Mon-Sun
        days_of_week_keys = ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri", "day_sat", "day_sun"] # Keys for translation
        default_work_indices = config.DEFAULT_WORK_DAYS_INDICES
        for i, day_key in enumerate(days_of_week_keys):
            cb = ttk.Checkbutton(work_days_frame, text=_(day_key), variable=self.work_day_vars[i])
            cb.pack(side="left", padx=3)
            self._add_translatable_widget_alerts(cb, day_key) # Register for translation
            if i in default_work_indices:
                self.work_day_vars[i].set(True)

        generate_alerts_btn = ttk.Button(params_grid_frame, text=_("alerts_generate_button"), command=self._gui_generate_alerts, bootstyle=db_schema.BS_ADD)
        generate_alerts_btn.grid(row=4, column=3, sticky="e", padx=5, pady=10)
        self._add_translatable_widget_alerts(generate_alerts_btn, "alerts_generate_button")

        # --- Alerts Display Frame ---
        alerts_display_frame = ttk.LabelFrame(self, text=_("alerts_generated_alerts_frame_title"), padding="10")
        alerts_display_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._add_translatable_widget_alerts(alerts_display_frame, "alerts_generated_alerts_frame_title")


        self.alerts_tree_cols = ("emp_id", "emp_name", "alert_type", "count", "details")
        self.alerts_tree = ttk.Treeview(alerts_display_frame, columns=self.alerts_tree_cols, show="headings")

        # Configure headings
        self._update_alerts_tree_headers() # Call method to set headers

        # Configure column widths and properties
        self.alerts_tree.column("emp_id", width=80, anchor="w")
        self.alerts_tree.column("emp_name", width=150, anchor="w")
        self.alerts_tree.column("alert_type", width=150, anchor="w")
        self.alerts_tree.column("count", width=80, anchor="e")
        self.alerts_tree.column("details", width=350, stretch=tk.YES)

        # Add scrollbars
        alerts_scrollbar_y = ttk.Scrollbar(alerts_display_frame, orient="vertical", command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=alerts_scrollbar_y.set)

        alerts_scrollbar_x = ttk.Scrollbar(alerts_display_frame, orient="horizontal", command=self.alerts_tree.xview)
        self.alerts_tree.configure(xscrollcommand=alerts_scrollbar_x.set)

        self.alerts_tree.pack(side="left", fill="both", expand=True)
        alerts_scrollbar_y.pack(side="right", fill="y")
        alerts_scrollbar_x.pack(side="bottom", fill="x")

    def _add_translatable_widget_alerts(self, widget, key):
        self.translatable_widgets_alerts.append((widget,key))

    def _update_alerts_tree_headers(self):
        """Updates the headers of the alerts treeview based on current language."""
        if hasattr(self, 'alerts_tree') and self.alerts_tree.winfo_exists():
            self.alerts_tree.heading("emp_id", text=_("alerts_header_emp_id"))
            self.alerts_tree.heading("emp_name", text=_("alerts_header_emp_name"))
            self.alerts_tree.heading("alert_type", text=_("alerts_header_alert_type"))
            self.alerts_tree.heading("count", text=_("alerts_header_count"))
            self.alerts_tree.heading("details", text=_("alerts_header_details"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("alerts_window_title"))
        self._update_alerts_tree_headers() # Refresh tree headers
        for widget, key in self.translatable_widgets_alerts:
            if widget.winfo_exists():
                try: widget.config(text=_(key))
                except tk.TclError:
                    if isinstance(widget, ttk.LabelFrame): widget.config(text=_(key))

    def _gui_generate_alerts(self):
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)

        self.config(cursor="watch")
        self.update_idletasks()

        start_date_str = self.alert_period_start_entry.entry.get()
        end_date_str = self.alert_period_end_entry.entry.get()
        std_start_time_str = self.std_start_time_var.get()

        try:
            absence_thresh = int(self.absence_threshold_var.get())
            tardy_thresh = int(self.tardy_threshold_var.get())
            if absence_thresh <= 0 or tardy_thresh <= 0:
                messagebox.showerror(_("input_error_title"), _("alerts_threshold_positive_error"), parent=self)
                return
            datetime.strptime(start_date_str, '%Y-%m-%d')
            datetime.strptime(end_date_str, '%Y-%m-%d')
            datetime.strptime(std_start_time_str, '%H:%M:%S')
        except ValueError:
            messagebox.showerror(_("input_error_title"), _("alerts_invalid_format_error"), parent=self)
            self.config(cursor="")
            return

        selected_work_days = [i for i, var in enumerate(self.work_day_vars) if var.get()]
        if not selected_work_days:
            messagebox.showerror(_("input_error_title"), _("alerts_select_workday_error"), parent=self)
            self.config(cursor="")
            return
        try:
            alerts_data = db_queries.generate_hr_alerts_report(
                start_date_str, end_date_str,
                absence_thresh, tardy_thresh,
                selected_work_days, std_start_time_str
            )
            if not alerts_data:
                messagebox.showinfo(_("alerts_no_alerts_title"), _("alerts_no_alerts_message"), parent=self)
                self.config(cursor="")
                return

            for alert_item in alerts_data:
                self.alerts_tree.insert("", "end", values=(
                    alert_item['employee_id'], alert_item['employee_name'],
                    alert_item['alert_type'], alert_item['count'],
                    alert_item['details']
                ))
        except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(_("alerts_generation_error_title"), str(e), parent=self)
        finally:
            self.config(cursor="")
