# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\dashboard_window.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging
from datetime import date as dt_date, timedelta # Added dt_date and timedelta
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd # If pandas is used for data manipulation for charts
import matplotlib.pyplot as plt # Keep one import for pyplot
from ttkbootstrap.widgets import DateEntry # Added DateEntry import
from ttkbootstrap.tooltip import ToolTip # Added import for ToolTip

# --- Project-specific imports ---
import config # Added import for config
from data import database as db_schema # Added db_schema import
from data import queries as db_queries
from utils.localization import _ # Import _ directly
from utils.chart_utils import create_bar_chart, create_pie_chart, create_line_chart # If you have these helpers
from .themed_toplevel import ThemedToplevel
from utils.theming_utils import get_theme_palette_global # Added import

logger = logging.getLogger(__name__)

class DashboardWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("dashboard_window_title")) # Use translation key
        self.geometry("900x700") # Adjusted size
        self.translatable_widgets_dashboard = [] # For DashboardWindow specific translatable widgets

        # --- Main Frame for Dashboard Content ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # --- Period Selection Frame ---
        period_frame = ttk.LabelFrame(main_frame, text=_("dashboard_period_label"), padding="10")
        period_frame.pack(side="top", fill="x", pady=(0,10))
        self._add_translatable_widget_dashboard(period_frame, "dashboard_period_label")

        ttk.Label(period_frame, text=_("dashboard_from_date_label")).pack(side="left", padx=5)
        self._add_translatable_widget_dashboard(period_frame.winfo_children()[-1], "dashboard_from_date_label")
        self.dash_start_date_entry = DateEntry(period_frame, width=12, dateformat='%Y-%m-%d')
        self.dash_start_date_entry.pack(side="left", padx=5)
        self.dash_start_date_entry.date = dt_date.today().replace(day=1) - timedelta(days=30*2) # Default to 2 months ago, start of month
        self.dash_start_date_entry.date = self.dash_start_date_entry.date.replace(day=1)

        ttk.Label(period_frame, text=_("dashboard_to_date_label")).pack(side="left", padx=5)
        self._add_translatable_widget_dashboard(period_frame.winfo_children()[-1], "dashboard_to_date_label")
        self.dash_end_date_entry = DateEntry(period_frame, width=12, dateformat='%Y-%m-%d')
        self.dash_end_date_entry.pack(side="left", padx=5)
        self.dash_end_date_entry.date = dt_date.today()

        refresh_btn_key = "dashboard_refresh_btn_text"
        self.dash_refresh_btn = ttk.Button(period_frame, text=_(refresh_btn_key), command=self._load_dashboard_data, bootstyle=db_schema.BS_VIEW_EDIT)
        self.dash_refresh_btn.pack(side="left", padx=10)
        self._add_translatable_widget_dashboard(self.dash_refresh_btn, refresh_btn_key)

        # --- Key Metrics Cards Section ---
        cards_frame = ttk.Frame(main_frame) # No LabelFrame, just a container for cards
        cards_frame.pack(side="top", fill="x", pady=10)
        cards_frame.columnconfigure(0, weight=1) # Make columns expand equally
        for i in range(5): # Now 5 cards
            cards_frame.columnconfigure(i, weight=1)

        self.metric_vars = {
            "total_employees": tk.StringVar(value="--"),
            "pending_vacations": tk.StringVar(value="--"),
            "total_departments": tk.StringVar(value="--"),
            "absences_today": tk.StringVar(value="--"),
            "avg_performance": tk.StringVar(value="--") # New metric
        }

        # Pass the original key and the translated title separately
        self._create_metric_card(cards_frame, "dashboard_card_employees", _("dashboard_card_employees"), self.metric_vars["total_employees"], "primary", 0)
        self._create_metric_card(cards_frame, "dashboard_card_pending_leaves", _("dashboard_card_pending_leaves"), self.metric_vars["pending_vacations"], "warning", 1)
        self._create_metric_card(cards_frame, "dashboard_card_departments", _("dashboard_card_departments"), self.metric_vars["total_departments"], "info", 2)
        self._create_metric_card(cards_frame, "dashboard_card_absences_today", _("dashboard_card_absences_today"), self.metric_vars["absences_today"], "danger", 3)
        self._create_metric_card(cards_frame, "dashboard_card_avg_performance", _("dashboard_card_avg_performance"), self.metric_vars["avg_performance"], "success", 4)

        # Bind click for pending vacations card
        # The card itself is a LabelFrame, we need to find its child label for binding if specific text is clickable
        # For simplicity, let's assume clicking anywhere on the "Pending Vacations" card opens the leave management.
        # We need a reference to the card widget. _create_metric_card will store it.
        # This will be handled after _create_metric_card is defined and called.
        
        # Example of how to bind if card_widget is the LabelFrame:
        # self.pending_vacations_card.bind("<Button-1>", self._open_vacation_management)
        # self.pending_vacations_card.bind("<Enter>", lambda e, w=self.pending_vacations_card: w.config(cursor="hand2"))
        # self.pending_vacations_card.bind("<Leave>", lambda e, w=self.pending_vacations_card: w.config(cursor=""))

        # Link for pending leaves (if not using card click)
        # self.pending_leaves_label = ttk.Label(metrics_frame, textvariable=self.pending_leaves_var, font=("Helvetica", 12))
        # self.pending_leaves_label.pack(anchor="w", pady=2)
        # self.pending_leaves_label.bind("<Button-1>", self._open_vacation_management)

        # --- Charts Section (Using Matplotlib subplots) ---
        # This is where the Notebook for chart tabs will go
        charts_outer_frame = ttk.LabelFrame(main_frame, text=_("dashboard_charts_section_title"), padding="10")
        charts_outer_frame.pack(side="top", fill="both", expand=True, pady=10)
        self._add_translatable_widget_dashboard(charts_outer_frame, "dashboard_charts_section_title")

        # --- Tab Creation for Charts ---
        self.notebook = ttk.Notebook(charts_outer_frame) # Notebook inside the "Visualizations" frame

        # Employee Tab
        self.employee_tab = ttk.Frame(self.notebook)
        self._create_employee_tab_content(self.employee_tab) # This creates self.emp_fig, self.emp_axs_array, self.emp_canvas
        self.notebook.add(self.employee_tab, text=_("dashboard_tab_employees"))

        # Attendance Tab
        self.attendance_tab = ttk.Frame(self.notebook)
        self._create_attendance_tab_content(self.attendance_tab) # This creates self.att_fig, self.att_axs, self.att_canvas
        self.notebook.add(self.attendance_tab, text=_("dashboard_tab_attendance"))

        # Payroll Tab
        self.payroll_tab = ttk.Frame(self.notebook)
        self._create_payroll_tab_content(self.payroll_tab) # This creates self.payroll_fig, self.payroll_axs, self.payroll_canvas
        self.notebook.add(self.payroll_tab, text=_("dashboard_tab_payroll"))

        # Performance Tab (currently empty of charts, but structure is there)
        self.performance_tab = ttk.Frame(self.notebook)
        self._create_performance_tab_content(self.performance_tab) # This creates self.perf_fig, self.perf_axs, self.perf_canvas
        self.notebook.add(self.performance_tab, text=_("dashboard_tab_performance"))

        self.notebook.pack(expand=True, fill="both")

        # Old single canvas setup (REMOVED as charts are now in tabs)
        # self.fig, self.axs = plt.subplots(2, 2, figsize=(8, 6), dpi=100)
        # self.axs = self.axs.flatten()
        # self.fig.tight_layout(pad=3.0)
        # self.canvas = FigureCanvasTkAgg(self.fig, master=charts_outer_frame)
        # self.canvas_widget = self.canvas.get_tk_widget()
        # self.canvas_widget.pack(side="top", fill="both", expand=True)
        # self.canvas.draw()
        self._load_dashboard_data()
        # update_local_theme_elements is called by ThemedToplevel's __init__ via self.after()

    def _add_translatable_widget_dashboard(self, widget, key, attr="text"):
        """Helper to register translatable widgets for DashboardWindow."""
        # Ensure the attribute 'title' is used for LabelFrames if not specified for them
        if isinstance(widget, ttk.LabelFrame) and attr == "text": # Default attr is text
            actual_attr = "title"
        else:
            actual_attr = attr
        self.translatable_widgets_dashboard.append({"widget": widget, "key": key, "attr": actual_attr})
    
    def _create_employee_tab_content(self, tab_frame):
        """Creates the content for the 'Employees' tab in the dashboard."""
        # Figure for this tab, 1 row, 2 columns (for two charts side-by-side)
        self.emp_fig, self.emp_axs_array = plt.subplots(1, 2, figsize=(10, 4.5), dpi=100) # Returns fig and an array of Axes
        self.emp_fig.tight_layout(pad=4.0) # Increased padding
        
        self.emp_canvas = FigureCanvasTkAgg(self.emp_fig, master=tab_frame)
        self.emp_canvas_widget = self.emp_canvas.get_tk_widget()
        self.emp_canvas_widget.pack(side="top", fill="both", expand=True)

        # Frame for counters below the charts
        counters_frame = ttk.Frame(tab_frame, padding=(0, 10, 0, 0)) # Add some top padding
        counters_frame.pack(side="top", fill="x", pady=5)

        # Total Active Employees Counter
        self.total_employees_counter_var = tk.StringVar(value="--")
        total_emp_lbl = ttk.Label(counters_frame, text=_("dashboard_counter_total_employees"), font=("Helvetica", 10, "bold")); total_emp_lbl.pack(side="left", padx=(10,0))
        self._add_translatable_widget_dashboard(total_emp_lbl, "dashboard_counter_total_employees")
        ttk.Label(counters_frame, textvariable=self.total_employees_counter_var, font=("Helvetica", 10)).pack(side="left", padx=(0,20))

        # New Employees This Month Counter
        self.new_hires_counter_var = tk.StringVar(value="--")
        new_hires_lbl = ttk.Label(counters_frame, text=_("dashboard_counter_new_this_month"), font=("Helvetica", 10, "bold")); new_hires_lbl.pack(side="left", padx=(10,0))
        self._add_translatable_widget_dashboard(new_hires_lbl, "dashboard_counter_new_this_month")
        ttk.Label(counters_frame, textvariable=self.new_hires_counter_var, font=("Helvetica", 10)).pack(side="left", padx=(0,20))

    def _create_attendance_tab_content(self, tab_frame):
        """Creates the content for the 'Attendance' tab in the dashboard."""
        # Figure for this tab, 1 row, 2 columns (for two charts side-by-side)
        self.att_fig, self.att_axs = plt.subplots(1, 2, figsize=(10, 4.5), dpi=100) # Returns fig and an array of Axes
        self.att_fig.tight_layout(pad=4.0)
        
        self.att_canvas = FigureCanvasTkAgg(self.att_fig, master=tab_frame)
        self.att_canvas_widget = self.att_canvas.get_tk_widget()
        self.att_canvas_widget.pack(side="top", fill="both", expand=True)

    def _create_payroll_tab_content(self, tab_frame):
        """Creates the content for the 'Payroll' tab in the dashboard."""
        self.payroll_fig, self.payroll_axs = plt.subplots(1, 2, figsize=(10, 4.5), dpi=100) # Now 1 row, 2 columns
        self.payroll_fig.tight_layout(pad=4.0)

        self.payroll_canvas = FigureCanvasTkAgg(self.payroll_fig, master=tab_frame)
        self.payroll_canvas_widget = self.payroll_canvas.get_tk_widget()
        self.payroll_canvas_widget.pack(side="top", fill="both", expand=True)

    def _create_performance_tab_content(self, tab_frame):
        """Creates the content for the 'Performance' tab in the dashboard."""
        self.perf_fig, self.perf_axs = plt.subplots(1, 1, figsize=(7, 5), dpi=100) # Single Axes for now
        self.perf_fig.tight_layout(pad=3.0)
        self.perf_canvas = FigureCanvasTkAgg(self.perf_fig, master=tab_frame)
        self.perf_canvas_widget = self.perf_canvas.get_tk_widget()
        self.perf_canvas_widget.pack(side="top", fill="both", expand=True)

    def _create_metric_card(self, parent_frame, original_key: str, display_title: str, value_var: tk.StringVar, bootstyle: str, col_index: int):
        """Helper to create a styled metric card."""
        card_lf = ttk.LabelFrame(parent_frame, text=display_title, bootstyle=bootstyle, padding="15")
        card_lf.grid(row=0, column=col_index, padx=5, pady=5, sticky="nsew")

        value_label = ttk.Label(card_lf, textvariable=value_var, font=("Helvetica", 24, "bold"), bootstyle=f"{bootstyle}-inverse") # Inverse for contrast
        value_label.pack(pady=10, expand=True)

        # Store reference if needed for binding, e.g., for pending vacations
        if original_key == "dashboard_card_pending_leaves":
            self.pending_vacations_card_widget = card_lf # Store the LabelFrame widget
            card_lf.bind("<Button-1>", self._open_vacation_management)
            card_lf.bind("<Enter>", lambda e, w=card_lf: w.config(cursor="hand2"))
            card_lf.bind("<Leave>", lambda e, w=card_lf: w.config(cursor="")); ToolTip(card_lf, text=_("tooltip_manage_leave_requests")) # Use a translation key
            ToolTip(card_lf, text=_("tooltip_manage_leave_requests")) # Use a translation key

        # Register the LabelFrame for title translation
        self._add_translatable_widget_dashboard(card_lf, original_key, attr="title") # Register with original key

    def update_local_theme_elements(self):
        super().update_local_theme_elements() # Call parent's method first

        # Update specific elements like the link label's color and chart theme
        palette = get_theme_palette_global(self.parent_app.get_current_theme())

        if hasattr(self, 'pending_leaves_label') and self.pending_leaves_label.winfo_exists():
            # This label might have been removed in favor of the card.
            # If kept, style it:
            # link_fg_color = palette.get('tree_selected_bg', 'blue') # Using a theme color for the link
            # self.pending_leaves_label.configure(foreground=link_fg_color)
            pass

        # Update matplotlib chart colors for all tab figures within the dashboard
        figures_and_axes = []
        if hasattr(self, 'emp_fig') and hasattr(self, 'emp_axs_array'): figures_and_axes.append((self.emp_fig, self.emp_axs_array, getattr(self, 'emp_canvas', None)))
        if hasattr(self, 'att_fig') and hasattr(self, 'att_axs'): figures_and_axes.append((self.att_fig, self.att_axs, getattr(self, 'att_canvas', None)))
        if hasattr(self, 'payroll_fig') and hasattr(self, 'payroll_axs'): figures_and_axes.append((self.payroll_fig, self.payroll_axs, getattr(self, 'payroll_canvas', None)))
        # Note: self.perf_axs is a single Axes object, not an array.
        if hasattr(self, 'perf_fig') and hasattr(self, 'perf_axs'): figures_and_axes.append((self.perf_fig, [self.perf_axs], getattr(self, 'perf_canvas', None))) # perf_axs is single

        bg_color = palette.get('bg_secondary', '#FFFFFF')
        fg_color = palette.get('fg_primary', '#000000')
        bar_colors_palette = [palette.get('tree_selected_bg', 'skyblue'), palette.get('button_active_bg', 'lightcoral'), '#77dd77', '#fdfd96', '#aec6cf', '#ffb347']

        for fig, axes_list, canvas_instance in figures_and_axes:
            if hasattr(fig, 'winfo_exists') and fig.winfo_exists() and canvas_instance and canvas_instance.get_tk_widget().winfo_exists():
                fig.patch.set_facecolor(bg_color)
                for i, ax in enumerate(axes_list):
                    ax.set_facecolor(bg_color)
                    ax.title.set_color(fg_color)
                    ax.xaxis.label.set_color(fg_color)
                    ax.yaxis.label.set_color(fg_color)
                    ax.tick_params(axis='x', colors=fg_color)
                    ax.tick_params(axis='y', colors=fg_color)
                    for bar_patch in ax.patches: # Update color of existing bars
                        bar_patch.set_facecolor(bar_colors_palette[i % len(bar_colors_palette)])
                    canvas_instance.draw_idle()

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("dashboard_window_title"))
        # Update notebook tab texts
        if hasattr(self, 'notebook') and self.notebook.winfo_exists():
            self.notebook.tab(self.employee_tab, text=_("dashboard_tab_employees"))
            self.notebook.tab(self.attendance_tab, text=_("dashboard_tab_attendance"))
            self.notebook.tab(self.payroll_tab, text=_("dashboard_tab_payroll"))
            self.notebook.tab(self.performance_tab, text=_("dashboard_tab_performance"))

        for item_info in self.translatable_widgets_dashboard:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")
            if widget.winfo_exists():
                try:
                    if attr_to_update == "text": widget.config(text=_(key))
                    elif attr_to_update == "title": widget.config(text=_(key)) # For LabelFrames
                except tk.TclError: pass

    def _load_dashboard_data(self):
        self.config(cursor="watch")
        self.update_idletasks()
        period_start = self.dash_start_date_entry.entry.get()
        period_end = self.dash_end_date_entry.entry.get()
        work_day_indices = config.DEFAULT_WORK_DAYS_INDICES # Use from config

        try:
            # Validate dates
            dt_date.fromisoformat(period_start)
            dt_date.fromisoformat(period_end)

            # --- Key Metrics ---
            self.metric_vars["total_employees"].set(str(db_queries.get_total_employee_count_db()))
            self.metric_vars["total_departments"].set(str(len(db_queries.list_departments_db())))
            
            # Pending leaves for the selected period (or all if no period filter in get_pending_leave_requests_db)
            # For the card, let's show all pending leaves, not just for the period.
            all_pending_leaves = db_queries.get_pending_leave_requests_db() # Get all pending # Corrected: Use db_schema for COL_LR_STATUS
            self.metric_vars["pending_vacations"].set(str(len(all_pending_leaves)))

            # Absences today
            absences_today = db_queries.get_absences_today_count_db()
            self.metric_vars["absences_today"].set(str(absences_today))
            
            # Overall Average Performance
            avg_perf = db_queries.get_overall_average_performance_score_db(period_start, period_end)
            self.metric_vars["avg_performance"].set(f"{avg_perf:.2f}" if avg_perf is not None else "N/A")


            # --- Chart Data ---
            palette = get_theme_palette_global(self.parent_app.get_current_theme())
            bar_colors = [palette.get('tree_selected_bg', 'skyblue'), 
                          palette.get('button_active_bg', 'lightcoral'), 
                          '#77dd77', '#fdfd96', '#aec6cf', '#ffb347'] # Skyblue, Lightcoral, PastelGreen, PastelYellow, PastelBlue, PastelOrange

            # --- Employee Tab Charts (already refactored in previous step) ---            if hasattr(self, 'emp_axs_array'):
            for ax_emp in self.emp_axs_array:
                ax_emp.clear()

            
            dept_summary_data = db_queries.get_department_summary_report()
            
            dept_names = [item.get(db_schema.COL_EMP_DEPARTMENT) or "Unassigned" for item in dept_summary_data]
            headcounts = [item.get('employee_count', 0) for item in dept_summary_data]
            if dept_names and hasattr(self, 'emp_axs_array') and len(self.emp_axs_array) > 0:
                self.emp_axs_array[0].bar(dept_names, headcounts, color=bar_colors[0 % len(bar_colors)])
                self.emp_axs_array[0].set_title(_("dashboard_chart_headcount_title"))
                self.emp_axs_array[0].set_ylabel("Employees")
                self.emp_axs_array[0].tick_params(axis='x', rotation=30)
                self.emp_axs_array[0].grid(True, axis='y', linestyle='--', alpha=0.7)

            # Corrected: Use db_queries for data fetching
            contract_type_data = db_queries.get_employee_contract_type_counts_db()
            if contract_type_data and hasattr(self, 'emp_axs_array') and len(self.emp_axs_array) > 1:
                labels = contract_type_data.keys()
                sizes = contract_type_data.values()
                
                pie_colors = bar_colors[1:1+len(labels)] if len(labels) > 0 else bar_colors
                self.emp_axs_array[1].pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=pie_colors)
                self.emp_axs_array[1].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                self.emp_axs_array[1].set_title(_("dashboard_chart_contract_type_title"))
            # Update Employee Tab Counters
            if hasattr(self, 'total_employees_counter_var'):
                self.total_employees_counter_var.set(str(db_queries.get_total_employee_count_db()))
            if hasattr(self, 'new_hires_counter_var'):
                self.new_hires_counter_var.set(str(db_queries.get_new_employees_this_month_count_db()))

            if hasattr(self, 'emp_canvas'): self.emp_canvas.draw()

# --- Attendance Tab Charts ---
            if hasattr(self, 'att_axs'): # att_axs is an array of 2 axes
                for ax_att in self.att_axs: # Ensure att_axs is iterable
                    ax_att.clear()
            # Chart 1 (Attendance Tab): Absenteeism Rate by Department
            absenteeism_data = db_queries.get_absenteeism_rate_by_department_db(period_start, period_end, work_day_indices)
            if absenteeism_data and hasattr(self, 'att_axs') and len(self.att_axs) > 0:
                self.att_axs[0].bar(absenteeism_data.keys(), absenteeism_data.values(), color=bar_colors[1 % len(bar_colors)])
                self.att_axs[0].set_title(_("dashboard_chart_absenteeism_title"))
                self.att_axs[0].set_ylabel("Rate (%)")
                self.att_axs[0].tick_params(axis='x', rotation=30)
                self.att_axs[0].grid(True, axis='y', linestyle='--', alpha=0.7)
            # Chart 2 (Attendance Tab): Department Attendance Adherence
            adherence_data = db_queries.get_department_attendance_adherence_db(period_start, period_end, work_day_indices)
            if adherence_data and hasattr(self, 'att_axs') and len(self.att_axs) > 1:
                self.att_axs[1].bar(adherence_data.keys(), adherence_data.values(), color=bar_colors[3 % len(bar_colors)])
                self.att_axs[1].set_title(_("dashboard_chart_dept_adherence_title"))
                self.att_axs[1].set_ylabel("Adherence (%)")
                self.att_axs[1].tick_params(axis='x', rotation=30)
                self.att_axs[1].grid(True, axis='y', linestyle='--', alpha=0.7)
            if hasattr(self, 'att_canvas'): self.att_canvas.draw()

            # --- Payroll Tab Charts ---
            if hasattr(self, 'payroll_axs'): # payroll_axs is now an array of 2 axes
                for ax_payroll in self.payroll_axs:
                    ax_payroll.clear()
            # Chart 1 (Payroll Tab): Payslips Generated by Department
            payslips_data = db_queries.get_payslips_generated_by_department_db(period_start, period_end)
            if payslips_data and hasattr(self, 'payroll_axs') and len(self.payroll_axs) > 0:
                self.payroll_axs[0].bar(payslips_data.keys(), payslips_data.values(), color=bar_colors[4 % len(bar_colors)])
                self.payroll_axs[0].set_title(_("dashboard_chart_payslips_title"))
                self.payroll_axs[0].set_ylabel("Number of Payslips")
                self.payroll_axs[0].tick_params(axis='x', rotation=30)
                self.payroll_axs[0].grid(True, axis='y', linestyle='--', alpha=0.7)
            # Chart 2 (Payroll Tab): Leave Request Statuses

            leave_summary = db_queries.get_leave_request_status_summary_db(period_start, period_end)
            if leave_summary and hasattr(self, 'payroll_axs') and len(self.payroll_axs) > 1:
                self.payroll_axs[1].bar(leave_summary.keys(), leave_summary.values(), color=bar_colors[2 % len(bar_colors)])
                self.payroll_axs[1].set_title(_("dashboard_chart_leave_status_title"))
                self.payroll_axs[1].set_ylabel("Number of Requests")
                self.payroll_axs[1].tick_params(axis='x', rotation=30)
                self.payroll_axs[1].grid(True, axis='y', linestyle='--', alpha=0.7)
  
            if hasattr(self, 'payroll_canvas'): self.payroll_canvas.draw()
            # --- Performance Tab Chart ---
            if hasattr(self, 'perf_axs'): # perf_axs is a single Axes
                self.perf_axs.clear()
            avg_perf_by_dept_data = db_queries.get_average_performance_by_department_db(period_start, period_end)
            if avg_perf_by_dept_data and hasattr(self, 'perf_axs'):
                create_bar_chart(
                    self.perf_axs, avg_perf_by_dept_data,
                    title=_("dashboard_chart_avg_perf_dept_title"), # New key
                    xlabel=_("header_emp_department"), # Reuse key
                    ylabel=_("dashboard_chart_avg_perf_dept_ylabel"), # New key
                    bar_colors=[bar_colors[0 % len(bar_colors)]], rotation=30
                )
            # --- Performance Tab (currently empty, no charts to draw) ---
            if hasattr(self, 'perf_canvas'): self.perf_canvas.draw() # Draw empty if needed

            self.update_local_theme_elements()

        except ValueError as ve:
            messagebox.showerror(_("input_error_title"), f"Invalid date format for period: {ve}", parent=self)
            logger.error(f"Invalid date format for dashboard period: {ve}")
        except Exception as e: # pragma: no cover
            logger.error(f"Error loading dashboard data: {e}")
            # Update metric card vars on error
            if hasattr(self, 'metric_vars'):
                for key in self.metric_vars:
                    self.metric_vars[key].set("Error")
        finally:
            self.config(cursor="")

    def _open_vacation_management(self, event=None):
        """Opens the Vacation Management window."""
        if self.parent_app and hasattr(self.parent_app, 'hr_app_gui') and self.parent_app.hr_app_gui:
            self.parent_app.hr_app_gui.gui_show_vacation_management_window()
        else:
            logger.warning("Could not open Vacation Management window: HRAppGUI instance not found.")
            messagebox.showwarning("Navigation Error", "Cannot open the leave management window at this time.", parent=self)
