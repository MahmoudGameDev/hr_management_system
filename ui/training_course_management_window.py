# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\training_course_management_window.py
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

class TrainingCourseManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title_key = "training_course_mgt_window_title"
        self.title(_(self.title_key))
        self.geometry("800x600")

        self.current_selected_course_id: Optional[int] = None
        self.translatable_widgets_course_mgt = []

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Course List (Left) ---
        list_lf_key = "training_course_list_frame_title"
        list_frame = ttk.LabelFrame(main_frame, text=_(list_lf_key), padding="10")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._add_translatable_widget(list_frame, list_lf_key, attr="title")

        self.course_tree_cols = (db_schema.COL_COURSE_ID, db_schema.COL_COURSE_NAME, db_schema.COL_COURSE_PROVIDER, db_schema.COL_COURSE_DEFAULT_DURATION_HOURS)
        self.course_tree = ttk.Treeview(list_frame, columns=self.course_tree_cols, show="headings")
        self._update_course_tree_headers()

        self.course_tree.column(db_schema.COL_COURSE_ID, width=60, anchor="e", stretch=tk.NO)
        self.course_tree.column(db_schema.COL_COURSE_NAME, width=200, stretch=tk.YES)
        self.course_tree.column(db_schema.COL_COURSE_PROVIDER, width=150)
        self.course_tree.column(db_schema.COL_COURSE_DEFAULT_DURATION_HOURS, width=100, anchor="e")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.course_tree.yview)
        self.course_tree.configure(yscrollcommand=scrollbar.set)
        self.course_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.course_tree.bind("<<TreeviewSelect>>", self._on_course_select)

        # --- Course Form (Right) ---
        form_lf_key = "training_course_details_frame_title"
        form_frame = ttk.LabelFrame(main_frame, text=_(form_lf_key), padding="10")
        form_frame.pack(side="right", fill="y", padx=(5, 0))
        self._add_translatable_widget(form_frame, form_lf_key, attr="title")
        form_frame.columnconfigure(1, weight=1)

        self.course_form_vars = {}
        row_idx = 0

        # Course Name
        name_lbl_key = "training_course_name_label"
        ttk.Label(form_frame, text=_(name_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], name_lbl_key)
        self.course_form_vars[db_schema.COL_COURSE_NAME] = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.course_form_vars[db_schema.COL_COURSE_NAME], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Provider
        provider_lbl_key = "training_course_provider_label"
        ttk.Label(form_frame, text=_(provider_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], provider_lbl_key)
        self.course_form_vars[db_schema.COL_COURSE_PROVIDER] = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.course_form_vars[db_schema.COL_COURSE_PROVIDER], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Default Duration (Hours)
        duration_lbl_key = "training_course_duration_label"
        ttk.Label(form_frame, text=_(duration_lbl_key)).grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], duration_lbl_key)
        self.course_form_vars[db_schema.COL_COURSE_DEFAULT_DURATION_HOURS] = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.course_form_vars[db_schema.COL_COURSE_DEFAULT_DURATION_HOURS], width=10).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Description
        desc_lbl_key = "training_course_description_label"
        ttk.Label(form_frame, text=_(desc_lbl_key)).grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=row_idx, column=0)[0], desc_lbl_key)
        self.course_desc_text = tk.Text(form_frame, height=5, width=30, relief="solid", borderwidth=1)
        self.course_desc_text.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.course_desc_text, palette)
        row_idx += 1

        # Action Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=15, sticky="ew")

        self.add_course_btn = ttk.Button(buttons_frame, text=_("training_course_add_btn"), command=self._gui_add_course, bootstyle=db_schema.BS_ADD)
        self.add_course_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.add_course_btn, "training_course_add_btn")

        self.update_course_btn = ttk.Button(buttons_frame, text=_("training_course_update_btn"), command=self._gui_update_course, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.update_course_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.update_course_btn, "training_course_update_btn")

        self.delete_course_btn = ttk.Button(buttons_frame, text=_("training_course_delete_btn"), command=self._gui_delete_course, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_course_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.delete_course_btn, "training_course_delete_btn")

        self.clear_course_form_btn = ttk.Button(buttons_frame, text=_("training_course_clear_btn"), command=self._gui_clear_course_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_course_form_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.clear_course_form_btn, "training_course_clear_btn")

        self._load_courses_to_tree()

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_course_mgt.append({"widget": widget, "key": key, "attr": attr})

    def _update_course_tree_headers(self):
        if hasattr(self, 'course_tree') and self.course_tree.winfo_exists():
            self.course_tree.heading(db_schema.COL_COURSE_ID, text=_("training_course_header_id"))
            self.course_tree.heading(db_schema.COL_COURSE_NAME, text=_("training_course_header_name"))
            self.course_tree.heading(db_schema.COL_COURSE_PROVIDER, text=_("training_course_header_provider"))
            self.course_tree.heading(db_schema.COL_COURSE_DEFAULT_DURATION_HOURS, text=_("training_course_header_duration"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_(self.title_key))
        self._update_course_tree_headers()
        for item in self.translatable_widgets_course_mgt:
            widget, key, attr = item["widget"], item["key"], item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text": widget.config(text=_(key))
                    elif attr == "title": widget.config(text=_(key))
                except tk.TclError: pass

    def _load_courses_to_tree(self):
        for item in self.course_tree.get_children(): self.course_tree.delete(item)
        try:
            courses = db_queries.get_all_training_courses_db()
            for course in courses:
                self.course_tree.insert("", "end", iid=course[db_schema.COL_COURSE_ID], values=(
                    course[db_schema.COL_COURSE_ID], course[db_schema.COL_COURSE_NAME],
                    course.get(db_schema.COL_COURSE_PROVIDER, ""),
                    course.get(db_schema.COL_COURSE_DEFAULT_DURATION_HOURS, "")
                ))
        except DatabaseOperationError as e: messagebox.showerror(_("db_error_title"), str(e), parent=self)
        self._gui_clear_course_form()

    def _on_course_select(self, event=None):
        selected_item_iid = self.course_tree.focus()
        if not selected_item_iid: self._gui_clear_course_form(); return
        self.current_selected_course_id = int(selected_item_iid)
        try:
            courses = db_queries.get_all_training_courses_db() # Inefficient, better to have get_course_by_id
            course_details = next((c for c in courses if c[db_schema.COL_COURSE_ID] == self.current_selected_course_id), None)
            if course_details:
                self.course_form_vars[db_schema.COL_COURSE_NAME].set(course_details.get(db_schema.COL_COURSE_NAME, ""))
                self.course_form_vars[db_schema.COL_COURSE_PROVIDER].set(course_details.get(db_schema.COL_COURSE_PROVIDER, ""))
                self.course_form_vars[db_schema.COL_COURSE_DEFAULT_DURATION_HOURS].set(str(course_details.get(db_schema.COL_COURSE_DEFAULT_DURATION_HOURS, "")))
                self.course_desc_text.delete("1.0", tk.END)
                self.course_desc_text.insert("1.0", course_details.get(db_schema.COL_COURSE_DESCRIPTION, ""))
                self.update_course_btn.config(state="normal"); self.delete_course_btn.config(state="normal"); self.add_course_btn.config(state="disabled")
        except DatabaseOperationError as e: messagebox.showerror(_("db_error_title"), _("training_course_error_loading_details", error=e), parent=self)

    def _gui_add_course(self):
        name = self.course_form_vars[db_schema.COL_COURSE_NAME].get().strip()
        provider = self.course_form_vars[db_schema.COL_COURSE_PROVIDER].get().strip()
        duration_str = self.course_form_vars[db_schema.COL_COURSE_DEFAULT_DURATION_HOURS].get().strip()
        description = self.course_desc_text.get("1.0", tk.END).strip()
        duration = float(duration_str) if duration_str else None
        try:
            db_queries.add_training_course_db(name, description, provider, duration)
            messagebox.showinfo(_("success_title"), _("training_course_add_success", name=name), parent=self)
            self._load_courses_to_tree()
        except (InvalidInputError, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_update_course(self):
        if self.current_selected_course_id is None: return
        name = self.course_form_vars[db_schema.COL_COURSE_NAME].get().strip()
        provider = self.course_form_vars[db_schema.COL_COURSE_PROVIDER].get().strip()
        duration_str = self.course_form_vars[db_schema.COL_COURSE_DEFAULT_DURATION_HOURS].get().strip()
        description = self.course_desc_text.get("1.0", tk.END).strip()
        duration = float(duration_str) if duration_str else None
        try:
            db_queries.update_training_course_db(self.current_selected_course_id, name, description, provider, duration)
            messagebox.showinfo(_("success_title"), _("training_course_update_success", name=name), parent=self)
            self._load_courses_to_tree()
        except (InvalidInputError, HRException, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_delete_course(self):
        if self.current_selected_course_id is None: return
        name = self.course_form_vars[db_schema.COL_COURSE_NAME].get()
        if messagebox.askyesno(_("confirm_delete_title"), _("training_course_delete_confirm", name=name), parent=self):
            try:
                db_queries.delete_training_course_db(self.current_selected_course_id)
                messagebox.showinfo(_("success_title"), _("training_course_delete_success", name=name), parent=self)
                self._load_courses_to_tree()
            except (HRException, DatabaseOperationError) as e: messagebox.showerror(_("error_title"), str(e), parent=self)

    def _gui_clear_course_form(self):
        self.current_selected_course_id = None
        for var in self.course_form_vars.values(): var.set("")
        self.course_desc_text.delete("1.0", tk.END)
        self.add_course_btn.config(state="normal"); self.update_course_btn.config(state="disabled"); self.delete_course_btn.config(state="disabled")
        if self.course_tree.selection(): self.course_tree.selection_remove(self.course_tree.selection())
        if hasattr(self.course_form_vars[db_schema.COL_COURSE_NAME], 'focus_set'): # Check if it's an Entry
            self.course_form_vars[db_schema.COL_COURSE_NAME].focus_set()

    def update_local_theme_elements(self):
        super().update_local_theme_elements()
        if hasattr(self, 'course_desc_text') and self.course_desc_text.winfo_exists():
            palette = get_theme_palette_global(self.parent_app.get_current_theme())
            _theme_text_widget_global(self.course_desc_text, palette)