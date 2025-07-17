# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\evaluation_criteria_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging
from typing import List, Dict, Optional # Added Dict and Optional

# --- Project-specific imports ---
from data import database as db_schema # For COL_CRITERIA_... constants
from data import queries as db_queries # For criteria DB functions
from utils import localization # For _()
from utils.exceptions import InvalidInputError, DatabaseOperationError, HRException # Import exceptions
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # For theming tk.Text
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class EvaluationCriteriaWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("eval_criteria_window_title"))
        self.geometry("700x500")
        self.translatable_widgets_criteria = []
        self.current_selected_criteria_id = None

        # --- Main Frame ---
        main_frame = ttkb.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # --- Criteria List (Left) ---
        list_lf_key = "eval_criteria_list_frame_title"
        list_frame = ttkb.LabelFrame(main_frame, text=localization._(list_lf_key), padding="10")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._add_translatable_widget(list_frame, list_lf_key, attr="title")

        self.criteria_tree_cols = (db_schema.COL_CRITERIA_ID, db_schema.COL_CRITERIA_NAME, db_schema.COL_CRITERIA_MAX_POINTS)
        self.criteria_tree = ttkb.Treeview(list_frame, columns=self.criteria_tree_cols, show="headings")
        self._update_criteria_tree_headers()

        self.criteria_tree.column(db_schema.COL_CRITERIA_ID, width=50, anchor="e", stretch=tk.NO)
        self.criteria_tree.column(db_schema.COL_CRITERIA_NAME, width=200, stretch=tk.YES)
        self.criteria_tree.column(db_schema.COL_CRITERIA_MAX_POINTS, width=100, anchor="e")

        criteria_scrollbar = ttkb.Scrollbar(list_frame, orient="vertical", command=self.criteria_tree.yview)
        self.criteria_tree.configure(yscrollcommand=criteria_scrollbar.set)
        self.criteria_tree.pack(side="left", fill="both", expand=True)
        criteria_scrollbar.pack(side="right", fill="y")
        self.criteria_tree.bind("<<TreeviewSelect>>", self._on_criteria_select)

        # --- Criteria Form (Right) ---
        form_lf_key = "eval_criteria_details_frame_title"
        form_frame = ttkb.LabelFrame(main_frame, text=localization._(form_lf_key), padding="10")
        form_frame.pack(side="right", fill="y", padx=(5, 0))
        self._add_translatable_widget(form_frame, form_lf_key, attr="title")
        form_frame.columnconfigure(1, weight=1)

        # Criterion Name
        name_lbl_key = "eval_criteria_name_label"
        ttk.Label(form_frame, text=localization._(name_lbl_key)).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=0,column=0)[0], name_lbl_key)
        self.criteria_name_var = tk.StringVar()
        self.criteria_name_entry = ttkb.Entry(form_frame, textvariable=self.criteria_name_var, width=30)
        self.criteria_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Max Points
        points_lbl_key = "eval_criteria_max_points_label"
        ttk.Label(form_frame, text=localization._(points_lbl_key)).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=1,column=0)[0], points_lbl_key)
        self.criteria_points_var = tk.StringVar(value="10")
        self.criteria_points_spin = ttkb.Spinbox(form_frame, from_=1, to=100, textvariable=self.criteria_points_var, width=5)
        self.criteria_points_spin.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        # Description
        desc_lbl_key = "eval_criteria_description_label"
        ttk.Label(form_frame, text=localization._(desc_lbl_key)).grid(row=2, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget(form_frame.grid_slaves(row=2,column=0)[0], desc_lbl_key)
        self.criteria_desc_text = tk.Text(form_frame, height=5, width=30, relief="solid", borderwidth=1)
        self.criteria_desc_text.grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.criteria_desc_text, palette)

        # Action Buttons
        buttons_frame = ttkb.Frame(form_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=15, sticky="ew")

        add_btn_key = "eval_criteria_add_button"
        self.add_criteria_btn = ttkb.Button(buttons_frame, text=localization._(add_btn_key), command=self._gui_add_criterion, bootstyle=db_schema.BS_ADD)
        self.add_criteria_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.add_criteria_btn, add_btn_key)

        update_btn_key = "eval_criteria_update_button"
        self.update_criteria_btn = ttkb.Button(buttons_frame, text=localization._(update_btn_key), command=self._gui_update_criterion, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.update_criteria_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.update_criteria_btn, update_btn_key)

        delete_btn_key = "eval_criteria_delete_button"
        self.delete_criteria_btn = ttkb.Button(buttons_frame, text=localization._(delete_btn_key), command=self._gui_delete_criterion, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_criteria_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.delete_criteria_btn, delete_btn_key)

        clear_btn_key = "eval_criteria_clear_button"
        self.clear_criteria_form_btn = ttkb.Button(buttons_frame, text=localization._(clear_btn_key), command=self._gui_clear_criteria_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_criteria_form_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget(self.clear_criteria_form_btn, clear_btn_key)

        self._load_criteria_to_tree()

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_criteria.append({"widget": widget, "key": key, "attr": attr})

    def _update_criteria_tree_headers(self):
        if hasattr(self, 'criteria_tree') and self.criteria_tree.winfo_exists():
            self.criteria_tree.heading(db_schema.COL_CRITERIA_ID, text=localization._("eval_criteria_header_id"))
            self.criteria_tree.heading(db_schema.COL_CRITERIA_NAME, text=localization._("eval_criteria_header_name"))
            self.criteria_tree.heading(db_schema.COL_CRITERIA_MAX_POINTS, text=localization._("eval_criteria_header_max_points"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("eval_criteria_window_title"))
        self._update_criteria_tree_headers()
        for item in self.translatable_widgets_criteria:
            widget = item["widget"]
            key = item["key"]
            attr = item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title": # For LabelFrames
                         widget.config(text=localization._(key))
                except tk.TclError: pass

    def _load_criteria_to_tree(self):
        for item in self.criteria_tree.get_children():
            self.criteria_tree.delete(item)
        try:
            criteria_list = db_queries.list_evaluation_criteria_db()
            for criterion in criteria_list:
                self.criteria_tree.insert("", "end", iid=criterion[db_schema.COL_CRITERIA_ID], values=(
                    criterion[db_schema.COL_CRITERIA_ID],
                    criterion[db_schema.COL_CRITERIA_NAME],
                    criterion[db_schema.COL_CRITERIA_MAX_POINTS]
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("db_error_title"), str(e), parent=self)
        self._gui_clear_criteria_form() # Reset form and buttons

    def _on_criteria_select(self, event=None):
        selected_item_iid = self.criteria_tree.focus()
        if not selected_item_iid:
            self._gui_clear_criteria_form()
            return

        self.current_selected_criteria_id = int(selected_item_iid)
        try:
            # Assuming a function get_evaluation_criterion_by_id_db exists or adapt
            # For now, let's assume list_evaluation_criteria_db can be filtered if no direct get_by_id
            criteria_list = db_queries.list_evaluation_criteria_db()
            criterion_details = next((c for c in criteria_list if c[db_schema.COL_CRITERIA_ID] == self.current_selected_criteria_id), None)

            if criterion_details:
                self.criteria_name_var.set(criterion_details.get(db_schema.COL_CRITERIA_NAME, ""))
                self.criteria_points_var.set(str(criterion_details.get(db_schema.COL_CRITERIA_MAX_POINTS, 10)))
                self.criteria_desc_text.delete("1.0", tk.END)
                self.criteria_desc_text.insert("1.0", criterion_details.get(db_schema.COL_CRITERIA_DESCRIPTION, ""))
                
                self.update_criteria_btn.config(state="normal")
                self.delete_criteria_btn.config(state="normal")
                self.add_criteria_btn.config(state="disabled")
            else:
                self._gui_clear_criteria_form() # Should not happen if ID is from tree
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("db_error_title"), localization._("eval_criteria_error_loading_details", error=e), parent=self) # Add key
            self._gui_clear_criteria_form()

    def _gui_add_criterion(self):
        name = self.criteria_name_var.get().strip()
        description = self.criteria_desc_text.get("1.0", tk.END).strip()
        try:
            max_points = int(self.criteria_points_var.get())
        except ValueError:
            messagebox.showwarning(localization._("input_error_title"), localization._("eval_criteria_max_points_invalid_error"), parent=self) # Add key
            return

        if not name:
            messagebox.showwarning(localization._("input_error_title"), localization._("eval_criteria_name_required_error"), parent=self) # Add key
            return

        try:
            db_queries.add_evaluation_criterion_db(name, description, max_points)
            messagebox.showinfo(localization._("success_title"), localization._("eval_criteria_add_success", name=name), parent=self) # Add key
            self._load_criteria_to_tree()
        except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(localization._("error_title"), str(e), parent=self)

    def _gui_update_criterion(self):
        if self.current_selected_criteria_id is None:
            messagebox.showwarning(localization._("warning_title"), localization._("eval_criteria_select_to_update_warning"), parent=self) # Add key
            return

        name = self.criteria_name_var.get().strip()
        description = self.criteria_desc_text.get("1.0", tk.END).strip()
        try:
            max_points = int(self.criteria_points_var.get())
        except ValueError:
            messagebox.showwarning(localization._("input_error_title"), localization._("eval_criteria_max_points_invalid_error"), parent=self)
            return

        if not name:
            messagebox.showwarning(localization._("input_error_title"), localization._("eval_criteria_name_required_error"), parent=self)
            return

        try:
            db_queries.update_evaluation_criterion_db(self.current_selected_criteria_id, name, description, max_points)
            messagebox.showinfo(localization._("success_title"), localization._("eval_criteria_update_success", name=name), parent=self) # Add key
            self._load_criteria_to_tree()
        except (db_queries.InvalidInputError, db_queries.HRException, db_queries.DatabaseOperationError) as e: # HRException for "not found"
            messagebox.showerror(localization._("error_title"), str(e), parent=self)

    def _gui_delete_criterion(self):
        if self.current_selected_criteria_id is None:
            messagebox.showwarning(localization._("warning_title"), localization._("eval_criteria_select_to_delete_warning"), parent=self) # Add key
            return

        name = self.criteria_name_var.get().strip() # For confirmation message
        if messagebox.askyesno(localization._("confirm_delete_title"), localization._("eval_criteria_delete_confirm", name=name), parent=self): # Add key
            try:
                db_queries.delete_evaluation_criterion_db(self.current_selected_criteria_id)
                messagebox.showinfo(localization._("success_title"), localization._("eval_criteria_delete_success", name=name), parent=self) # Add key
                self._load_criteria_to_tree()
            except (db_queries.HRException, db_queries.DatabaseOperationError) as e: # HRException for "not found" or "in use"
                messagebox.showerror(localization._("error_title"), str(e), parent=self)

    def _gui_clear_criteria_form(self):
        self.current_selected_criteria_id = None
        self.criteria_name_var.set("")
        self.criteria_points_var.set("10") # Default max points
        self.criteria_desc_text.delete("1.0", tk.END)
        self.criteria_name_entry.focus_set()
        
        self.add_criteria_btn.config(state="normal")
        self.update_criteria_btn.config(state="disabled")
        self.delete_criteria_btn.config(state="disabled")
        if self.criteria_tree.selection():
            self.criteria_tree.selection_remove(self.criteria_tree.selection())
