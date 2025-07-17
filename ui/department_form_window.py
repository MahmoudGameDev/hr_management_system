# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\department_form_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging

# --- Project-specific imports ---
from data import database as db_schema # For constants like COL_DEPT_NAME
from data import queries as db_queries # For functions like list_departments_db, add_department_db
from utils import localization # For _()
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # Added import
from .themed_toplevel import ThemedToplevel # Base class for themed modal windows

logger = logging.getLogger(__name__)

class DepartmentManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("department_management_window_title")) # Add this key to localization files
        self.geometry("900x700+100+50") # Adjust as needed
        self.translatable_widgets_dept = [] # For this window's specific translatable widgets

        # --- Main Frame ---
        main_frame = ttkb.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # --- Department List (Left) ---
        list_frame = ttkb.LabelFrame(main_frame, text=localization._("department_list_frame_title"), padding="10") # Add key
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._add_translatable_widget_dept(list_frame, "department_list_frame_title")


        self.dept_tree = ttkb.Treeview(list_frame, columns=(db_schema.COL_DEPT_ID, db_schema.COL_DEPT_NAME, "employee_count"), show="headings")
        self.dept_tree.heading(db_schema.COL_DEPT_ID, text=localization._("dept_id_header")) # Add key
        self.dept_tree.heading(db_schema.COL_DEPT_NAME, text=localization._("dept_name_header")) # Add key
        self.dept_tree.heading("employee_count", text=localization._("dept_emp_count_header")) # Add key

        self.dept_tree.column(db_schema.COL_DEPT_ID, width=50, anchor="e", stretch=tk.NO)
        self.dept_tree.column(db_schema.COL_DEPT_NAME, width=200, stretch=tk.YES)
        self.dept_tree.column("employee_count", width=100, anchor="e")

        dept_scrollbar = ttkb.Scrollbar(list_frame, orient="vertical", command=self.dept_tree.yview)
        self.dept_tree.configure(yscrollcommand=dept_scrollbar.set)
        self.dept_tree.pack(side="left", fill="both", expand=True)
        dept_scrollbar.pack(side="right", fill="y")
        self.dept_tree.bind("<<TreeviewSelect>>", self._on_department_select)

        # --- Department Form (Right) ---
        form_frame = ttkb.LabelFrame(main_frame, text=localization._("department_details_frame_title"), padding="10") # Add key
        form_frame.pack(side="right", fill="y", padx=(5, 0))
        self._add_translatable_widget_dept(form_frame, "department_details_frame_title")


        # Department Name
        name_lbl = ttkb.Label(form_frame, text=localization._("dept_name_label")) # Add key
        name_lbl.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget_dept(name_lbl, "dept_name_label")
        self.dept_name_var = tk.StringVar()
        self.dept_name_entry = ttkb.Entry(form_frame, textvariable=self.dept_name_var, width=30)
        self.dept_name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Department Description
        desc_lbl = ttkb.Label(form_frame, text=localization._("dept_description_label")) # Add key
        desc_lbl.grid(row=1, column=0, sticky="nw", padx=5, pady=5)
        self._add_translatable_widget_dept(desc_lbl, "dept_description_label")
        self.dept_desc_text = tk.Text(form_frame, height=5, width=30, relief="solid", borderwidth=1)
        self.dept_desc_text.grid(row=1, column=1, padx=5, pady=5)
        # Apply theme to Text widget
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.dept_desc_text, palette)


        # Action Buttons
        buttons_frame = ttkb.Frame(form_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.add_dept_btn = ttkb.Button(buttons_frame, text=localization._("dept_add_button"), command=self._gui_add_department, bootstyle=SUCCESS) # Add key
        self.add_dept_btn.pack(side="left", padx=5)
        self._add_translatable_widget_dept(self.add_dept_btn, "dept_add_button")

        self.update_dept_btn = ttkb.Button(buttons_frame, text=localization._("dept_update_button"), command=self._gui_update_department, state="disabled", bootstyle=PRIMARY) # Add key
        self.update_dept_btn.pack(side="left", padx=5)
        self._add_translatable_widget_dept(self.update_dept_btn, "dept_update_button")

        self.delete_dept_btn = ttkb.Button(buttons_frame, text=localization._("dept_delete_button"), command=self._gui_delete_department, state="disabled", bootstyle=DANGER) # Add key
        self.delete_dept_btn.pack(side="left", padx=5)
        self._add_translatable_widget_dept(self.delete_dept_btn, "dept_delete_button")

        self.clear_dept_form_btn = ttkb.Button(buttons_frame, text=localization._("dept_clear_button"), command=self._gui_clear_department_form, bootstyle=LIGHT) # Add key
        self.clear_dept_form_btn.pack(side="left", padx=5)
        self._add_translatable_widget_dept(self.clear_dept_form_btn, "dept_clear_button")

        self._load_departments_to_tree()
        self.current_selected_dept_id = None

        # Call refresh_ui_for_language after all widgets are created
        # ThemedToplevel's _deferred_theme_update will call update_local_theme_elements,
        # which can be overridden to also call refresh_ui_for_language.
        # Or call it explicitly here if needed after a short delay.

    def _add_translatable_widget_dept(self, widget, key):
        """Helper to register translatable widgets for this window.
        """
        attr = "text"
        if isinstance(widget, ttkb.LabelFrame):
            attr = "title"
        self.translatable_widgets_dept.append({"widget": widget, "key": key, "attr": attr})


    def refresh_ui_for_language(self): # pragma: no cover
        """Updates translatable text elements in the Department Management window."""
        self.title(localization._("department_management_window_title"))
        for item_info in self.translatable_widgets_dept:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")

            if widget.winfo_exists():
                try:
                    if attr_to_update == "text":
                        widget.config(text=localization._(key))
                    elif attr_to_update == "title": # For LabelFrames
                        widget.config(text=localization._(key))
                except tk.TclError: # For LabelFrames
                    if isinstance(widget, ttkb.LabelFrame): # Use ttkb
                        widget.config(text=localization._(key))
        # Update Treeview headers
        if hasattr(self, 'dept_tree') and self.dept_tree.winfo_exists():
            self.dept_tree.heading(db_schema.COL_DEPT_ID, text=localization._("dept_id_header"))
            self.dept_tree.heading(db_schema.COL_DEPT_NAME, text=localization._("dept_name_header"))
            self.dept_tree.heading("employee_count", text=localization._("dept_emp_count_header"))


    def _load_departments_to_tree(self):
        for item in self.dept_tree.get_children():
            self.dept_tree.delete(item)
        try:
            departments = db_queries.list_departments_db()
            for dept in departments:
                emp_count = db_queries.get_employee_count_for_department_db(dept[db_schema.COL_DEPT_ID])
                self.dept_tree.insert("", "end", values=(dept[db_schema.COL_DEPT_ID], dept[db_schema.COL_DEPT_NAME], emp_count), iid=dept[db_schema.COL_DEPT_ID])
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("db_error_title"), str(e), parent=self)
        self._gui_clear_department_form() # Clear form and reset buttons

    def _on_department_select(self, event=None):
        selected_item_iid = self.dept_tree.focus()
        if not selected_item_iid:
            self._gui_clear_department_form()
            return

        self.current_selected_dept_id = int(selected_item_iid)
        try:
            dept_details = db_queries.get_department_by_id_db(self.current_selected_dept_id)
            if dept_details:
                self.dept_name_var.set(dept_details.get(db_schema.COL_DEPT_NAME, ""))
                self.dept_desc_text.delete("1.0", tk.END)
                self.dept_desc_text.insert("1.0", dept_details.get(db_schema.COL_DEPT_DESCRIPTION, ""))
                self.update_dept_btn.config(state="normal")
                self.delete_dept_btn.config(state="normal")
                self.add_dept_btn.config(state="disabled")
            else:
                self._gui_clear_department_form() # Should not happen if ID is from tree
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("db_error_title"), localization._("dept_error_loading_details", error=e), parent=self)
            self._gui_clear_department_form()

    def _gui_add_department(self):
        dept_name = self.dept_name_var.get().strip()
        dept_desc = self.dept_desc_text.get("1.0", tk.END).strip()

        if not dept_name:
            messagebox.showwarning(localization._("input_error_title"), localization._("dept_name_required_error"), parent=self)
            return

        try:
            db_queries.add_department_db(dept_name, dept_desc)
            messagebox.showinfo(localization._("success_title"), localization._("dept_add_success_message", name=dept_name), parent=self)
            self._load_departments_to_tree() # Refresh list
            # self._gui_clear_department_form() # Already called by _load_departments_to_tree
        except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(localization._("error_title"), localization._("dept_add_error_message", error=e), parent=self)
        except Exception as e_generic:
            logger.error(f"Unexpected error adding department: {e_generic}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("dept_add_error_message", error=e_generic), parent=self)

    def _gui_update_department(self):
        if self.current_selected_dept_id is None:
            messagebox.showwarning(localization._("warning_title"), localization._("dept_select_to_update_warning"), parent=self)
            return

        dept_name = self.dept_name_var.get().strip()
        dept_desc = self.dept_desc_text.get("1.0", tk.END).strip()

        if not dept_name:
            messagebox.showwarning(localization._("input_error_title"), localization._("dept_name_required_error"), parent=self)
            return

        try:
            db_queries.update_department_db(self.current_selected_dept_id, dept_name, dept_desc)
            messagebox.showinfo(localization._("success_title"), localization._("dept_update_success_message", name=dept_name), parent=self)
            self._load_departments_to_tree()
        except (db_queries.InvalidInputError, db_queries.DepartmentNotFoundError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(localization._("error_title"), localization._("dept_update_error_message", error=e), parent=self)
        except Exception as e_generic:
            logger.error(f"Unexpected error updating department: {e_generic}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("dept_update_error_message", error=e_generic), parent=self)

    def _gui_delete_department(self):
        if self.current_selected_dept_id is None:
            messagebox.showwarning(localization._("warning_title"), localization._("dept_select_to_delete_warning"), parent=self)
            return

        dept_name = self.dept_name_var.get().strip() # For the confirmation message
        if messagebox.askyesno(localization._("confirm_delete_title"), localization._("dept_delete_confirm_message", name=dept_name), parent=self):
            try:
                db_queries.delete_department_db(self.current_selected_dept_id)
                messagebox.showinfo(localization._("success_title"), localization._("dept_delete_success_message", name=dept_name), parent=self)
                self._load_departments_to_tree()
            except (db_queries.DepartmentNotFoundError, db_queries.DatabaseOperationError) as e: # Catch specific errors
                messagebox.showerror(localization._("error_title"), localization._("dept_delete_error_message", error=e), parent=self)
            except Exception as e_generic:
                logger.error(f"Unexpected error deleting department: {e_generic}", exc_info=True)
                messagebox.showerror(localization._("error_title"), localization._("dept_delete_error_message", error=e_generic), parent=self)

    def _gui_clear_department_form(self):
        self.current_selected_dept_id = None
        self.dept_name_var.set("")
        self.dept_desc_text.delete("1.0", tk.END)
        self.dept_name_entry.focus_set()
        self.add_dept_btn.config(state="normal")
        self.update_dept_btn.config(state="disabled")
        self.delete_dept_btn.config(state="disabled")
        if self.dept_tree.selection():
            self.dept_tree.selection_remove(self.dept_tree.selection())

    # Override update_local_theme_elements if this window has its own non-ttk widgets
    # that need specific theming beyond what ThemedToplevel handles.
    def update_local_theme_elements(self):
        super().update_local_theme_elements()
        # Theme the tk.Text widget for department description
        if hasattr(self, 'dept_desc_text') and self.dept_desc_text.winfo_exists():
            palette = get_theme_palette_global(self.parent_app.get_current_theme())
            _theme_text_widget_global(self.dept_desc_text, palette)
