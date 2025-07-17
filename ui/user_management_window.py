# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\user_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import sys # For path manipulation
import os # For path manipulation

# Add the project root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from ttkbootstrap.tooltip import ToolTip # Added for tooltips
# --- Project-specific imports ---
from data import database as db_schema # For constants like VALID_ROLES, COL_USER_ID, BS_...
from data import queries as db_queries # For user DB functions
from utils.localization import _ # For _() # pragma: no cover
from utils.exceptions import DatabaseOperationError, InvalidInputError, UserNotFoundError # Import custom exceptions
from utils.gui_utils import extract_id_from_combobox_selection, populate_employee_combobox # If used
from .themed_toplevel import ThemedToplevel
from .components import AutocompleteCombobox # If used for linking employees

logger = logging.getLogger(__name__)

class UserManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("user_management_window_title")) # Add this key
        self.geometry("750x500") # Adjust as needed
        self.translatable_widgets_user_mgt = []
        self.current_selected_user_id = None

        self._create_user_management_widgets() # Create the UI
        self._load_users_to_tree() # Initial load

    def _create_user_management_widgets(self):
        main_frame = ttkb.Frame(self, padding="12") # Parent is self
        main_frame.pack(expand=True, fill="both")


        # --- User List (Left) ---
        list_frame = ttkb.LabelFrame(main_frame, text=_("user_list_frame_title"), padding="10") # Add key
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5)) # Use attr="title" for LabelFrames
        self._add_translatable_widget_user_mgt(list_frame, "user_list_frame_title", attr="title")

        self.user_tree_cols = (db_schema.COL_USER_ID, db_schema.COL_USER_USERNAME, db_schema.COL_USER_ROLE, "linked_employee_display") # Define columns
        self.user_tree = ttkb.Treeview(list_frame, columns=self.user_tree_cols, show="headings") # Create treeview
        # Headers will be set/updated in refresh_ui_for_language or a dedicated _update_headers method

        self.user_tree.column(db_schema.COL_USER_ID, width=50, anchor="e", stretch=tk.NO)
        self.user_tree.column(db_schema.COL_USER_USERNAME, width=150)
        self.user_tree.column(db_schema.COL_USER_ROLE, width=120)
        self.user_tree.column("linked_employee_display", width=200, stretch=tk.YES)

        user_scrollbar = ttkb.Scrollbar(list_frame, orient="vertical", command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=user_scrollbar.set)
        self.user_tree.pack(side="left", fill="both", expand=True)
        user_scrollbar.pack(side="right", fill="y") # Pack scrollbar
        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        # --- User Form (Right) ---
        form_frame = ttkb.LabelFrame(main_frame, text=_("user_details_frame_title"), padding="10") # Add key
        form_frame.pack(side="right", fill="y", padx=(5, 0)) # Use attr="title" for LabelFrames
        self._add_translatable_widget_user_mgt(form_frame, "user_details_frame_title", attr="title")
        form_frame.columnconfigure(1, weight=1) # Make entry column expand

        # Username
        username_lbl = ttkb.Label(form_frame, text=_("user_username_label")); username_lbl.grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_user_mgt(username_lbl, "user_username_label")
        self.username_var = tk.StringVar()
        self.username_entry = ttkb.Entry(form_frame, textvariable=self.username_var, width=30)
        self.username_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Password
        password_lbl = ttkb.Label(form_frame, text=_("user_password_label")); password_lbl.grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_user_mgt(password_lbl, "user_password_label")
        self.password_var = tk.StringVar()
        self.password_entry = ttkb.Entry(form_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        password_hint_lbl = ttk.Label(form_frame, text=_("user_password_hint_label")); password_hint_lbl.grid(row=1, column=2, sticky="w", padx=5, pady=3) # Add key
        self._add_translatable_widget_user_mgt(password_hint_lbl, "user_password_hint_label")

        # Role
        role_lbl = ttkb.Label(form_frame, text=_("user_role_label")); role_lbl.grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_user_mgt(role_lbl, "user_role_label")
        self.role_var = tk.StringVar()
        self.role_combo = ttkb.Combobox(form_frame, textvariable=self.role_var, values=db_schema.VALID_ROLES, state="readonly", width=28)
        self.role_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        self.role_combo.set(db_schema.ROLE_EMPLOYEE) # Default

        # Linked Employee
        linked_emp_lbl = ttkb.Label(form_frame, text=_("user_linked_employee_label")); linked_emp_lbl.grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_user_mgt(linked_emp_lbl, "user_linked_employee_label") # Use helper
        self.linked_emp_var = tk.StringVar()
        self.linked_emp_combo = AutocompleteCombobox(form_frame, textvariable=self.linked_emp_var, width=28, completevalues=[]) # Initialize with empty list
        # populate_employee_combobox(self.linked_emp_combo, db_queries.list_all_employees, include_active_only=False, empty_option_text="None") # Populate after db_queries is fully set up
        ToolTip(self.linked_emp_combo, text=_("user_linked_employee_tooltip")) # Add key for tooltip
        self.linked_emp_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=3)


        # Action Buttons
        buttons_frame = ttkb.Frame(form_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, pady=15, sticky="ew")

        self.add_user_btn = ttkb.Button(buttons_frame, text=_("user_add_button"), command=self._gui_add_user, bootstyle=db_schema.BS_ADD)
        self.add_user_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget_user_mgt(self.add_user_btn, "user_add_button")

        self.update_user_btn = ttkb.Button(buttons_frame, text=_("user_update_button"), command=self._gui_update_user, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.update_user_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget_user_mgt(self.update_user_btn, "user_update_button")

        self.delete_user_btn = ttkb.Button(buttons_frame, text=_("user_delete_button"), command=self._gui_delete_user, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_user_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget_user_mgt(self.delete_user_btn, "user_delete_button")

        self.clear_user_form_btn = ttkb.Button(buttons_frame, text=_("user_clear_button"), command=self._gui_clear_user_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_user_form_btn.pack(side="left", padx=3, fill="x", expand=True)
        self._add_translatable_widget_user_mgt(self.clear_user_form_btn, "user_clear_button")    
        self._populate_linked_employee_combobox() # Call after other widgets are set up

    def _add_translatable_widget_user_mgt(self, widget, key: str, attr: str = "text"): # pragma: no cover
        """Helper to register translatable widgets for UserManagementWindow."""
        # Ensure attr is "title" for LabelFrames if not specified or specified as "text"
        if isinstance(widget, ttk.LabelFrame) and attr == "text":
            actual_attr = "title"
        else:
            actual_attr = attr
        self.translatable_widgets_user_mgt.append({"widget": widget, "key": key, "attr": actual_attr})

    def _update_user_tree_headers(self):
        if hasattr(self, 'user_tree') and self.user_tree.winfo_exists():
            self.user_tree.heading(db_schema.COL_USER_ID, text=_("user_id_header")) # Add key
            self.user_tree.heading(db_schema.COL_USER_USERNAME, text=_("user_username_header"))
            self.user_tree.heading(db_schema.COL_USER_ROLE, text=_("user_role_header"))
            self.user_tree.heading("linked_employee_display", text=_("user_linked_employee_header"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("user_management_window_title"))
        self._update_user_tree_headers()
        for item_info in self.translatable_widgets_user_mgt:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text") # Default to "text"

            if widget.winfo_exists():
                try:
                    widget.config(**{attr_to_update: _(key)})
                except tk.TclError: pass # Widget might not support the attribute or was destroyed
        # Repopulate comboboxes if their content depends on language (e.g., "None" option)
        self._populate_linked_employee_combobox()


    def _populate_linked_employee_combobox(self): # pragma: no cover
        populate_employee_combobox(self.linked_emp_combo, db_queries.get_all_employees_db, include_active_only=False, empty_option_text=_("user_no_linked_employee_option"))

    def _load_users_to_tree(self): # Copied from HRAppGUI
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        try:
            users = db_queries.get_all_users_db()
            for user in users:
                # Fetch employee name if linked_emp_id exists
                emp_name_display = ""
                if user.get(db_schema.COL_USER_LINKED_EMP_ID):
                    emp_details = db_queries.view_employee_details(user[db_schema.COL_USER_LINKED_EMP_ID])
                    if emp_details: emp_name_display = f" ({emp_details[db_schema.COL_EMP_NAME]})"

                # Construct the linked employee display string safely
                linked_emp_id_val = user.get(db_schema.COL_USER_LINKED_EMP_ID) # Get the raw value, could be None
                linked_emp_display = ""
                if linked_emp_id_val:
                    linked_emp_display = str(linked_emp_id_val) + emp_name_display # Concatenate ID (as string) and name display
                self.user_tree.insert("", "end", values=(user[db_schema.COL_USER_ID], user[db_schema.COL_USER_USERNAME], user[db_schema.COL_USER_ROLE], linked_emp_display))
        except DatabaseOperationError as e:
            messagebox.showerror(localization._("user_admin_error_title"), localization._("user_admin_load_users_error", error=e), parent=self)
        except Exception as e: # pragma: no cover
            logger.error(f"Unexpected error loading users: {e}", exc_info=True)
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_load_users_unexpected_error", error=e), parent=self)

    def _on_user_select(self, event=None):
        selected_item_iid = self.user_tree.focus()
        if not selected_item_iid:
            self.current_selected_user_id = None
            self._gui_clear_user_form()
            return
        
        # The IID is the user_id from the first column
        self.current_selected_user_id = int(self.user_tree.item(selected_item_iid, "values")[0])
        
        try:
            user_details = db_queries.get_user_by_id_db(self.current_selected_user_id)
            if not user_details:
                messagebox.showerror(_("user_admin_error_title"), _("user_not_found_error"), parent=self)
                self._gui_clear_user_form()
                return

            self.username_var.set(user_details[db_schema.COL_USER_USERNAME])
            self.username_entry.config(state="readonly") # Username is key, don't allow edit directly
            self.password_var.set("") # Clear password field, admin should type new if changing
            self.role_var.set(user_details[db_schema.COL_USER_ROLE])
            
            # Set linked employee combobox
            linked_emp_id = user_details.get(db_schema.COL_USER_LINKED_EMP_ID)
            if linked_emp_id:
                emp_details = db_queries.view_employee_details(linked_emp_id)
                self.linked_emp_var.set(f"{emp_details[db_schema.COL_EMP_NAME]} ({emp_details[db_schema.COL_EMP_ID]})" if emp_details else _("user_no_linked_employee_option"))
            else:
                self.linked_emp_var.set(_("user_no_linked_employee_option"))

            self.update_user_btn.config(state="normal")
            # Prevent deleting self - ensure parent_app and current_user_details are available
            is_current_user = self.parent_app and self.parent_app.current_user_details and user_details[db_schema.COL_USER_ID] == self.parent_app.current_user_details.get(db_schema.COL_USER_ID)
            self.delete_user_btn.config(state="normal" if not is_current_user else "disabled")
            self.add_user_btn.config(state="disabled") # Disable add button when editing
        except DatabaseOperationError as e:
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_load_details_error", error=e), parent=self)
            self._gui_clear_user_form()
        except Exception as e: # pragma: no cover
            logger.error(f"Unexpected error selecting user: {e}", exc_info=True)
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_load_details_unexpected_error", error=e), parent=self)
            self._gui_clear_user_form()

    def _gui_add_user(self):
        username = self.username_var.get().strip()
        password = self.password_var.get() # No strip, password can have spaces
        role = self.role_var.get()
        linked_emp_selection = self.linked_emp_var.get()
        linked_emp_id = extract_id_from_combobox_selection(linked_emp_selection) if linked_emp_selection != _("user_no_linked_employee_option") else None
        
        if not username or not password:
            messagebox.showerror(_("input_error_title"), _("user_admin_username_password_required_error"), parent=self)
            return
        try:
            db_queries.add_user_db(username, password, role, linked_emp_id)
            messagebox.showinfo(_("success_title"), _("user_added_success_message", username=username, role=role), parent=self)
            self._load_users_to_tree()
            self._gui_clear_user_form()
        except (InvalidInputError, DatabaseOperationError) as e:
            messagebox.showerror(_("user_admin_add_error_title"), str(e), parent=self)
        except Exception as e: # pragma: no cover
            logger.error(f"Unexpected error adding user: {e}", exc_info=True)
            messagebox.showerror(_("user_admin_add_error_title"), _("user_admin_add_unexpected_error", error=e), parent=self)

    def _gui_update_user(self):
        user_id = self.current_selected_user_id
        if user_id is None:
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_select_user_update_error"), parent=self) # pragma: no cover
            return
        
        new_password = self.password_var.get()
        new_role = self.role_var.get()
        linked_emp_selection = self.linked_emp_var.get()
        new_linked_emp_id = extract_id_from_combobox_selection(linked_emp_selection) if linked_emp_selection != _("user_no_linked_employee_option") else None

        try:
            # Corrected function call to update_user_db
            # The username is not updated from this form, so pass None for it.
            # The set_emp_id_null parameter defaults to False, which is fine here.
            # If new_linked_emp_id is None and we want to explicitly set it to NULL in DB,
            # we might need to pass set_emp_id_null=True if new_linked_emp_id is None.
            # For now, assuming new_linked_emp_id=None will correctly set it to NULL.
            db_queries.update_user_db(user_id, username=None, password=(new_password if new_password else None), role=new_role, employee_id=new_linked_emp_id) # type: ignore
            messagebox.showinfo(_("success_title"), _("user_updated_success_message", username=self.username_var.get()), parent=self)
            self._load_users_to_tree() # Refresh user list
            self._gui_clear_user_form() # Clear form
        except (InvalidInputError, DatabaseOperationError, UserNotFoundError) as e:
            messagebox.showerror(_("user_admin_update_error_title"), str(e), parent=self)
        except Exception as e: # pragma: no cover
            logger.error(f"Unexpected error updating user: {e}", exc_info=True)
            messagebox.showerror(_("user_admin_update_error_title"), _("user_admin_update_unexpected_error", error=e), parent=self)

    def _gui_delete_user(self):
        user_id = self.current_selected_user_id
        username = self.username_var.get()
        if user_id is None:
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_select_user_delete_error"), parent=self) # pragma: no cover
            return
        
        if self.parent_app and self.parent_app.current_user_details and user_id == self.parent_app.current_user_details.get(db_schema.COL_USER_ID):
            messagebox.showerror(_("user_admin_error_title"), _("user_admin_cannot_delete_self_error"), parent=self)
            return

        if messagebox.askyesno(_("confirm_delete_title"), _("user_admin_confirm_delete_message", username=username), parent=self):
            try:
                db_queries.delete_user_db(user_id)
                messagebox.showinfo(_("success_title"), _("user_deleted_success_message", username=username), parent=self)
                self._load_users_to_tree()
                self._gui_clear_user_form()
            except (DatabaseOperationError, UserNotFoundError) as e:
                messagebox.showerror(_("user_admin_delete_error_title"), str(e), parent=self)
            except Exception as e: # pragma: no cover
                logger.error(f"Unexpected error deleting user: {e}", exc_info=True)
                messagebox.showerror(_("user_admin_delete_error_title"), _("user_admin_delete_unexpected_error", error=e), parent=self)

    def _gui_clear_user_form(self):
        self.current_selected_user_id = None
        self.username_var.set("")
        self.username_entry.config(state="normal")
        self.password_var.set("")
        self.role_var.set(db_schema.ROLE_EMPLOYEE)
        self.linked_emp_var.set(_("user_no_linked_employee_option"))
        if self.user_tree.selection():
            self.user_tree.selection_remove(self.user_tree.selection())
        self.update_user_btn.config(state="disabled")
        self.delete_user_btn.config(state="disabled")
        self.add_user_btn.config(state="normal") # Enable add button when form is clear
        self.username_entry.focus_set() # Set focus to username field

    # No need to override update_local_theme_elements unless there are non-ttk widgets
    # that need specific theming beyond what ThemedToplevel handles.
    # The current UI uses only ttk widgets and a standard tk.Text (which is handled by ThemedToplevel).
    # def update_local_theme_elements(self):
    #     super().update_local_theme_elements() # Call parent's theming
    #     # Add any UserManagementWindow-specific theming here if needed.
 
