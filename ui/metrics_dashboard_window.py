# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\metrics_dashboard_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd # If pandas is used for data manipulation for charts
import matplotlib.pyplot as plt
import logging
from datetime import date as dt_date, timedelta # Added dt_date and timedelta
# --- Project-specific imports ---
from typing import Dict, List, Optional, Any # Added Dict, List, Optional, Any
from data import database as db_schema # For constants if needed
from data import queries as db_queries # For fetching metrics data
from utils import localization # For _()
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class MetricsDashboardWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("metrics_dashboard_title"))
        self.geometry("960x900")
        self.translatable_widgets_metrics = [] # Initialize for this window

        # --- Period Selection Frame ---
        period_frame = ttk.LabelFrame(self, text=localization._("dashboard_period_label"), padding="10") # Reusing key
        period_frame.pack(side="top", fill="x", padx=10, pady=(10,0))
        self._add_translatable_widget(period_frame, "dashboard_period_label", attr="title")

        ttk.Label(period_frame, text=localization._("dashboard_from_date_label")).pack(side="left", padx=5)
        self.metrics_start_date_entry = DateEntry(period_frame, width=12, dateformat='%Y-%m-%d')
        self.metrics_start_date_entry.pack(side="left", padx=5)
        self.metrics_start_date_entry.date = dt_date.today().replace(day=1) - timedelta(days=30*2) # Default to 2 months ago, start of month
        self.metrics_start_date_entry.date = self.metrics_start_date_entry.date.replace(day=1)
        ttk.Label(period_frame, text=localization._("dashboard_to_date_label")).pack(side="left", padx=5)
        self.metrics_end_date_entry = DateEntry(period_frame, width=12, dateformat='%Y-%m-%d')
        self.metrics_end_date_entry.pack(side="left", padx=5)
        self.metrics_end_date_entry.date = dt_date.today()

        refresh_btn_key = "dashboard_refresh_btn_text" # Reusing key
        self.metrics_refresh_btn = ttk.Button(period_frame, text=localization._(refresh_btn_key), command=self._load_metrics_data, bootstyle=db_schema.BS_VIEW_EDIT)
        self.metrics_refresh_btn.pack(side="left", padx=10)
        self._add_translatable_widget(self.metrics_refresh_btn, refresh_btn_key)

        self.translatable_widgets_metrics = []

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.hr_metrics_tab = ttk.Frame(self.notebook, padding="10")
        self.app_stats_tab = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.hr_metrics_tab, text=localization._("metrics_hr_tab_title"))
        self._add_translatable_widget(self.notebook, "metrics_hr_tab_title", attr="tab", tab_id=self.hr_metrics_tab, is_notebook_tab=True)
        self.notebook.add(self.app_stats_tab, text=localization._("metrics_app_usage_tab_title"))
        self._add_translatable_widget(self.notebook, "metrics_app_usage_tab_title", attr="tab", tab_id=self.app_stats_tab, is_notebook_tab=True)

        self._create_hr_metrics_widgets(self.hr_metrics_tab)
        self._create_app_stats_widgets(self.app_stats_tab)

        self._load_metrics_data()
        self.refresh_ui_for_language() # Initial translation

    def _add_translatable_widget(self, widget, key: str, attr: str = "text", tab_id: Optional[Any] = None, is_notebook_tab: bool = False):
        """Adds a widget to the list of translatable widgets for this specific window."""
        self.translatable_widgets_metrics.append({
            "widget": widget, "key": key, "attr": attr, "tab_id": tab_id, "is_notebook_tab": is_notebook_tab
        })

    def _create_hr_metrics_widgets(self, tab_frame):
        # Frame to hold multiple LabelFrames for better organization
        hr_metrics_content_frame = ttk.Frame(tab_frame)
        hr_metrics_content_frame.pack(fill="both", expand=True)

        # Configure columns for side-by-side layout if desired
        hr_metrics_content_frame.columnconfigure(0, weight=1)
        hr_metrics_content_frame.columnconfigure(1, weight=1)
        status_frame = ttk.LabelFrame(hr_metrics_content_frame, text=localization._("metrics_status_counts_title"), padding="10")
        status_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self._add_translatable_widget(status_frame, "metrics_status_counts_title", attr="title")
        self.status_tree = self._create_simple_treeview(status_frame, 
                                                        columns_config={"status": {"header_key": "metrics_header_status", "width": 150},
                                                                        "count": {"header_key": "metrics_header_count", "width": 80, "anchor": "e"}})

        gender_frame = ttk.LabelFrame(hr_metrics_content_frame, text=localization._("metrics_gender_counts_title"), padding="10")
        gender_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self._add_translatable_widget(gender_frame, "metrics_gender_counts_title", attr="title")
        self.gender_tree = self._create_simple_treeview(gender_frame,
                                                        columns_config={"gender": {"header_key": "metrics_header_gender", "width": 150},
                                                                        "count": {"header_key": "metrics_header_count", "width": 80, "anchor": "e"}})

        leave_frame = ttk.LabelFrame(hr_metrics_content_frame, text=localization._("metrics_leave_counts_title"), padding="10")
        leave_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self._add_translatable_widget(leave_frame, "metrics_leave_counts_title", attr="title")
        self.leave_tree = self._create_simple_treeview(leave_frame,
                                                       columns_config={"leave_type": {"header_key": "metrics_header_leave_type", "width": 150},
                                                                       "count": {"header_key": "metrics_header_count", "width": 80, "anchor": "e"}})

        # New Metrics Section
        general_hr_frame = ttk.LabelFrame(hr_metrics_content_frame, text=localization._("metrics_general_hr_title"), padding="10") # Add key
        general_hr_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self._add_translatable_widget(general_hr_frame, "metrics_general_hr_title", attr="title")

        self.avg_tenure_var = tk.StringVar(value="--")
        avg_tenure_lbl_key = "metrics_avg_tenure_label"
        ttk.Label(general_hr_frame, text=localization._(avg_tenure_lbl_key)).pack(anchor="w")
        self._add_translatable_widget(general_hr_frame.winfo_children()[-1], avg_tenure_lbl_key)
        ttk.Label(general_hr_frame, textvariable=self.avg_tenure_var, font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))

        self.new_hires_var = tk.StringVar(value="--")
        new_hires_lbl_key = "metrics_new_hires_label"
        ttk.Label(general_hr_frame, text=localization._(new_hires_lbl_key)).pack(anchor="w")
        self._add_translatable_widget(general_hr_frame.winfo_children()[-1], new_hires_lbl_key)
        ttk.Label(general_hr_frame, textvariable=self.new_hires_var, font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))

        self.terminations_var = tk.StringVar(value="--")
        terminations_lbl_key = "metrics_terminations_label"
        ttk.Label(general_hr_frame, text=localization._(terminations_lbl_key)).pack(anchor="w")
        self._add_translatable_widget(general_hr_frame.winfo_children()[-1], terminations_lbl_key)
        ttk.Label(general_hr_frame, textvariable=self.terminations_var, font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))

        self.active_contracts_var = tk.StringVar(value="--")
        active_contracts_lbl_key = "metrics_active_contracts_label"
        ttk.Label(general_hr_frame, text=localization._(active_contracts_lbl_key)).pack(anchor="w")
        self._add_translatable_widget(general_hr_frame.winfo_children()[-1], active_contracts_lbl_key)
        ttk.Label(general_hr_frame, textvariable=self.active_contracts_var, font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))


    def _create_app_stats_widgets(self, tab_frame):
        stats_frame = ttk.LabelFrame(tab_frame, text=localization._("metrics_general_stats_title"), padding="10")
        stats_frame.pack(fill="x", pady=5); self._add_translatable_widget(stats_frame, "metrics_general_stats_title", attr="title")
        self.app_stats_tree = self._create_simple_treeview(stats_frame,
                                                           columns_config={"statistic": {"header_key": "metrics_header_statistic", "width": 250},
                                                                           "value": {"header_key": "metrics_header_value", "width": 100, "anchor": "e"}})


    def _create_simple_treeview(self, parent_frame, columns_config: Dict[str, Dict]) -> ttk.Treeview:
        col_ids = list(columns_config.keys())
        tree = ttk.Treeview(parent_frame, columns=col_ids, show="headings", height=5)
        
        for col_id, config_dict in columns_config.items():
            header_text = localization._(config_dict.get("header_key", col_id.replace("_", " ").title()))
            width = config_dict.get("width", 120)
            anchor = config_dict.get("anchor", "w")
            stretch = config_dict.get("stretch", tk.YES if width == 0 else tk.NO)
            tree.heading(col_id, text=header_text, anchor=anchor)
            tree.column(col_id, width=width, anchor=anchor, stretch=stretch)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="x", expand=True); scrollbar.pack(side="right", fill="y")
        return tree

    def _populate_treeview_from_dict(self, tree: ttk.Treeview, data_dict: dict, col_id_map: Optional[Dict[str, str]] = None):
        for item in tree.get_children():
            tree.delete(item)
        for key, value in data_dict.items():
            display_key = localization._(key) if col_id_map and key in col_id_map else key # Translate key if mapping provided
            tree.insert("", "end", values=(display_key, value))

    def _populate_treeview_from_list(self, tree: ttk.Treeview, data_list: List[Dict], col_ids: List[str]):
        for item in tree.get_children():
            tree.delete(item)
        for row_dict in data_list:
            values_tuple = tuple(row_dict.get(col_id, "") for col_id in col_ids)
            tree.insert("", "end", values=values_tuple)

    def _load_metrics_data(self):
        start_date_str = self.metrics_start_date_entry.entry.get()
        end_date_str = self.metrics_end_date_entry.entry.get()
        try:
            dt_date.fromisoformat(start_date_str)
            dt_date.fromisoformat(end_date_str)
        except ValueError:
            messagebox.showerror(localization._("input_error_title"), localization._("invalid_date_format_yyyy_mm_dd_error"), parent=self)
            return

        # HR Metrics
        status_counts = db_queries.get_employee_status_counts_db()
        self._populate_treeview_from_dict(self.status_tree, status_counts)

        gender_counts = db_queries.get_employee_gender_counts_db()
        self._populate_treeview_from_dict(self.gender_tree, gender_counts)

        leave_counts = db_queries.get_leave_type_counts_db(start_date_str, end_date_str)
        self._populate_treeview_from_dict(self.leave_tree, leave_counts)

        avg_tenure_days = db_queries.get_average_employee_tenure_db()
        self.avg_tenure_var.set(f"{avg_tenure_days/365.25:.1f} years" if avg_tenure_days is not None else "N/A")

        new_hires = db_queries.get_new_hires_in_period_db(start_date_str, end_date_str)
        self.new_hires_var.set(str(new_hires))

        terminations = db_queries.get_terminations_in_period_db(start_date_str, end_date_str)
        self.terminations_var.set(str(terminations))

        active_contracts = db_queries.get_active_contracts_count_db() # Assuming this function exists
        self.active_contracts_var.set(str(active_contracts))

        # App Usage Stats
        app_counters = db_queries.get_all_app_counters_db()
        app_stats_data = {item[db_schema.COL_COUNTER_NAME]: item[db_schema.COL_COUNTER_VALUE] for item in app_counters}
        self._populate_treeview_from_dict(self.app_stats_tree, app_stats_data)

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("metrics_dashboard_title"))
        
        # Update notebook tab texts
        if hasattr(self, 'notebook') and self.notebook.winfo_exists():
            self.notebook.tab(self.hr_metrics_tab, text=localization._("metrics_hr_tab_title"))
            self.notebook.tab(self.app_stats_tab, text=localization._("metrics_app_usage_tab_title"))

        for item_info in self.translatable_widgets_metrics:
            widget = item_info["widget"]
            key = item_info["key"]
            attr = item_info.get("attr", "text")
            tab_id = item_info.get("tab_id")

            if widget.winfo_exists():
                try:
                    if attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title": # For LabelFrames
                        widget.config(text=localization._(key))
                    elif attr == "tab" and isinstance(widget, ttk.Notebook) and tab_id:
                        widget.tab(tab_id, text=localization._(key))
                except tk.TclError: pass
        
        # Refresh treeview headers by re-creating them (or update if method exists)
        # This requires storing the column_config used at creation or re-fetching it.
        # For simplicity, we might need to re-call the _create_..._widgets methods
        # or make _create_simple_treeview update headers.
        # For now, let's assume headers are set with _() at creation and might not need dynamic refresh
        # unless the keys themselves change, which is unlikely for headers.
        # If dynamic header refresh is needed, _create_simple_treeview needs modification.
        self._load_metrics_data() # Reload data which might re-populate treeviews with translated keys if applicable