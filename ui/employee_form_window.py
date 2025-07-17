# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\employee_form_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText # If used for notes/history
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk, UnidentifiedImageError
import os
import logging
from datetime import datetime, date as dt_date # For DateEntry or date handling

# --- Project-specific imports ---
import config
from data import database as db_schema
from data import queries as db_queries
from utils import localization
from utils.image_utils import load_and_resize_photo # or other image utils used
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # Added import
from utils.gui_utils import extract_id_from_combobox_selection # Corrected import from gui_utils
from utils.validators import is_valid_email, is_valid_phone 
from .components import AutocompleteCombobox
from .themed_toplevel import ThemedToplevel
# from .components import DateEntry # If you have a custom DateEntry, it would be in ui/components.py
# For PDF parsing
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

# If you use tkcalendar.DateEntry, you'd import it directly:
# from tkcalendar import DateEntry # Example
from typing import Optional, Callable, Dict # Import Callable and Dict

logger = logging.getLogger(__name__)

class EmployeeFormWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, 
                 mode: str = 'add', 
                 employee_id: Optional[str] = None, 
                 view_only: bool = False, 
                 callback_on_save: Optional[Callable] = None):
        super().__init__(parent, app_instance)
        self.parent_app = app_instance # ApplicationController

        # Determine operational mode and set attributes
        if view_only and employee_id:
            self.mode = 'view'
        elif mode == 'edit' and employee_id:
            self.mode = 'edit'
        elif mode == 'add':
            self.mode = 'add'
        else: # Default or fallback logic
            self.mode = 'add' if not employee_id else 'edit'

        self.emp_id_to_edit = employee_id if self.mode in ['edit', 'view'] else None
        self.view_only = (self.mode == 'view') # Final source of truth for view_only
        self.callback_on_save = callback_on_save

        self.current_photo_path = None # To store path of loaded photo
        self.translatable_widgets_form = []
        
        # Initialize dictionaries for input variables and widgets
        self.input_vars: Dict[str, tk.Variable] = {}
        self.input_widgets: Dict[str, tk.Widget] = {}

        # Title logic based on the determined self.mode
        if self.mode == 'view':
            self.title_key = "employee_form_title_view"
        elif self.mode == 'edit':
            self.title_key = "employee_form_title_edit"
        else: # 'add'
            self.title_key = "employee_form_title_add"
        self.title(localization._(self.title_key))
        
        # Adjust geometry as needed
        self.geometry("750x650") # Example size

        # --- Main Frame ---
        main_form_frame = ttkb.Frame(self, padding="15")
        main_form_frame.pack(expand=True, fill="both")

        # Notebook for sections (Personal, Job, etc.)
        self.notebook = ttkb.Notebook(main_form_frame)
        self.notebook.pack(expand=True, fill="both", pady=10)

        # --- Create Tabs ---
        self.personal_info_tab = ttkb.Frame(self.notebook, padding="10")
        self.job_info_tab = ttkb.Frame(self.notebook, padding="10")
        self.additional_info_tab = ttkb.Frame(self.notebook, padding="10") # For photo, notes etc.

        self.notebook.add(self.personal_info_tab, text=localization._("tab_personal_info"))
        self.notebook.add(self.job_info_tab, text=localization._("tab_job_info"))
        self.notebook.add(self.additional_info_tab, text=localization._("tab_additional_info"))
        
        self._add_translatable_tab(self.notebook, 0, "tab_personal_info")
        self._add_translatable_tab(self.notebook, 1, "tab_job_info")
        self._add_translatable_tab(self.notebook, 2, "tab_additional_info")


        # --- Populate Tabs ---
        self._create_personal_info_widgets(self.personal_info_tab)
        self._create_job_info_widgets(self.job_info_tab)
        self._create_additional_info_widgets(self.additional_info_tab)

        # --- Buttons Frame ---
        buttons_frame = ttkb.Frame(main_form_frame, padding=(0, 10, 0, 0))
        buttons_frame.pack(fill="x", side="bottom")

        self.save_btn_key = "save_button"
        self.save_button = ttkb.Button(buttons_frame, text=localization._(self.save_btn_key), command=self._save_employee_data, bootstyle=SUCCESS)
        if not view_only:
            self.save_button.pack(side="right", padx=5)
            self._add_translatable_widget_form(self.save_button, self.save_btn_key)

        self.cancel_btn_key = "cancel_button" if not view_only else "close_button"
        self.cancel_button = ttkb.Button(buttons_frame, text=localization._(self.cancel_btn_key), command=self.destroy, bootstyle=SECONDARY)
        self.cancel_button.pack(side="right", padx=5)
        self._add_translatable_widget_form(self.cancel_button, self.cancel_btn_key)
        
        # Load data or set defaults
        self._initialize_form_data()

        if view_only:
            self._set_view_only_state()
            
        # Ensure focus is set appropriately, e.g., to the first entry field
        # self.name_entry.focus_set() # Example, if name_entry is the first field

        if self.input_widgets.get(db_schema.COL_EMP_NAME):
            self.input_widgets[db_schema.COL_EMP_NAME].focus_set()
        # ThemedToplevel's _deferred_theme_update will call update_local_theme_elements,
        # and we can override update_local_theme_elements to also call refresh_ui_for_language
        # or call it explicitly here if needed after a short delay.

    def _add_translatable_widget_form(self, widget, key, attr="text"):
        self.translatable_widgets_form.append({"widget": widget, "key": key, "attr": attr})

    def _add_translatable_tab(self, notebook, tab_index, key):
        self.translatable_widgets_form.append({"widget": notebook, "key": key, "attr": "tab", "index": tab_index})


    def _create_personal_info_widgets(self, parent_tab):
        parent_tab.columnconfigure(1, weight=1) # Allow entry column to expand
        row_idx = 0

        # Employee ID (Read-only for edit/view, generated for add)
        id_lbl = ttkb.Label(parent_tab, text=localization._("employee_id_label"))
        id_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(id_lbl, "employee_id_label")
        self.input_vars[db_schema.COL_EMP_ID] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_ID] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_ID], state="readonly")
        self.input_widgets[db_schema.COL_EMP_ID].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Name
        name_lbl = ttkb.Label(parent_tab, text=localization._("name_label"))
        name_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(name_lbl, "name_label")
        self.input_vars[db_schema.COL_EMP_NAME] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_NAME] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_NAME])
        self.input_widgets[db_schema.COL_EMP_NAME].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Phone
        phone_lbl = ttkb.Label(parent_tab, text=localization._("phone_icon_label"))
        phone_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(phone_lbl, "phone_icon_label")
        self.input_vars[db_schema.COL_EMP_PHONE] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_PHONE] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_PHONE])
        self.input_widgets[db_schema.COL_EMP_PHONE].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Email
        email_lbl = ttkb.Label(parent_tab, text=localization._("email_icon_label"))
        email_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(email_lbl, "email_icon_label")
        self.input_vars[db_schema.COL_EMP_EMAIL] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_EMAIL] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_EMAIL])
        self.input_widgets[db_schema.COL_EMP_EMAIL].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Gender
        gender_lbl = ttkb.Label(parent_tab, text=localization._("gender_icon_label"))
        gender_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(gender_lbl, "gender_icon_label")
        self.input_vars[db_schema.COL_EMP_GENDER] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_GENDER] = ttkb.Combobox(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_GENDER], state="readonly")
        self.input_widgets[db_schema.COL_EMP_GENDER].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self._populate_gender_combobox() # Populate with translated values
        row_idx += 1

        # Marital Status
        marital_lbl = ttkb.Label(parent_tab, text=localization._("marital_status_icon_label"))
        marital_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(marital_lbl, "marital_status_icon_label")
        self.input_vars[db_schema.COL_EMP_MARITAL_STATUS] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_MARITAL_STATUS] = ttkb.Combobox(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_MARITAL_STATUS], state="readonly")
        self.input_widgets[db_schema.COL_EMP_MARITAL_STATUS].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self._populate_marital_status_combobox() # Populate with translated values
        row_idx += 1

        # Education
        edu_lbl = ttkb.Label(parent_tab, text=localization._("education_icon_label"))
        edu_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(edu_lbl, "education_icon_label")
        self.input_vars[db_schema.COL_EMP_EDUCATION] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_EDUCATION] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_EDUCATION])
        self.input_widgets[db_schema.COL_EMP_EDUCATION].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

    def _create_job_info_widgets(self, parent_tab):
        parent_tab.columnconfigure(1, weight=1)
        row_idx = 0

        # Department
        dept_lbl = ttkb.Label(parent_tab, text=localization._("department_icon_label"))
        dept_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(dept_lbl, "department_icon_label")
        self.input_vars["department_name"] = tk.StringVar() # Store department name for display
        self.input_widgets["department_name"] = AutocompleteCombobox(parent_tab, textvariable=self.input_vars["department_name"])
        self.input_widgets["department_name"].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self.populate_department_combobox()
        row_idx += 1

        # Position
        pos_lbl = ttkb.Label(parent_tab, text=localization._("position_icon_label"))
        pos_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(pos_lbl, "position_icon_label")
        self.input_vars[db_schema.COL_EMP_POSITION] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_POSITION] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_POSITION])
        self.input_widgets[db_schema.COL_EMP_POSITION].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Salary
        salary_lbl = ttkb.Label(parent_tab, text=localization._("salary_icon_label"))
        salary_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(salary_lbl, "salary_icon_label")
        self.input_vars[db_schema.COL_EMP_SALARY] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_SALARY] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_SALARY])
        self.input_widgets[db_schema.COL_EMP_SALARY].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Start Date
        start_date_lbl = ttkb.Label(parent_tab, text=localization._("start_date_icon_label"))
        start_date_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(start_date_lbl, "start_date_icon_label")
        self.input_widgets[db_schema.COL_EMP_START_DATE] = ttkb.DateEntry(parent_tab, dateformat='%Y-%m-%d')
        self.input_widgets[db_schema.COL_EMP_START_DATE].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Status
        status_lbl = ttkb.Label(parent_tab, text=localization._("status_icon_label"))
        status_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(status_lbl, "status_icon_label")
        self.input_vars[db_schema.COL_EMP_STATUS] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_STATUS] = ttkb.Combobox(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_STATUS], state="readonly")
        self.input_widgets[db_schema.COL_EMP_STATUS].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self._populate_status_combobox() # Populate with translated values
        self.input_vars[db_schema.COL_EMP_STATUS].set(db_schema.STATUS_ACTIVE) # Default
        row_idx += 1

        # Manager
        manager_lbl = ttkb.Label(parent_tab, text=localization._("manager_label")) # Add key
        manager_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(manager_lbl, "manager_label")
        self.input_vars["manager_name"] = tk.StringVar() # Store manager name for display
        self.input_widgets["manager_name"] = AutocompleteCombobox(parent_tab, textvariable=self.input_vars["manager_name"])
        self.input_widgets["manager_name"].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self.populate_manager_combobox()
        row_idx += 1

        # Device User ID
        device_id_lbl = ttkb.Label(parent_tab, text=localization._("device_user_id_icon_label"))
        device_id_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(device_id_lbl, "device_user_id_icon_label")
        self.input_vars[db_schema.COL_EMP_DEVICE_USER_ID] = tk.StringVar()
        self.input_widgets[db_schema.COL_EMP_DEVICE_USER_ID] = ttkb.Entry(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_DEVICE_USER_ID])
        self.input_widgets[db_schema.COL_EMP_DEVICE_USER_ID].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Vacation Days
        vac_days_lbl = ttkb.Label(parent_tab, text=localization._("vacation_days_icon_label"))
        vac_days_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(vac_days_lbl, "vacation_days_icon_label")
        self.input_vars[db_schema.COL_EMP_VACATION_DAYS] = tk.StringVar(value="21") # Default
        self.input_widgets[db_schema.COL_EMP_VACATION_DAYS] = ttkb.Spinbox(parent_tab, from_=0, to=100, textvariable=self.input_vars[db_schema.COL_EMP_VACATION_DAYS])
        self.input_widgets[db_schema.COL_EMP_VACATION_DAYS].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        row_idx += 1

        # Exclude Vacation Policy
        exclude_vac_lbl = ttkb.Label(parent_tab, text=localization._("exclude_vacation_policy_icon_label"))
        exclude_vac_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(exclude_vac_lbl, "exclude_vacation_policy_icon_label")
        self.input_vars[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY] = tk.BooleanVar(value=False)
        self.input_widgets[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY] = ttkb.Checkbutton(parent_tab, variable=self.input_vars[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY])
        self.input_widgets[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY].grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")
        row_idx += 1

        # Current Shift
        current_shift_lbl_key = "current_shift_label" # Add this key to localization
        current_shift_lbl = ttkb.Label(parent_tab, text=localization._(current_shift_lbl_key))
        current_shift_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_form(current_shift_lbl, current_shift_lbl_key)
        self.input_vars[db_schema.COL_EMP_CURRENT_SHIFT] = tk.StringVar()
        shift_options = ["Morning", "Evening", "Night"] # Define shift options
        self.input_widgets[db_schema.COL_EMP_CURRENT_SHIFT] = ttkb.Combobox(parent_tab, textvariable=self.input_vars[db_schema.COL_EMP_CURRENT_SHIFT], values=shift_options, state="readonly")
        self.input_widgets[db_schema.COL_EMP_CURRENT_SHIFT].grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
        self.input_vars[db_schema.COL_EMP_CURRENT_SHIFT].set("Morning") # Default value
        row_idx += 1


    def _create_additional_info_widgets(self, parent_tab):
        parent_tab.columnconfigure(0, weight=1) # Allow photo section to center/expand

        # Photo Section
        photo_lf_key = "photo_section_title"
        photo_frame = ttkb.LabelFrame(parent_tab, text=localization._(photo_lf_key), padding="10")
        photo_frame.pack(pady=10, fill="x")
        self._add_translatable_widget_form(photo_frame, photo_lf_key)

        # Create a Frame with fixed pixel dimensions for the preview area
        # This frame will act as the visual placeholder with a border
        self.photo_preview_area_frame = tk.Frame(photo_frame, width=150, height=150, relief="solid", borderwidth=1)
        self.photo_preview_area_frame.pack(pady=5)
        # Prevent the frame from shrinking or expanding to fit its children (the label)
        self.photo_preview_area_frame.pack_propagate(False) 

        # Label to display the image or "No photo" text, placed inside the fixed-size frame
        self.photo_preview_label = ttkb.Label(self.photo_preview_area_frame, anchor="center")
        self.photo_preview_label.pack(expand=True, fill="both") 
        self.photo_preview_label.config(text=localization._("no_photo_text")) # Initial text
        self._add_translatable_widget_form(self.photo_preview_label, "no_photo_text")

        select_photo_btn_key = "button_select_photo"
        self.select_photo_button = ttkb.Button(photo_frame, text=localization._(select_photo_btn_key), command=self._select_photo)
        self.select_photo_button.pack(pady=5)
        self._add_translatable_widget_form(self.select_photo_button, select_photo_btn_key)

        # Employment History
        history_lf_key = "emp_hist_section_title"
        history_frame = ttkb.LabelFrame(parent_tab, text=localization._(history_lf_key), padding="10")
        history_frame.pack(pady=10, fill="both", expand=True)
        self._add_translatable_widget_form(history_frame, history_lf_key)

        self.input_widgets[db_schema.COL_EMP_EMPLOYMENT_HISTORY] = ScrolledText(history_frame, height=5, width=60, relief="solid", borderwidth=1)
        self.input_widgets[db_schema.COL_EMP_EMPLOYMENT_HISTORY].pack(fill="both", expand=True, pady=5)
        # Theming for ScrolledText will be handled by update_local_theme_elements

    def _initialize_form_data(self):
        if self.mode == 'add':
            # Set defaults for add mode
            self.input_vars[db_schema.COL_EMP_ID].set(localization._("id_auto_generated_text"))
            self.input_vars[db_schema.COL_EMP_STATUS].set(db_schema.STATUS_ACTIVE) # Default status
            self.input_vars[db_schema.COL_EMP_VACATION_DAYS].set("21") # Default vacation days
        elif self.mode in ['edit', 'view'] and self.emp_id_to_edit:
            self._load_employee_data()

    def _load_employee_data(self):
        if not self.emp_id_to_edit: return
        try:
            emp = db_queries.get_employee_by_id_db(self.emp_id_to_edit)
            if not emp:
                messagebox.showerror(localization._("error_title"), localization._("employee_not_found_error_id", emp_id=self.emp_id_to_edit), parent=self)
                self.destroy()
                return

            self.input_vars[db_schema.COL_EMP_ID].set(emp.get(db_schema.COL_EMP_ID, ""))
            self.input_vars[db_schema.COL_EMP_NAME].set(emp.get(db_schema.COL_EMP_NAME, ""))
            self.input_vars[db_schema.COL_EMP_PHONE].set(emp.get(db_schema.COL_EMP_PHONE, ""))
            self.input_vars[db_schema.COL_EMP_EMAIL].set(emp.get(db_schema.COL_EMP_EMAIL, ""))
            
            # For Gender, Marital Status, Status - map DB value to translated display value
            gender_db_val = emp.get(db_schema.COL_EMP_GENDER, "")
            self.input_vars[db_schema.COL_EMP_GENDER].set(self._get_translated_gender(gender_db_val))
            
            marital_db_val = emp.get(db_schema.COL_EMP_MARITAL_STATUS, "")
            self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].set(self._get_translated_marital_status(marital_db_val))

            self.input_vars[db_schema.COL_EMP_EDUCATION].set(emp.get(db_schema.COL_EMP_EDUCATION, ""))

            self.input_vars["department_name"].set(emp.get("department_name", "")) # department_name from join
            self.input_vars[db_schema.COL_EMP_POSITION].set(emp.get(db_schema.COL_EMP_POSITION, ""))
            self.input_vars[db_schema.COL_EMP_SALARY].set(str(emp.get(db_schema.COL_EMP_SALARY, "")))
            if emp.get(db_schema.COL_EMP_START_DATE):
                self.input_widgets[db_schema.COL_EMP_START_DATE].date = dt_date.fromisoformat(emp[db_schema.COL_EMP_START_DATE])
            
            status_db_val = emp.get(db_schema.COL_EMP_STATUS, db_schema.STATUS_ACTIVE)
            self.input_vars[db_schema.COL_EMP_STATUS].set(self._get_translated_status(status_db_val))
            
            manager_id = emp.get(db_schema.COL_EMP_MANAGER_ID)
            if manager_id:
                manager_details = db_queries.get_employee_by_id_db(manager_id)
                if manager_details:
                    self.input_vars["manager_name"].set(f"{manager_details[db_schema.COL_EMP_NAME]} ({manager_details[db_schema.COL_EMP_ID]})")
            
            self.input_vars[db_schema.COL_EMP_DEVICE_USER_ID].set(emp.get(db_schema.COL_EMP_DEVICE_USER_ID, ""))
            self.input_vars[db_schema.COL_EMP_VACATION_DAYS].set(str(emp.get(db_schema.COL_EMP_VACATION_DAYS, "21")))
            self.input_vars[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY].set(bool(emp.get(db_schema.COL_EMP_EXCLUDE_VACATION_POLICY, False)))
            self.input_vars[db_schema.COL_EMP_CURRENT_SHIFT].set(emp.get(db_schema.COL_EMP_CURRENT_SHIFT, "Morning"))

            # Robust insertion for employment history
            history_text_widget = self.input_widgets[db_schema.COL_EMP_EMPLOYMENT_HISTORY]
            history_text_widget.delete("1.0", tk.END)
            history_text_content = emp.get(db_schema.COL_EMP_EMPLOYMENT_HISTORY, "")
            history_text_content = str(history_text_content if history_text_content is not None else "")
            if '\0' in history_text_content:
                logger.warning("Employment history (form) contains null bytes. Replacing with [NULL] for display.")
                history_text_content = history_text_content.replace('\0', '[NULL]')
            history_text_widget.insert("1.0", history_text_content)



            self.current_photo_path = emp.get(db_schema.COL_EMP_PHOTO_PATH)
            self._display_photo_preview()

        except Exception as e:
            logger.error(f"Error loading employee data for {self.mode}: {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("failed_to_load_employee_data_error", error=e), parent=self)

    def _save_employee_data(self):
        try:
            emp_id = self.input_vars[db_schema.COL_EMP_ID].get() # Read-only for edit, generated for add
            name = self.input_vars[db_schema.COL_EMP_NAME].get().strip()
            if not name:
                messagebox.showerror(localization._("input_error_title"), localization._("employee_name_required_error"), parent=self)
                return

            dept_name_selection = self.input_vars["department_name"].get()
            department_id = db_queries.get_department_id_by_name_db(dept_name_selection) if dept_name_selection else None

            position = self.input_vars[db_schema.COL_EMP_POSITION].get().strip()
            salary_str = self.input_vars[db_schema.COL_EMP_SALARY].get().strip()
            salary = float(salary_str) if salary_str else 0.0
            
            vacation_days_str = self.input_vars[db_schema.COL_EMP_VACATION_DAYS].get().strip()
            vacation_days = int(vacation_days_str) if vacation_days_str.isdigit() else 0

            # Map translated status back to DB value
            status_display_val = self.input_vars[db_schema.COL_EMP_STATUS].get()
            status = self._get_db_status_from_display(status_display_val)
            if not status: # Should not happen if combobox is populated correctly
                messagebox.showerror(localization._("input_error_title"), localization._("invalid_status_selection_error"), parent=self)
                return

            phone = self.input_vars[db_schema.COL_EMP_PHONE].get().strip() or None
            email = self.input_vars[db_schema.COL_EMP_EMAIL].get().strip() or None
            gender = self.input_vars[db_schema.COL_EMP_GENDER].get() or None
            start_date = self.input_widgets[db_schema.COL_EMP_START_DATE].entry.get() or None
            marital_status = self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].get() or None
            education = self.input_vars[db_schema.COL_EMP_EDUCATION].get().strip() or None
            employment_history = self.input_widgets[db_schema.COL_EMP_EMPLOYMENT_HISTORY].get("1.0", tk.END).strip() or None
            # Map translated gender and marital status back to DB values
            gender = self._get_db_gender_from_display(self.input_vars[db_schema.COL_EMP_GENDER].get())
            marital_status = self._get_db_marital_status_from_display(self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].get())

            manager_name_selection = self.input_vars["manager_name"].get()
            manager_id = extract_id_from_combobox_selection(manager_name_selection)

            device_user_id = self.input_vars[db_schema.COL_EMP_DEVICE_USER_ID].get().strip() or None
            current_shift = self.input_vars[db_schema.COL_EMP_CURRENT_SHIFT].get()
            exclude_vacation_policy = self.input_vars[db_schema.COL_EMP_EXCLUDE_VACATION_POLICY].get()

            if self.mode == 'add':
                new_emp_id = db_queries.add_employee_db(
                    emp_id=db_queries.get_next_employee_id_db(), # Generate new ID
                    name=name, department_id=department_id, position=position, salary=salary,
                    vacation_days=vacation_days, status=status, phone=phone, email=email,
                    photo_path=self.current_photo_path, gender=gender, start_date=start_date,
                    marital_status=marital_status, education=education, employment_history=employment_history, current_shift=current_shift,
                    manager_id=manager_id, device_user_id=device_user_id,
                    exclude_vacation_policy=exclude_vacation_policy
                )
                messagebox.showinfo(localization._("success_title"), localization._("employee_added_success_message_form", emp_id=new_emp_id), parent=self)
            elif self.mode == 'edit':
                updates = {
                    db_schema.COL_EMP_NAME: name, db_schema.COL_EMP_DEPARTMENT_ID: department_id,
                    db_schema.COL_EMP_POSITION: position, db_schema.COL_EMP_SALARY: salary,
                    db_schema.COL_EMP_VACATION_DAYS: vacation_days, db_schema.COL_EMP_STATUS: status,
                    db_schema.COL_EMP_PHONE: phone, db_schema.COL_EMP_EMAIL: email,
                    db_schema.COL_EMP_PHOTO_PATH: self.current_photo_path, db_schema.COL_EMP_GENDER: gender,
                    db_schema.COL_EMP_START_DATE: start_date, db_schema.COL_EMP_MARITAL_STATUS: marital_status,
                    db_schema.COL_EMP_EDUCATION: education, db_schema.COL_EMP_EMPLOYMENT_HISTORY: employment_history, db_schema.COL_EMP_CURRENT_SHIFT: current_shift,
                    db_schema.COL_EMP_MANAGER_ID: manager_id, db_schema.COL_EMP_DEVICE_USER_ID: device_user_id,
                    "exclude_vacation_policy": 1 if exclude_vacation_policy else 0
                }
                db_queries.update_employee_db(self.emp_id_to_edit, updates)
                messagebox.showinfo(localization._("success_title"), localization._("employee_updated_success_message_form", emp_id=self.emp_id_to_edit), parent=self)

            if self.callback_on_save:
                self.callback_on_save()
            self.destroy()

        except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(localization._("save_error_title"), str(e), parent=self)
        except ValueError as ve:
            messagebox.showerror(localization._("input_error_title"), localization._("invalid_numeric_format_error", field="Salary or Vacation Days"), parent=self)
        except Exception as ex:
            logger.error(f"Unexpected error saving employee: {ex}", exc_info=True)
            messagebox.showerror(localization._("unexpected_error_title"), localization._("unexpected_error_occurred_message", error=ex), parent=self)

    def _select_photo(self):
        # Open file dialog, validate image, display preview, store path in self.current_photo_path
        filepath = filedialog.askopenfilename(
            title=localization._("select_photo_dialog_title"),
            filetypes=[(localization._("image_files_filter_text"), "*.jpg *.jpeg *.png *.gif"), (localization._("all_files_filter_text"), "*.*")],
            parent=self
        )
        if filepath:
            self.current_photo_path = filepath
            self._display_photo_preview()

    def _display_photo_preview(self):
        if self.current_photo_path and os.path.exists(self.current_photo_path):
            try:
                img = load_and_resize_photo(self.current_photo_path, max_width=150, max_height=150) # Resize for preview
                self._photo_image_ref_form = img # Keep reference for this form
                self.photo_preview_label.config(image=self._photo_image_ref_form, text="")
            except (UnidentifiedImageError, Exception) as e:
                logger.warning(f"Could not load photo preview: {e}")
                self.photo_preview_label.config(image="", text=localization._("invalid_photo_text"))
                self._photo_image_ref_form = None
        else:
            self.photo_preview_label.config(image="", text=localization._("no_photo_text"))
            self._photo_image_ref_form = None
        
    def populate_department_combobox(self):
        # Fetch departments using db_queries.get_all_departments_db()
        # Populate self.department_combo
        try:
            departments = db_queries.get_all_departments_db()
            dept_names = [dept[db_schema.COL_DEPT_NAME] for dept in departments]
            self.input_widgets["department_name"].set_completion_list([""] + dept_names) # Allow empty selection
        except db_queries.DatabaseOperationError as e:
            logger.error(f"Error populating department combobox: {e}")
            self.input_widgets["department_name"].set_completion_list([])

    def populate_manager_combobox(self):
        # Fetch employees (potential managers) using db_queries.get_all_employees_db()
        # Populate self.manager_combo (excluding current employee if editing)
        try:
            employees = db_queries.get_all_employees_db(include_archived=False)
            # Exclude current employee if in edit mode
            manager_list = [f"{emp[db_schema.COL_EMP_NAME]} ({emp[db_schema.COL_EMP_ID]})" 
                            for emp in employees 
                            if self.mode == 'add' or (self.mode == 'edit' and emp[db_schema.COL_EMP_ID] != self.emp_id_to_edit)]
            self.input_widgets["manager_name"].set_completion_list([""] + manager_list) # Allow empty selection
        except db_queries.DatabaseOperationError as e:
            logger.error(f"Error populating manager combobox: {e}")
            self.input_widgets["manager_name"].set_completion_list([])

    def _set_view_only_state(self):
        """Sets all input widgets to a read-only or disabled state."""
        for key, widget_info in self.input_widgets.items():
            widget = widget_info # If input_widgets stores widgets directly
            if isinstance(widget_info, dict) and "widget" in widget_info: # If it's a dict like in settings_vars
                widget = widget_info["widget"]

            if isinstance(widget, (ttkb.Entry, ScrolledText, tk.Text)):
                widget.config(state="readonly" if isinstance(widget, ttkb.Entry) else "disabled")
            elif isinstance(widget, (ttkb.Combobox, ttkb.Spinbox, ttkb.DateEntry, ttkb.Checkbutton)):
                widget.config(state="disabled")
        
        # Disable photo selection button
        if hasattr(self, 'select_photo_button'):
            self.select_photo_button.config(state="disabled")
        # Save button is already handled (not packed) in __init__ if view_only

    
    def update_local_theme_elements(self):
        super().update_local_theme_elements() # Call parent's theming
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        
        # Theme the photo preview area frame (it's a tk.Frame)
        if hasattr(self, 'photo_preview_area_frame') and self.photo_preview_area_frame.winfo_exists():
            self.photo_preview_area_frame.config(bg=palette.get('entry_bg', palette.get('bg_secondary', '#FFFFFF')))

        # Theme the ScrolledText for employment history
        if hasattr(self, 'input_widgets') and db_schema.COL_EMP_EMPLOYMENT_HISTORY in self.input_widgets:
            history_text_widget = self.input_widgets[db_schema.COL_EMP_EMPLOYMENT_HISTORY]
            if history_text_widget.winfo_exists():
                _theme_text_widget_global(history_text_widget, palette)

    def _gui_manage_econtract(self):
        # Open ElectronicContractWindow for the current employee
        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            employee_id=self.employee_id,
            tracker_attr_name=f"active_econtract_window_{self.employee_id}" # Unique tracker
        )
        
    
    def refresh_ui_for_language(self): # pragma: no cover
        """Overrides ThemedToplevel's method to also update specific form elements."""
        # super().refresh_ui_for_language() # Call parent if it exists and does something useful
        self.title(localization._(self.title_key))

        for item_info in self.translatable_widgets_form:
            widget = item_info["widget"]
            key = item_info["key"]
            attr = item_info["attr"]
            
            if not widget.winfo_exists():
                continue

            try:
                if attr == "text":
                    widget.config(text=localization._(key))
                elif attr == "title": # For LabelFrames or similar
                    widget.config(text=localization._(key))
                elif attr == "tab": # For notebook tabs
                    tab_index = item_info["index"]
                    widget.tab(tab_index, text=localization._(key))
                # Add more attributes as needed
            except tk.TclError as e:
                logger.warning(f"TclError updating widget for key '{key}' in EmployeeForm: {e}")
            except Exception as e:
                logger.error(f"Error updating widget for key '{key}' in EmployeeForm: {e}")
        
        # Re-populate translatable comboboxes
        self._populate_gender_combobox()
        self._populate_marital_status_combobox()
        self._populate_status_combobox()

        # Repopulate department and manager comboboxes as their "empty" option might be translatable
        self.populate_department_combobox()
        self.populate_manager_combobox()

    def _populate_gender_combobox(self):
        current_val = self.input_vars[db_schema.COL_EMP_GENDER].get()
        translated_values = [localization._("gender_male"), localization._("gender_female"), localization._("gender_other")]
        self.input_widgets[db_schema.COL_EMP_GENDER]['values'] = translated_values
        if current_val in translated_values:
            self.input_vars[db_schema.COL_EMP_GENDER].set(current_val)
        elif translated_values:
            self.input_vars[db_schema.COL_EMP_GENDER].set(translated_values[0])

    def _get_translated_gender(self, db_value: Optional[str]) -> str:
        if db_value == "Male": return localization._("gender_male")
        if db_value == "Female": return localization._("gender_female")
        if db_value == "Other": return localization._("gender_other")
        return ""

    def _get_db_gender_from_display(self, display_value: str) -> Optional[str]:
        if display_value == localization._("gender_male"): return "Male"
        if display_value == localization._("gender_female"): return "Female"
        if display_value == localization._("gender_other"): return "Other"
        return None

    def _populate_marital_status_combobox(self):
        current_val = self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].get()
        translated_values = [localization._("marital_single"), localization._("marital_married"), localization._("marital_divorced"), localization._("marital_widowed")]
        self.input_widgets[db_schema.COL_EMP_MARITAL_STATUS]['values'] = translated_values
        if current_val in translated_values:
            self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].set(current_val)
        elif translated_values:
            self.input_vars[db_schema.COL_EMP_MARITAL_STATUS].set(translated_values[0])

    def _get_translated_marital_status(self, db_value: Optional[str]) -> str:
        # This assumes your DB stores "Single", "Married", etc.
        if db_value == "Single": return localization._("marital_single")
        if db_value == "Married": return localization._("marital_married")
        # ... add other mappings ...
        return ""

    def _get_db_marital_status_from_display(self, display_value: str) -> Optional[str]:
        if display_value == localization._("marital_single"): return "Single"
        if display_value == localization._("marital_married"): return "Married"
        # ... add other mappings ...
        return None

    def _populate_status_combobox(self):
        current_val = self.input_vars[db_schema.COL_EMP_STATUS].get()
        translated_values = [localization._(status) for status in db_schema.VALID_EMPLOYEE_STATUSES]
        self.input_widgets[db_schema.COL_EMP_STATUS]['values'] = translated_values
        if current_val in translated_values:
            self.input_vars[db_schema.COL_EMP_STATUS].set(current_val)
        elif translated_values: # Default to translated "Active"
            self.input_vars[db_schema.COL_EMP_STATUS].set(localization._(db_schema.STATUS_ACTIVE))

    def _get_translated_status(self, db_value: Optional[str]) -> str:
        return localization._(db_value) if db_value in db_schema.VALID_EMPLOYEE_STATUSES else ""

    def _get_db_status_from_display(self, display_value: str) -> Optional[str]:
        for status_key in db_schema.VALID_EMPLOYEE_STATUSES:
            if display_value == localization._(status_key):
                return status_key
        return None

    # Override update_local_theme_elements if EmployeeFormWindow has its own non-ttk widgets
    # that need specific theming beyond what ThemedToplevel handles.
    # def update_local_theme_elements(self):
    #     super().update_local_theme_elements() # Call parent's theming
    #     # Add any EmployeeFormWindow-specific theming here
    #     palette = get_theme_palette_global(self.current_theme)
    #     # Example: if you have a tk.Text widget for notes
    #     # if hasattr(self, 'notes_text_widget') and self.notes_text_widget.winfo_exists():
    #     #     _theme_text_widget_global(self.notes_text_widget, palette)
