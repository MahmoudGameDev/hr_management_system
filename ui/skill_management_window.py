# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\skill_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging
from typing import Optional

from .themed_toplevel import ThemedToplevel
from data import database as db_schema
from data import queries as db_queries
from utils.localization import _
from utils.exceptions import InvalidInputError, DatabaseOperationError, HRException
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global

logger = logging.getLogger(__name__)

class SkillManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title_key = "skill_mgt_window_title"
        self.title(_(self.title_key))
        self.geometry("800x600")

        self.current_selected_skill_id: Optional[int] = None
        self.translatable_widgets_skill_mgt = []

        main_frame = ttk.Frame(self, padding="10")
        self.skill_form_widgets = {} # Initialize dictionary to store form widgets
        main_frame.pack(fill="both", expand=True)

        # --- Skill List (Left) ---
        list_lf_key = "skill_list_frame_title"
        list_frame = ttk.LabelFrame(main_frame, text=_(list_lf_key), padding="10")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._add_translatable_widget(list_frame, list_lf_key, attr="title")

        self.skill_tree_cols = (db_schema.COL_SKILL_ID, db_schema.COL_SKILL_NAME, db_schema.COL_SKILL_CATEGORY)
        self.skill_tree = ttk.Treeview(list_frame, columns=self.skill_tree_cols, show="headings")
        self._update_skill_tree_headers()

        self.skill_tree.column(db_schema.COL_SKILL_ID, width=60, anchor="e", stretch=tk.NO)
        self.skill_tree.column(db_schema.COL_SKILL_NAME, width=200, stretch=tk.YES)
        self.skill_tree.column(db_schema.COL_SKILL_CATEGORY, width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.skill_tree.yview)
        self.skill_tree.configure(yscrollcommand=scrollbar.set)
        self.skill_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.skill_tree.bind("<<TreeviewSelect>>", self._on_skill_select)

        # --- Skill Form (Right) ---
        form_lf_key = "skill_details_frame_title"
        form_frame = ttk.LabelFrame(main_frame, text=_(form_lf_key), padding="10")
        form_frame.pack(side="right", fill="y", padx=(5, 0))
        self._add_translatable_widget(form_frame, form_lf_key, attr="title")
        form_frame.columnconfigure(1, weight=1)

        self.skill_form_vars = {}
        row_idx = 0

        # Skill Name
        name_lbl_key = "skill_name_label"
        ttk.Label(form_frame, text=_(name_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], name_lbl_key)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=30)
        name_entry.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        self.skill_form_vars[db_schema.COL_SKILL_NAME] = name_var
        self.skill_form_widgets[db_schema.COL_SKILL_NAME] = name_entry # Store the widget
        row_idx += 1

        # Category
        category_lbl_key = "skill_category_label"
        ttk.Label(form_frame, text=_(category_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], category_lbl_key)
        self.skill_form_vars[db_schema.COL_SKILL_CATEGORY] = tk.StringVar()
        # Example categories, could be loaded from DB or config
        categories = ["Technical", "Soft Skill", "Language", "Management", "Other"]
        ttk.Combobox(form_frame, textvariable=self.skill_form_vars[db_schema.COL_SKILL_CATEGORY], values=categories, width=28).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Description
        desc_lbl_key = "skill_description_label"
        ttk.Label(form_frame, text=_(desc_lbl_key)).grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], desc_lbl_key)
        self.skill_desc_text = tk.Text(form_frame, height=5, width=30, relief="solid", borderwidth=1)
        self.skill_desc_text.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.skill_desc_text, palette)
        row_idx += 1

        # Action Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=15, sticky="ew")

        self.add_skill_btn = ttk.Button(buttons_frame, text=_("skill_add_btn"), command=self._gui_add_skill, bootstyle=db_schema.BS_ADD)
        self.add_skill_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.add_skill_btn, "skill_add_btn")

        self.update_skill_btn = ttk.Button(buttons_frame, text=_("skill_update_btn"), command=self._gui_update_skill, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.update_skill_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.update_skill_btn, "skill_update_btn")

        self.delete_skill_btn = ttk.Button(buttons_frame, text=_("skill_delete_btn"), command=self._gui_delete_skill, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_skill_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.delete_skill_btn, "skill_delete_btn")

        self.clear_skill_form_btn = ttk.Button(buttons_frame, text=_("skill_clear_btn"), command=self._gui_clear_skill_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_skill_form_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.clear_skill_form_btn, "skill_clear_btn")

        self._load_skills_to_tree()

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_skill_mgt.append({"widget": widget, "key": key, "attr": attr})

    def _update_skill_tree_headers(self):
        if hasattr(self, 'skill_tree') and self.skill_tree.winfo_exists():
            self.skill_tree.heading(db_schema.COL_SKILL_ID, text=_("skill_header_id"))
            self.skill_tree.heading(db_schema.COL_SKILL_NAME, text=_("skill_header_name"))
            self.skill_tree.heading(db_schema.COL_SKILL_CATEGORY, text=_("skill_header_category"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_(self.title_key))
        self._update_skill_tree_headers()
        for item in self.translatable_widgets_skill_mgt:
            widget, key, attr = item["widget"], item["key"], item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text": widget.config(text=_(key))
                    elif attr == "title": widget.config(text=_(key))
                except tk.TclError: pass

    def _load_skills_to_tree(self):
        for item in self.skill_tree.get_children(): self.skill_tree.delete(item)
        try:
            skills = db_queries.get_all_skills_db()
            for skill in skills:
                self.skill_tree.insert("", "end", iid=skill[db_schema.COL_SKILL_ID], values=(
                    skill[db_schema.COL_SKILL_ID], skill[db_schema.COL_SKILL_NAME],
                    skill.get(db_schema.COL_SKILL_CATEGORY, "")
                ))
        except DatabaseOperationError as e: messagebox.showerror(_("db_error_title"), str(e), parent=self)
        self._gui_clear_skill_form()

    def _on_skill_select(self, event=None):
        selected_item_iid = self.skill_tree.focus()
        if not selected_item_iid: self._gui_clear_skill_form(); return
        self.current_selected_skill_id = int(selected_item_iid)
        try:
            skills = db_queries.get_all_skills_db() # Inefficient, better to have get_skill_by_id
            skill_details = next((s for s in skills if s[db_schema.COL_SKILL_ID] == self.current_selected_skill_id), None)
            if skill_details:
                self.skill_form_vars[db_schema.COL_SKILL_NAME].set(skill_details.get(db_schema.COL_SKILL_NAME, ""))
                self.skill_form_vars[db_schema.COL_SKILL_CATEGORY].set(skill_details.get(db_schema.COL_SKILL_CATEGORY, ""))
                self.skill_desc_text.delete("1.0", tk.END)
                self.skill_desc_text.insert("1.0", skill_details.get(db_schema.COL_SKILL_DESCRIPTION, ""))
                self.update_skill_btn.config(state="normal"); self.delete_skill_btn.config(state="normal"); self.add_skill_btn.config(state="disabled")
        except DatabaseOperationError as e: messagebox.showerror(_("db_error_title"), _("skill_error_loading_details", error=e), parent=self)

    def _gui_add_skill(self):
        name = self.skill_form_vars[db_schema.COL_SKILL_NAME].get().strip()
        category = self.skill_form_vars[db_schema.COL_SKILL_CATEGORY].get().strip()
        description = self.skill_desc_text.get("1.0", tk.END).strip()
        try:
            db_queries.add_skill_db(name, description, category)
            messagebox.showinfo(_("success_title"), _("skill_add_success", name=name), parent=self)
            self._load_skills_to_tree()
        except (InvalidInputError, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_update_skill(self):
        if self.current_selected_skill_id is None: return
        name = self.skill_form_vars[db_schema.COL_SKILL_NAME].get().strip()
        category = self.skill_form_vars[db_schema.COL_SKILL_CATEGORY].get().strip()
        description = self.skill_desc_text.get("1.0", tk.END).strip()
        try:
            db_queries.update_skill_db(self.current_selected_skill_id, name, description, category)
            messagebox.showinfo(_("success_title"), _("skill_update_success", name=name), parent=self)
            self._load_skills_to_tree()
        except (InvalidInputError, HRException, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_delete_skill(self):
        if self.current_selected_skill_id is None: return
        name = self.skill_form_vars[db_schema.COL_SKILL_NAME].get()
        if messagebox.askyesno(_("confirm_delete_title"), _("skill_delete_confirm", name=name), parent=self):
            try:
                db_queries.delete_skill_db(self.current_selected_skill_id)
                messagebox.showinfo(_("success_title"), _("skill_delete_success", name=name), parent=self)
                self._load_skills_to_tree()
            except (HRException, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_clear_skill_form(self):
        self.current_selected_skill_id = None
        for var_key in self.skill_form_vars:
            self.skill_form_vars[var_key].set("")
        self.skill_desc_text.delete("1.0", tk.END)
        self.add_skill_btn.config(state="normal"); self.update_skill_btn.config(state="disabled"); self.delete_skill_btn.config(state="disabled")
        if self.skill_tree.selection(): self.skill_tree.selection_remove(self.skill_tree.selection())
        # Focus the name entry
        name_entry_widget = self.skill_form_widgets.get(db_schema.COL_SKILL_NAME)
        if name_entry_widget:
            name_entry_widget.focus_set()

    def update_local_theme_elements(self):
        super().update_local_theme_elements()
        if hasattr(self, 'skill_desc_text') and self.skill_desc_text.winfo_exists():
            palette = get_theme_palette_global(self.parent_app.get_current_theme())
            _theme_text_widget_global(self.skill_desc_text, palette)