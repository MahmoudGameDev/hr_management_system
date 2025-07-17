# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\advanced_search_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
import logging
from datetime import datetime
from ui.employee_profile_window import EmployeeProfileWindow # Import EmployeeProfileWindow

# --- Project-specific imports ---
from data import database as db_schema # For COL_... constants
from data import queries as db_queries # For search_employees, list_departments_db
from utils import localization # For _()
from utils.exceptions import DatabaseOperationError # Import DatabaseOperationError
from .themed_toplevel import ThemedToplevel
from .components import AutocompleteCombobox # For department selection
from .employee_form_window import EmployeeFormWindow # To open profile

logger = logging.getLogger(__name__)

class AdvancedSearchWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("advanced_search_window_title"))
        self.title(localization._("adv_search_window_title"))
        self.geometry("950x750") # Adjusted size
        self.translatable_widgets_adv_search = []

        # --- Criteria Frame ---
        criteria_lf_key = "adv_search_criteria_frame_title"
        criteria_frame = ttk.LabelFrame(self, text=localization._(criteria_lf_key), padding="10")
        criteria_frame.pack(side="top", fill="x", padx=10, pady=10)
        self._add_translatable_widget(criteria_frame, criteria_lf_key, attr="title")

        # Store widgets for criteria
        self.adv_search_widgets = {}
        self.adv_criteria_vars = {} # To store StringVars for fields

        adv_fields = [
            ("adv_search_name_label", db_schema.COL_EMP_NAME, "entry"),
            ("adv_search_dept_label", "department_name", "dept_combo"), # Special key for department name
            ("adv_search_position_label", db_schema.COL_EMP_POSITION, "entry"),
            ("adv_search_status_label", db_schema.COL_EMP_STATUS, "status_combo"),
            ("adv_search_start_date_from_label", "start_date_from", "date_entry"),
            ("adv_search_start_date_to_label", "start_date_to", "date_entry"),
            ("adv_search_salary_from_label", "salary_from", "entry"),
            ("adv_search_salary_to_label", "salary_to", "entry"),
            ("adv_search_email_label", db_schema.COL_EMP_EMAIL, "entry"),
            ("adv_search_phone_label", db_schema.COL_EMP_PHONE, "entry"),
            ("adv_search_marital_status_label", db_schema.COL_EMP_MARITAL_STATUS, "entry"),
            ("adv_search_education_label", db_schema.COL_EMP_EDUCATION, "entry"),
            ("adv_search_termination_date_from_label", "termination_date_from", "date_entry"),
            ("adv_search_termination_date_to_label", "termination_date_to", "date_entry"),
            ("search_gender_label", db_schema.COL_EMP_GENDER, "gender_combo"), # Added Gender
        ]

        grid_col_count = 2
        for i, (label_key, data_key, widget_type) in enumerate(adv_fields):
            row = i // grid_col_count
            col_label = (i % grid_col_count) * 2
            col_widget = col_label + 1

            lbl = ttk.Label(criteria_frame, text=localization._(label_key))
            lbl.grid(row=row, column=col_label, sticky="w", padx=5, pady=3)
            self._add_translatable_widget(lbl, label_key)

            if widget_type == "entry": # No change needed here
                var = tk.StringVar()
                widget = ttk.Entry(criteria_frame, textvariable=var, width=25)
                self.adv_criteria_vars[data_key] = var
            elif widget_type == "dept_combo":
                var = tk.StringVar()
                widget = AutocompleteCombobox(criteria_frame, textvariable=var, width=23)
                self._populate_adv_search_dept_combo(widget, is_autocomplete=True)
                self.adv_criteria_vars[data_key] = var
            elif widget_type == "status_combo":
                var = tk.StringVar()
                widget = ttk.Combobox(criteria_frame, textvariable=var, values=["", "Active", "Terminated"], state="readonly", width=23)
                self.adv_criteria_vars[data_key] = var
            elif widget_type == "date_entry":
                widget = DateEntry(criteria_frame, width=23, dateformat='%Y-%m-%d')
                widget.entry.delete(0, tk.END) # Clear default date
            elif widget_type == "gender_combo": # New widget type for Gender
                var = tk.StringVar()
                widget = ttk.Combobox(criteria_frame, textvariable=var, state="readonly", width=23)
                # Values will be set in refresh_ui_for_language
                self.adv_criteria_vars[data_key] = var

            if widget:
                widget.grid(row=row, column=col_widget, sticky="ew", padx=5, pady=3)
                self.adv_search_widgets[data_key] = widget

        criteria_frame.columnconfigure(1, weight=1)
        criteria_frame.columnconfigure(3, weight=1)

        # --- Search and Clear Buttons ---
        search_buttons_frame = ttk.Frame(self)
        search_buttons_frame.pack(fill="x", padx=10, pady=5)

        # Clear Button
        clear_btn_key = "adv_search_clear_button"
        self.clear_button_adv_search = ttk.Button(search_buttons_frame, text=localization._(clear_btn_key), command=self._gui_clear_search_criteria, bootstyle=db_schema.BS_LIGHT)
        self.clear_button_adv_search.pack(side="left", padx=5)
        self._add_translatable_widget(self.clear_button_adv_search, clear_btn_key)

        # Search Button
        search_btn_key = "adv_search_button"
        self.execute_search_button = ttk.Button(search_buttons_frame, text=localization._(search_btn_key), command=self._gui_execute_advanced_search, bootstyle=db_schema.BS_PRIMARY_ACTION)
        self.execute_search_button.pack(side="right", padx=5)
        self._add_translatable_widget(self.execute_search_button, search_btn_key)

        # --- Results Frame ---
        results_lf_key = "adv_search_results_frame_title"
        results_frame = ttk.LabelFrame(self, text=localization._(results_lf_key), padding="10")
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._add_translatable_widget(results_frame, results_lf_key, attr="title")

        results_cols = (db_schema.COL_EMP_ID, db_schema.COL_EMP_NAME, "department_name", db_schema.COL_EMP_POSITION, db_schema.COL_EMP_STATUS)
        self.adv_search_results_tree = ttk.Treeview(results_frame, columns=results_cols, show="headings")
        # Headers will be set in refresh_ui_for_language
        self._update_adv_search_tree_headers()

        for col_id in results_cols:
            # Default width, can be overridden below
            width = 100
            if col_id == db_schema.COL_EMP_NAME: width = 150
            elif col_id == "department_name": width = 120
            elif col_id == db_schema.COL_EMP_POSITION: width = 120
            self.adv_search_results_tree.column(col_id, width=width, anchor="w", stretch=tk.YES)

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.adv_search_results_tree.yview)
        self.adv_search_results_tree.configure(yscrollcommand=scrollbar.set)
        self.adv_search_results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.adv_search_results_tree.bind("<Double-1>", self._gui_view_profile_from_adv_search)
        # Populate gender combobox after it's created
        self._populate_adv_search_gender_combo(self.adv_search_widgets[db_schema.COL_EMP_GENDER])

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_adv_search.append({"widget": widget, "key": key, "attr": attr})

    def _update_adv_search_tree_headers(self):
        if hasattr(self, 'adv_search_results_tree') and self.adv_search_results_tree.winfo_exists():
            self.adv_search_results_tree.heading(db_schema.COL_EMP_ID, text=localization._("header_emp_id"))
            self.adv_search_results_tree.heading(db_schema.COL_EMP_NAME, text=localization._("header_emp_name"))
            self.adv_search_results_tree.heading("department_name", text=localization._("header_emp_department"))
            self.adv_search_results_tree.heading(db_schema.COL_EMP_POSITION, text=localization._("header_emp_position"))
            self.adv_search_results_tree.heading(db_schema.COL_EMP_STATUS, text=localization._("header_emp_status"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("advanced_search_window_title"))
        self._update_adv_search_tree_headers()
        for item in self.translatable_widgets_adv_search:
            widget, key, attr = item["widget"], item["key"], item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text": widget.config(text=localization._(key))
                    elif attr == "title": widget.config(text=localization._(key))
                except tk.TclError: pass

    # Placeholder methods for functionality (to be copied from HRAppGUI and adapted)
    def _populate_adv_search_gender_combo(self, combo_widget):
        gender_options = [
            localization._("gender_option_all"), localization._("gender_option_male"),
            localization._("gender_option_female"), localization._("gender_option_other")
        ]
        combo_widget['values'] = gender_options
        combo_widget.set(localization._("gender_option_all")) # Default to "All"

    def _gui_perform_advanced_search(self, is_initial_load: bool = False):
        criteria: Dict[str, Any] = {}
        has_non_archived_criteria = False # Track if any criteria *other than* include_archived are present

    def _populate_adv_search_dept_combo(self, combo_widget, is_autocomplete=False):
        """Populates the department combobox in the advanced search view with names."""
        try:
            departments = db_queries.get_all_departments_db() # Corrected function name
            dept_names = [dept.get(db_schema.COL_DEPT_NAME, "N/A") for dept in departments] # Use .get() for safety
            
            # Add an option for "All Departments" or an empty selection
            empty_option_text = localization._("adv_search_all_departments_option", default="All Departments") # Add new key
            options = [empty_option_text] + dept_names

            if is_autocomplete and hasattr(combo_widget, 'set_completion_list'):
                combo_widget.set_completion_list(options)
            else: # Fallback for standard combobox
                combo_widget['values'] = options
            
            combo_widget.set(empty_option_text) # Default to "All Departments"
        except db_queries.DatabaseOperationError as e: # Corrected exception import
            logger.error(f"DB Error populating department combo in advanced search: {e}")
            messagebox.showerror(localization._("db_error_title"), localization._("contract_error_loading_list", error=e), parent=self) # Reusing key
            if hasattr(combo_widget, 'set_completion_list'):
                combo_widget.set_completion_list([])
            else:
                combo_widget['values'] = []
            combo_widget.set("Error loading")

    def _gui_clear_search_criteria(self):
        """Clears all search criteria fields and the results tree."""
        for key, var in self.adv_criteria_vars.items():
            var.set("")
        
        for key, widget in self.adv_search_widgets.items():
            if isinstance(widget, DateEntry):
                widget.entry.delete(0, tk.END)
            elif isinstance(widget, AutocompleteCombobox): # Specifically reset AutocompleteCombobox
                if key == "department_name": # If it's the department combobox
                    self._populate_adv_search_dept_combo(widget, is_autocomplete=True) # Repopulate and set default
                # No specific reset for gender_combo here as its StringVars is cleared by the loop above,
                
                else:
                    widget.set("") # Clear other AutocompleteComboboxes
            elif key == db_schema.COL_EMP_GENDER and isinstance(widget, ttk.Combobox): # Handle gender combobox
                widget.set(localization._("gender_option_all"))

            # StringVars linked to Entries and standard Comboboxes are cleared by the loop above

        # Clear results tree
        for item in self.adv_search_results_tree.get_children():
            self.adv_search_results_tree.delete(item)
        logger.debug("Advanced search criteria and results cleared.")

    def _gui_execute_advanced_search(self):
        """Collects criteria and executes the advanced search."""
        criteria = {}
        

        for key, var in self.adv_criteria_vars.items():
            value = var.get().strip()
            if value and value != localization._("adv_search_all_departments_option", default="All Departments") and value != localization._("gender_option_all"): # Exclude "All" options
                if key == "department_name" and value == localization._("contract_filter_all_departments"):
                    continue 
                if key == db_schema.COL_EMP_STATUS and not value: # Skip empty status selection
                    continue
                if key == db_schema.COL_EMP_GENDER: # Handle gender filter
                    if value == localization._("gender_option_all"):
                        continue # Skip "All" for gender
                    # Map translated UI value back to DB value if necessary
                    if value == localization._("gender_option_male"): criteria[key] = "Male"
                    elif value == localization._("gender_option_female"): criteria[key] = "Female"
                    elif value == localization._("gender_option_other"): criteria[key] = "Other"
                    continue
                criteria[key] = value
                

        for key, widget in self.adv_search_widgets.items():
            if isinstance(widget, DateEntry):
                value = widget.entry.get().strip()
                if value:
                    try:
                        datetime.strptime(value, '%Y-%m-%d') # Validate date format
                        criteria[key] = value
                        
                    except ValueError:
                        messagebox.showerror(localization._("input_error_title"), localization._("invalid_date_format_yyyy_mm_dd_error", field=key.replace("_", " ").title()), parent=self)
                        return
            # Other widget types like Entry/Combobox are handled by adv_criteria_vars

        if not criteria: # Check if the criteria dictionary is empty
            messagebox.showinfo(localization._("info_title"), localization._("adv_search_no_criteria_message"), parent=self)
            # Optionally load all employees or clear results
            # self._gui_clear_search_criteria() # Or load all
            return

        try:
            results = db_queries.advanced_search_employees_db(criteria)
            # Clear previous results
            for item in self.adv_search_results_tree.get_children():
                self.adv_search_results_tree.delete(item)
            
            if results:
                for emp in results:
                    self.adv_search_results_tree.insert("", "end", values=(
                        emp.get(db_schema.COL_EMP_ID, ""), emp.get(db_schema.COL_EMP_NAME, ""),
                        emp.get("department_name", "N/A"), emp.get(db_schema.COL_EMP_POSITION, ""),
                        emp.get(db_schema.COL_EMP_STATUS, "")
                    ))
            else:
                messagebox.showinfo(localization._("info_title"), localization._("adv_search_no_results_message"), parent=self)
        except (db_queries.DatabaseOperationError, InvalidInputError) as e:
            messagebox.showerror(localization._("db_error_title"), localization._("adv_search_db_error", error=e), parent=self)
        except Exception as e_gen:
            logger.error(f"Unexpected error during advanced search: {e_gen}", exc_info=True)
            messagebox.showerror(localization._("unexpected_error_title"), localization._("unexpected_error_occurred_message", error=e_gen), parent=self)

    def _gui_view_profile_from_adv_search(self, event=None):
        selected_item_iid = self.adv_search_results_tree.focus()
        if not selected_item_iid:
            return
        
        item_values = self.adv_search_results_tree.item(selected_item_iid, "values")
        if not item_values:
            return
            
        emp_id_to_view = item_values[0] # Assuming Employee ID is the first column

        # Use ApplicationController's method to open the EmployeeFormWindow
        # Pass view_only=True to open in read-only mode
        self.parent_app._create_and_show_toplevel(
            EmployeeFormWindow,
            employee_id=emp_id_to_view,
            view_only=True, # Open in view-only mode from search results
            tracker_attr_name=f"active_employee_profile_view_{emp_id_to_view}" # Unique tracker
        )