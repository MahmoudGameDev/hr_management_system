import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
import threading
from datetime import datetime, timedelta, date as dt_date
import os
import csv
import logging
from typing import Dict, List, Any, Optional

from utils import localization
from utils.localization import _
from data import queries as db_queries
from data import database as db_schema
from utils import pdf_utils # Assuming pdf_utils is in the top-level utils
from utils.gui_utils import extract_id_from_combobox_selection, setup_treeview_columns, clear_treeview # Corrected import path
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

# Report Type Constants (moved here)
REPORT_TYPE_DEPT_SUMMARY = "Department Summary"
REPORT_TYPE_SALARY_DIST = "Salary Distribution"
REPORT_TYPE_DEPT_STATS = "Department Statistics (Headcount & Person-Days)"
REPORT_TYPE_SALARY_DIST_BY_DEPT = "Salary Distribution by Department" # New Report Type
REPORT_TYPE_AVG_EMP_PERFORMANCE = "Average Employee Performance"
REPORT_TYPE_EMP_PERFORMANCE_EVAL = "Employee Performance Evaluation (Detailed)"

class ReportsWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title_key = "reports_window_title"
        self.title(_(self.title_key))
        self.geometry("950x700")
        self.translatable_widgets_reports = []

        self.report_params: Dict[str, Any] = {}
        self.current_report_data: List[Dict[str, Any]] = []
        self.current_report_col_config: Dict[str, Dict[str, Any]] = {}

        # --- Main Frames ---
        controls_frame = ttk.Frame(self, padding="10")
        controls_frame.pack(side="top", fill="x")

        display_lf_key = "reports_display_lf_title"
        self.report_display_frame = ttk.LabelFrame(self, text=_(display_lf_key), padding="10")
        self.report_display_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(0,10))
        self._add_translatable_widget(self.report_display_frame, display_lf_key, attr="title")

        # --- Controls ---
        select_lf_key = "reports_select_report_lf_title"
        report_select_lf = ttk.LabelFrame(controls_frame, text=_(select_lf_key), padding="5")
        report_select_lf.pack(side="left", padx=(0,10), fill="y")
        self._add_translatable_widget(report_select_lf, select_lf_key, attr="title")

        report_type_lbl_key = "reports_select_report_type_label"
        report_type_label = ttk.Label(report_select_lf, text=_(report_type_lbl_key))
        report_type_label.pack(side="top", anchor="w", padx=5, pady=(0,2))
        self._add_translatable_widget(report_type_label, report_type_lbl_key)

        self.report_type_var = tk.StringVar()
        self.report_combo = ttk.Combobox(
            report_select_lf,
            textvariable=self.report_type_var,
            values=[
                _(REPORT_TYPE_DEPT_SUMMARY), _(REPORT_TYPE_SALARY_DIST),
                _(REPORT_TYPE_DEPT_STATS), _(REPORT_TYPE_SALARY_DIST_BY_DEPT), # Added new report
                _(REPORT_TYPE_AVG_EMP_PERFORMANCE),
                _(REPORT_TYPE_EMP_PERFORMANCE_EVAL)
            ],
            state="readonly",
            width=30 # Increased width
        )
        self.report_combo.pack(side="top", fill="x", padx=5, pady=(0,5))
        self.report_combo.bind("<<ComboboxSelected>>", self._on_report_type_change)
        if self.report_combo['values']:
            self.report_combo.current(0)

        # --- Parameters Frame (for specific reports) ---
        params_lf_key = "reports_parameters_lf_title"
        self.params_lf = ttk.LabelFrame(controls_frame, text=_(params_lf_key), padding="5")
        self.params_lf.pack(side="left", padx=10, fill="both", expand=True)
        self._add_translatable_widget(self.params_lf, params_lf_key, attr="title")

        # General Period Filter Widgets
        self.report_period_start_label = ttk.Label(self.params_lf, text=_("dashboard_from_date_label"))
        self.report_period_start_entry = DateEntry(self.params_lf, width=12, dateformat='%Y-%m-%d')
        self.report_period_start_entry.date = dt_date.today().replace(day=1) - timedelta(days=60)

        self.report_period_end_label = ttk.Label(self.params_lf, text=_("dashboard_to_date_label"))
        self.report_period_end_entry = DateEntry(self.params_lf, width=12, dateformat='%Y-%m-%d')
        self.report_period_end_entry.date = dt_date.today()

        # Salary Distribution Params
        self.salary_dist_bins_label_key = "reports_num_bins_label"
        self.salary_dist_bins_label = ttk.Label(self.params_lf, text=_(self.salary_dist_bins_label_key))
        self.salary_dist_bins_var = tk.StringVar(value="5")
        self.salary_dist_bins_spinbox = ttk.Spinbox(self.params_lf, from_=2, to=20, textvariable=self.salary_dist_bins_var, width=5)

        # Employee Performance Evaluation Params
        self.perf_eval_emp_label = ttk.Label(self.params_lf, text=_("report_select_employee_label"))
        self.perf_eval_emp_var = tk.StringVar()
        self.perf_eval_emp_combo = ttk.Combobox(self.params_lf, textvariable=self.perf_eval_emp_var, state="readonly", width=25)

        self.perf_eval_period_label = ttk.Label(self.params_lf, text=_("report_eval_period_label"))
        self.perf_eval_period_var = tk.StringVar(value="Latest")
        self.perf_eval_period_entry = ttk.Entry(self.params_lf, textvariable=self.perf_eval_period_var, width=15)

        self._populate_perf_eval_employee_dropdown()
        self._on_report_type_change() # Initial setup of params visibility

        # --- Action Buttons ---
        action_buttons_frame = ttk.Frame(controls_frame)
        action_buttons_frame.pack(side="left", fill="y", padx=(10,0))

        generate_btn_key = "reports_generate_button"
        self.generate_report_btn = ttk.Button(action_buttons_frame, text=_(generate_btn_key), command=self._gui_generate_report, bootstyle=PRIMARY)
        self.generate_report_btn.pack(side="top", pady=2, fill="x")
        self._add_translatable_widget(self.generate_report_btn, generate_btn_key)

        export_csv_btn_key = "reports_export_csv_button"
        self.export_csv_btn = ttk.Button(action_buttons_frame, text=_(export_csv_btn_key), command=self._gui_export_to_csv, state="disabled", bootstyle=SUCCESS)
        self.export_csv_btn.pack(side="top", pady=2, fill="x")
        self._add_translatable_widget(self.export_csv_btn, export_csv_btn_key)

        export_pdf_btn_key = "reports_export_pdf_button"
        self.export_pdf_btn = ttk.Button(action_buttons_frame, text=_(export_pdf_btn_key), command=self._gui_export_to_pdf, state="disabled", bootstyle=INFO)
        self.export_pdf_btn.pack(side="top", pady=2, fill="x")
        self._add_translatable_widget(self.export_pdf_btn, export_pdf_btn_key)

        # --- Report Display Area (Treeview) ---
        self.report_tree = ttk.Treeview(self.report_display_frame, show="headings")
        self.report_tree.pack(side="left", fill="both", expand=True)
        report_scrollbar_y = ttk.Scrollbar(self.report_display_frame, orient="vertical", command=self.report_tree.yview)
        self.report_tree.configure(yscrollcommand=report_scrollbar_y.set)
        report_scrollbar_y.pack(side="right", fill="y")
        report_scrollbar_x = ttk.Scrollbar(self.report_display_frame, orient="horizontal", command=self.report_tree.xview, bootstyle="secondary-round")
        self.report_tree.configure(xscrollcommand=report_scrollbar_x.set)
        report_scrollbar_x.pack(side="bottom", fill="x")

        self.refresh_ui_for_language() # Initial translation

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_reports.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_(self.title_key))
        for item_info in self.translatable_widgets_reports:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")
            if widget.winfo_exists():
                try:
                    if attr_to_update == "text": widget.config(text=_(key))
                    elif attr_to_update == "title": widget.config(text=_(key))
                except tk.TclError: pass

        # Update Combobox values (since they are translated strings)
        current_selection_key = self.report_type_var.get() # This will be the translated string
        new_values = [
            _(REPORT_TYPE_DEPT_SUMMARY), _(REPORT_TYPE_SALARY_DIST),
            _(REPORT_TYPE_DEPT_STATS), _(REPORT_TYPE_AVG_EMP_PERFORMANCE),
            _(REPORT_TYPE_EMP_PERFORMANCE_EVAL),
            _(REPORT_TYPE_SALARY_DIST_BY_DEPT)
        ]
        self.report_combo['values'] = new_values
        # Try to reselect based on the key if possible, or default
        # This is tricky because current_selection_key is already translated.
        # A better way would be to store the original key and re-translate.
        # For now, let's just set to the first if the old value isn't in new_values.
        try:
            self.report_combo.current(new_values.index(current_selection_key))
        except ValueError:
            if new_values: self.report_combo.current(0)

        # Update parameter labels
        if hasattr(self, 'salary_dist_bins_label'): self.salary_dist_bins_label.config(text=_(self.salary_dist_bins_label_key))
        if hasattr(self, 'perf_eval_emp_label'): self.perf_eval_emp_label.config(text=_("report_select_employee_label"))
        if hasattr(self, 'perf_eval_period_label'): self.perf_eval_period_label.config(text=_("report_eval_period_label"))
        if hasattr(self, 'report_period_start_label'): self.report_period_start_label.config(text=_("dashboard_from_date_label"))
        if hasattr(self, 'report_period_end_label'): self.report_period_end_label.config(text=_("dashboard_to_date_label"))

        # Refresh treeview headers if data exists
        if self.current_report_col_config:
            self._setup_report_treeview_columns(self.current_report_col_config, retranslate_headers=True)

    def _populate_perf_eval_employee_dropdown(self):
        try:
            employees = db_queries.get_all_employees_db(include_archived=False) # Get active employees
            emp_list = [f"{emp[db_schema.COL_EMP_NAME]} ({emp[db_schema.COL_EMP_ID]})" for emp in employees]
            self.perf_eval_emp_combo['values'] = emp_list
            if emp_list:
                self.perf_eval_emp_combo.current(0)
        except Exception as e:
            logger.error(f"Failed to populate employee dropdown for perf eval report: {e}")

    def _on_report_type_change(self, event=None):
        # Hide all parameter widgets first
        for widget in self.params_lf.winfo_children():
            widget.pack_forget()

        selected_report_display_name = self.report_type_var.get()
        # Map display name back to constant key
        report_map = {
            _(REPORT_TYPE_DEPT_SUMMARY): REPORT_TYPE_DEPT_SUMMARY,
            _(REPORT_TYPE_SALARY_DIST): REPORT_TYPE_SALARY_DIST,
            _(REPORT_TYPE_DEPT_STATS): REPORT_TYPE_DEPT_STATS,
            _(REPORT_TYPE_SALARY_DIST_BY_DEPT): REPORT_TYPE_SALARY_DIST_BY_DEPT,
            _(REPORT_TYPE_AVG_EMP_PERFORMANCE): REPORT_TYPE_AVG_EMP_PERFORMANCE, # Keep this line
            _(REPORT_TYPE_EMP_PERFORMANCE_EVAL): REPORT_TYPE_EMP_PERFORMANCE_EVAL
        }
        selected_report = report_map.get(selected_report_display_name)

        if selected_report == REPORT_TYPE_SALARY_DIST:
            self.salary_dist_bins_label.pack(side="left", padx=(0,2))
            self.salary_dist_bins_spinbox.pack(side="left")
        elif selected_report == REPORT_TYPE_EMP_PERFORMANCE_EVAL:
            self.perf_eval_emp_label.pack(side="left", padx=(0,2))
            self.perf_eval_emp_combo.pack(side="left", padx=(0,5))
            self.perf_eval_period_label.pack(side="left", padx=(5,2))
            self.perf_eval_period_entry.pack(side="left")
        elif selected_report in [REPORT_TYPE_AVG_EMP_PERFORMANCE, REPORT_TYPE_SALARY_DIST_BY_DEPT]: # Show period for these
            self.report_period_start_label.pack(side="left", padx=(0,2))
            self.report_period_start_entry.pack(side="left", padx=(0,5))
            self.report_period_end_label.pack(side="left", padx=(5,2))
            self.report_period_end_entry.pack(side="left")

    def _gui_generate_report(self):
        selected_report_display_name = self.report_type_var.get()
        report_map = {
            _(REPORT_TYPE_DEPT_SUMMARY): REPORT_TYPE_DEPT_SUMMARY,
            _(REPORT_TYPE_SALARY_DIST): REPORT_TYPE_SALARY_DIST,
            _(REPORT_TYPE_DEPT_STATS): REPORT_TYPE_DEPT_STATS,
            _(REPORT_TYPE_SALARY_DIST_BY_DEPT): REPORT_TYPE_SALARY_DIST_BY_DEPT,
            _(REPORT_TYPE_AVG_EMP_PERFORMANCE): REPORT_TYPE_AVG_EMP_PERFORMANCE, # Keep this line
            _(REPORT_TYPE_EMP_PERFORMANCE_EVAL): REPORT_TYPE_EMP_PERFORMANCE_EVAL
        }
        selected_report = report_map.get(selected_report_display_name)

        if not selected_report:
            messagebox.showerror(_("error_title"), "Please select a valid report type.", parent=self) # TODO: Translate
            return

        self.report_params = {
            "report_type": selected_report,
            "num_bins": int(self.salary_dist_bins_var.get()) if selected_report == REPORT_TYPE_SALARY_DIST else None,
            "employee_id": extract_id_from_combobox_selection(self.perf_eval_emp_var.get()) if selected_report == REPORT_TYPE_EMP_PERFORMANCE_EVAL else None,
            "evaluation_period": self.perf_eval_period_var.get() if selected_report == REPORT_TYPE_EMP_PERFORMANCE_EVAL else None,
            "period_start": self.report_period_start_entry.entry.get() if selected_report in [REPORT_TYPE_AVG_EMP_PERFORMANCE, REPORT_TYPE_SALARY_DIST_BY_DEPT] else None,
            "period_end": self.report_period_end_entry.entry.get() if selected_report in [REPORT_TYPE_AVG_EMP_PERFORMANCE, REPORT_TYPE_SALARY_DIST_BY_DEPT] else None,
        }

        thread = threading.Thread(target=self._perform_report_generation_threaded,
                                  args=(self.report_params,), daemon=True)
        thread.start()
        self.config(cursor="watch")
        self.generate_report_btn.config(state="disabled")

    def _perform_report_generation_threaded(self, report_params: Dict):
        try:
            report_type = report_params["report_type"]
            data_for_report: List[Dict[str, Any]] = []
            col_conf_for_report: Dict[str, Dict[str, Any]] = {}

            if report_type == REPORT_TYPE_DEPT_SUMMARY:
                col_conf_for_report = {
                    db_schema.COL_DEPT_NAME: {"header": _("header_emp_department"), "width": 200, "stretch": tk.YES},
                    "employee_count": {"header": _("reports_col_employee_count"), "width": 150, "anchor": "e"},
                    "average_salary": {"header": _("reports_col_avg_salary"), "width": 150, "anchor": "e"}
                }
                raw_data = db_queries.get_department_summary_report()
                for row in raw_data:
                    data_for_report.append({
                        db_schema.COL_DEPT_NAME: row[db_schema.COL_DEPT_NAME],
                        "employee_count": row["employee_count"],
                        "average_salary": f"{row['average_salary']:.2f}" if row['average_salary'] is not None else "N/A"
                    })
            elif report_type == REPORT_TYPE_SALARY_DIST: # Added colon here
                # This report generates a plot, not tabular data for the treeview directly
                num_bins = report_params.get("num_bins", 5)
                plot_path = db_queries.get_salary_distribution_report(num_bins) # This function needs to save a plot
                # For now, let's assume it returns a path or some indicator
                # We'll show a message instead of populating treeview
                data_for_report = [{"status": f"Salary distribution plot generated: {plot_path}"}] # TODO: Translate
                col_conf_for_report = {"status": {"header": "Status", "width": 400, "stretch": tk.YES}} # TODO: Translate

            elif report_type == REPORT_TYPE_DEPT_STATS: # Added colon
                col_conf_for_report = {
                    db_schema.COL_DEPT_NAME: {"header": _("header_emp_department"), "width": 200, "stretch": tk.YES},
                    "headcount": {"header": _("reports_col_employee_count"), "width": 150, "anchor": "e"},
                    "total_person_days": {"header": _("reports_col_total_hours"), "width": 150, "anchor": "e"} # Assuming person-days
                }
                raw_data = db_queries.get_department_statistics_report()
                for row in raw_data:
                    data_for_report.append(dict(row))

            elif report_type == REPORT_TYPE_EMP_PERFORMANCE_EVAL: # Added colon
                emp_id_param = report_params.get("employee_id")
                eval_period_param = report_params.get("evaluation_period")
                if not emp_id_param:
                    raise ValueError(_("report_select_employee_label")) # Re-use label as error

                col_conf_for_report = {
                    db_schema.COL_EVAL_PERIOD: {"header": _("report_header_eval_period"), "width": 100},
                    db_schema.COL_EVAL_DATE: {"header": _("report_header_eval_date"), "width": 100},
                    "evaluator_name": {"header": _("report_header_evaluator"), "width": 150},
                    "criterion_name": {"header": _("report_header_criteria"), "width": 200, "stretch": tk.YES},
                    db_schema.COL_EVAL_DETAIL_SCORE: {"header": _("report_header_score"), "width": 70, "anchor": "e"},
                    "criterion_max_points": {"header": _("report_header_max_points"), "width": 70, "anchor": "e"},
                    db_schema.COL_EVAL_DETAIL_COMMENT: {"header": _("report_header_comment"), "width": 250},
                    "overall_score": {"header": _("report_header_overall_score"), "width":100, "anchor":"e"},
                    "overall_notes": {"header": _("report_header_overall_notes"), "width":250}
                }
                data_for_report = db_queries.get_employee_performance_evaluation_report(emp_id_param, eval_period_param)

            elif report_type == REPORT_TYPE_AVG_EMP_PERFORMANCE: # Added colon
                period_start = report_params.get("period_start")
                period_end = report_params.get("period_end")
                col_conf_for_report = {
                    "employee_id": {"header": _("header_emp_id"), "width": 100},
                    "employee_name": {"header": _("header_emp_name"), "width": 200, "stretch": tk.YES},
                    "average_score": {"header": _("report_header_avg_score"), "width": 150, "anchor": "e"},
                    "evaluation_count": {"header": _("report_header_eval_count"), "width": 150, "anchor": "e"}
                }
                raw_data = db_queries.get_average_performance_by_employee_db(period_start, period_end)
                for row in raw_data:
                    data_for_report.append({
                        "employee_id": row["employee_id"],
                        "employee_name": row["employee_name"],
                        "average_score": f"{row['average_score']:.2f}" if row['average_score'] is not None else "N/A",
                        "evaluation_count": row["evaluation_count"]
                    })
            elif report_type == REPORT_TYPE_SALARY_DIST_BY_DEPT:
                # period_start = report_params.get("period_start") # Not used by current backend function for this report
                # period_end = report_params.get("period_end")
                col_conf_for_report = {
                    "department_name": {"header": _("header_emp_department"), "width": 200, "stretch": tk.YES},
                    "min_salary": {"header": _("reports_min_salary_header"), "width": 120, "anchor": "e"},
                    "max_salary": {"header": _("reports_max_salary_header"), "width": 120, "anchor": "e"},
                    "avg_salary": {"header": _("reports_col_avg_salary"), "width": 120, "anchor": "e"}, # Reusing key
                    "employee_count": {"header": _("reports_col_employee_count"), "width": 120, "anchor": "e"} # Reusing key
                }
                raw_data = db_queries.get_salary_distribution_by_department_report_db()
                for row in raw_data:
                    data_for_report.append({
                        "department_name": row.get("department_name", "Unassigned"),
                        "min_salary": f"{row.get('min_salary', 0.0):,.2f}",
                        "max_salary": f"{row.get('max_salary', 0.0):,.2f}",
                        "avg_salary": f"{row.get('avg_salary', 0.0):,.2f}",
                        "employee_count": row.get("employee_count", 0)
                    })
            else:
                raise ValueError(f"Unknown report type: {report_type}")

            self.current_report_data = data_for_report
            self.current_report_col_config = col_conf_for_report
            self.after(0, self._update_report_display)

        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror(_("reports_generation_error", error_message=str(e)), parent=self))
        finally:
            self.after(0, lambda: self.config(cursor=""))
            self.after(0, lambda: self.generate_report_btn.config(state="normal"))
            self.after(0, lambda: self.export_csv_btn.config(state="normal" if self.current_report_data else "disabled"))
            self.after(0, lambda: self.export_pdf_btn.config(state="normal" if self.current_report_data else "disabled"))

    def _update_report_display(self):
        clear_treeview(self.report_tree)
        if not self.current_report_data:
            # Optionally show a "No data" message in the tree or a label
            return

        self._setup_report_treeview_columns(self.current_report_col_config)

        for row_data in self.current_report_data:
            values = [row_data.get(col_id, "") for col_id in self.current_report_col_config.keys()]
            self.report_tree.insert("", "end", values=values)

    def _setup_report_treeview_columns(self, column_config: Dict[str, Dict[str, Any]], retranslate_headers: bool = False):
        """Configures or reconfigures the report Treeview columns."""
        current_cols = self.report_tree["columns"]
        if not retranslate_headers and list(current_cols) == list(column_config.keys()):
            # Columns are already set up and we are not retranslating, so skip
            # This check might be too simple if order can change but keys remain same.
            # For retranslation, we always proceed.
            pass

        self.report_tree["columns"] = list(column_config.keys())
        for col_id, conf in column_config.items():
            header_text = _(conf["header"]) if conf.get("header") else col_id.replace("_", " ").title()
            self.report_tree.heading(col_id, text=header_text, anchor=conf.get("anchor", "w"))
            self.report_tree.column(col_id, width=conf.get("width", 100), stretch=conf.get("stretch", tk.NO), anchor=conf.get("anchor", "w"))

    def _gui_export_to_csv(self):
        if not self.current_report_data or not self.current_report_col_config:
            messagebox.showwarning(_("info_title"), "No report data to export.", parent=self) # TODO: Translate
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title=_("reports_save_csv_dialog_title")
        )
        if not filepath:
            return

        try:
            headers = [_(conf.get("header", col_id)) for col_id, conf in self.current_report_col_config.items()]
            with open(filepath, "w", newline="", encoding="utf-8-sig") as csvfile: # utf-8-sig for Excel compatibility
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                for row_data in self.current_report_data:
                    row_values = [row_data.get(col_id, "") for col_id in self.current_report_col_config.keys()]
                    writer.writerow(row_values)
            messagebox.showinfo(_("success_title"), f"Report exported to CSV: {filepath}", parent=self) # TODO: Translate
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {e}", exc_info=True)
            messagebox.showerror(_("error_title"), f"Failed to export to CSV: {e}", parent=self) # TODO: Translate

    def _gui_export_to_pdf(self):
        if not self.current_report_data or not self.current_report_col_config:
            messagebox.showwarning(_("info_title"), "No report data to export.", parent=self) # TODO: Translate
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[(_("pdf_file_type_label"), "*.pdf"), ("All files", "*.*")],
            title=_("reports_save_pdf_dialog_title")
        )
        if not filepath:
            return

        try:
            report_title = self.report_type_var.get()
            headers = [_(conf.get("header", col_id)) for col_id, conf in self.current_report_col_config.items()]
            data_for_pdf = [[row_data.get(col_id, "") for col_id in self.current_report_col_config.keys()] for row_data in self.current_report_data]
            
            pdf_utils.generate_professional_pdf_report(data_for_pdf, headers, None, report_title, filepath) # Corrected function name and arguments
            messagebox.showinfo(_("success_title"), f"Report exported to PDF: {filepath}", parent=self) # TODO: Translate
        except Exception as e:
            logger.error(f"Error exporting report to PDF: {e}", exc_info=True)
            messagebox.showerror(_("error_title"), f"Failed to export to PDF: {e}", parent=self) # TODO: Translate

    def update_local_theme_elements(self):
        super().update_local_theme_elements()
        # Add any specific non-ttk widget theming here if needed
        pass