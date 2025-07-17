# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\assign_skill_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
import logging
from datetime import date as dt_date
from typing import Optional, List, Dict

from .themed_toplevel import ThemedToplevel
from data import database as db_schema
from data import queries as db_queries
from utils.localization import _
from utils.exceptions import InvalidInputError, DatabaseOperationError
from utils.gui_utils import extract_id_from_combobox_selection # For skill ID

logger = logging.getLogger(__name__)

class AssignSkillDialog(ThemedToplevel):
    def __init__(self, parent, app_instance, employee_id: str, existing_skill_data: Optional[Dict] = None):
        super().__init__(parent, app_instance)
        self.employee_id = employee_id
        self.existing_skill_data = existing_skill_data # For edit mode
        self.result: Optional[Dict] = None # To store skill_id, proficiency, date

        self.title_key = "assign_skill_dialog_title"
        self.title(_(self.title_key))
        self.geometry("450x300") # Adjusted size
        self.translatable_widgets_assign_skill = []

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1)

        row_idx = 0

        # Select Skill
        skill_lbl_key = "assign_skill_select_skill_label"
        ttk.Label(main_frame, text=_(skill_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget(main_frame.grid_slaves(row=row_idx, column=0)[0], skill_lbl_key)
        self.skill_var = tk.StringVar()
        self.skill_combo = ttk.Combobox(main_frame, textvariable=self.skill_var, state="readonly", width=35)
        self.skill_combo.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=5)
        self._populate_skills_combobox()
        row_idx += 1

        # Proficiency Level
        prof_lbl_key = "assign_skill_proficiency_label"
        ttk.Label(main_frame, text=_(prof_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget(main_frame.grid_slaves(row=row_idx, column=0)[0], prof_lbl_key)
        self.proficiency_var = tk.StringVar()
        # Example proficiency levels, could be configurable
        proficiency_levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
        self.proficiency_combo = ttk.Combobox(main_frame, textvariable=self.proficiency_var, values=proficiency_levels, width=35)
        self.proficiency_combo.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=5)
        row_idx += 1

        # Acquisition Date
        acq_date_lbl_key = "assign_skill_acquisition_date_label"
        ttk.Label(main_frame, text=_(acq_date_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget(main_frame.grid_slaves(row=row_idx, column=0)[0], acq_date_lbl_key)
        self.acquisition_date_entry = DateEntry(main_frame, width=15, dateformat='%Y-%m-%d')
        self.acquisition_date_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)
        self.acquisition_date_entry.date = dt_date.today() # Default to today
        row_idx += 1

        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=15, sticky="e")

        save_btn_key = "assign_skill_save_button"
        ttk.Button(buttons_frame, text=_(save_btn_key), command=self._on_save, bootstyle=db_schema.BS_ADD).pack(side="left", padx=5)
        self._add_translatable_widget(buttons_frame.winfo_children()[-1], save_btn_key)

        cancel_btn_key = "form_button_cancel" # Reusing key
        ttk.Button(buttons_frame, text=_(cancel_btn_key), command=self.destroy, bootstyle=db_schema.BS_LIGHT).pack(side="left", padx=5)
        self._add_translatable_widget(buttons_frame.winfo_children()[-1], cancel_btn_key)

        if self.existing_skill_data:
            self._load_existing_data()

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_assign_skill.append({"widget": widget, "key": key, "attr": attr})

    def _populate_skills_combobox(self):
        try:
            skills = db_queries.get_all_skills_db()
            skill_display_list = [f"{skill[db_schema.COL_SKILL_NAME]} (ID: {skill[db_schema.COL_SKILL_ID]})" for skill in skills]
            self.skill_combo['values'] = skill_display_list
            if skill_display_list:
                self.skill_combo.current(0)
        except DatabaseOperationError as e:
            messagebox.showerror(_("db_error_title"), str(e), parent=self)

    def _load_existing_data(self):
        if not self.existing_skill_data: return
        skill_id = self.existing_skill_data.get(db_schema.COL_EMP_SKILL_SKILL_ID)
        skill_name = self.existing_skill_data.get(db_schema.COL_SKILL_NAME)
        
        # Find and set the skill in combobox
        for val in self.skill_combo['values']:
            if f"(ID: {skill_id})" in val and skill_name in val:
                self.skill_var.set(val)
                break
        self.skill_combo.config(state="disabled") # Cannot change skill in edit mode

        self.proficiency_var.set(self.existing_skill_data.get(db_schema.COL_EMP_SKILL_PROFICIENCY_LEVEL, ""))
        acq_date_str = self.existing_skill_data.get(db_schema.COL_EMP_SKILL_ACQUISITION_DATE)
        if acq_date_str:
            try: self.acquisition_date_entry.date = dt_date.fromisoformat(acq_date_str)
            except ValueError: pass # Keep default if format is wrong

    def _on_save(self):
        skill_selection = self.skill_var.get()
        skill_id = extract_id_from_combobox_selection(skill_selection)
        proficiency = self.proficiency_var.get().strip()
        acquisition_date = self.acquisition_date_entry.entry.get()

        if not skill_id:
            messagebox.showerror(_("input_error_title"), _("assign_skill_no_skill_selected_error"), parent=self)
            return
        if not proficiency:
            messagebox.showerror(_("input_error_title"), _("assign_skill_proficiency_empty_error"), parent=self)
            return
        # Date validation is implicitly handled by DateEntry, but can add explicit check if needed

        self.result = {
            "skill_id": int(skill_id),
            "skill_name": skill_selection.split(' (ID:')[0], # Get name part for success message
            "proficiency_level": proficiency,
            "acquisition_date": acquisition_date
        }
        self.destroy()

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_(self.title_key))
        for item in self.translatable_widgets_assign_skill:
            widget, key, attr = item["widget"], item["key"], item["attr"]
            if widget.winfo_exists():
                try: widget.config(**{attr: _(key)})
                except tk.TclError: pass
        # Repopulate comboboxes if their "empty" or default options are translatable
        self._populate_skills_combobox()
        # Proficiency levels are hardcoded for now, but if they were keys, they'd be updated here.