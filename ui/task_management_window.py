# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\task_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, date as dt_date

# --- Project-specific imports ---
from data import database as db_schema # For COL_TASK_... constants
from data import queries as db_queries # For task DB functions
from utils.localization import _ # Import _ directly
from utils.exceptions import InvalidInputError, EmployeeNotFoundError, UserNotFoundError, DatabaseOperationError, HRException
from utils.gui_utils import populate_employee_combobox, populate_user_combobox, extract_id_from_combobox_selection
from .themed_toplevel import ThemedToplevel
from .components import AutocompleteCombobox # If used


logger = logging.getLogger(__name__)

class TaskFormWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, mode='add', task_id=None, callback_on_save=None):
        super().__init__(parent, app_instance)
        self.mode = mode
        self.task_id_to_edit = task_id
        self.callback_on_save = callback_on_save
        self.translatable_widgets_task_form = []


        form_title = _("task_form_title_add") if mode == 'add' else _("task_form_title_edit")
        self.title(form_title)
        self.geometry("550x500") # Adjusted size

        self.input_vars = {}
        self.input_widgets = {}

        self._setup_task_form_widgets()
        if self.mode == 'edit' and self.task_id_to_edit:
            self._load_task_data_for_edit()

    def _setup_task_form_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1)

        row_idx = 0

        # Task Title
        title_lbl = ttk.Label(main_frame, text=_("task_title_label")); title_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(title_lbl, "task_title_label")
        self.input_vars[db_schema.COL_TASK_TITLE] = tk.StringVar()
        self.input_widgets[db_schema.COL_TASK_TITLE] = ttk.Entry(main_frame, textvariable=self.input_vars[db_schema.COL_TASK_TITLE], width=40)
        self.input_widgets[db_schema.COL_TASK_TITLE].grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Assigned To (Employee)
        assignee_lbl = ttk.Label(main_frame, text=_("tasks_assignee_label")); assignee_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(assignee_lbl, "tasks_assignee_label")
        self.input_vars[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID] = tk.StringVar() # Stores "Name (ID)"
        self.input_widgets[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID] = AutocompleteCombobox(main_frame, textvariable=self.input_vars[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID], width=38, completevalues=[])
        populate_employee_combobox(self.input_widgets[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID], db_queries.get_all_employees_db, include_active_only=True)
        self.input_widgets[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID].grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Monitor (User)
        monitor_lbl = ttk.Label(main_frame, text=_("tasks_monitor_label")); monitor_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(monitor_lbl, "tasks_monitor_label")
        self.input_vars[db_schema.COL_TASK_MONITOR_USER_ID] = tk.StringVar() # Stores "Username (ID)"
        self.input_widgets[db_schema.COL_TASK_MONITOR_USER_ID] = AutocompleteCombobox(main_frame, textvariable=self.input_vars[db_schema.COL_TASK_MONITOR_USER_ID], width=38, completevalues=[]) # Initialize with empty list
        self._populate_user_combobox(self.input_widgets[db_schema.COL_TASK_MONITOR_USER_ID])
        self.input_widgets[db_schema.COL_TASK_MONITOR_USER_ID].grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Due Date
        due_date_lbl = ttk.Label(main_frame, text=_("task_due_date_label")); due_date_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(due_date_lbl, "task_due_date_label")
        self.input_widgets[db_schema.COL_TASK_DUE_DATE] = DateEntry(main_frame, width=15, dateformat='%Y-%m-%d')
        self.input_widgets[db_schema.COL_TASK_DUE_DATE].grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # sticky ww
        row_idx += 1

        # Priority
        priority_lbl = ttk.Label(main_frame, text=_("tasks_priority_label")); priority_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(priority_lbl, "tasks_priority_label")
        self.input_vars[db_schema.COL_TASK_PRIORITY] = tk.StringVar(value="Medium")
        self.input_widgets[db_schema.COL_TASK_PRIORITY] = ttk.Combobox(main_frame, textvariable=self.input_vars[db_schema.COL_TASK_PRIORITY],
                                                           values=db_schema.VALID_TASK_PRIORITIES, state="readonly", width=15)
        self.input_widgets[db_schema.COL_TASK_PRIORITY].grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # sticky w
        row_idx += 1

        # Status
        status_lbl = ttk.Label(main_frame, text=_("tasks_status_label")); status_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_task_form(status_lbl, "tasks_status_label")
        self.input_vars[db_schema.COL_TASK_STATUS] = tk.StringVar(value="To Do")
        self.input_widgets[db_schema.COL_TASK_STATUS] = ttk.Combobox(main_frame, textvariable=self.input_vars[db_schema.COL_TASK_STATUS],
                                                         values=db_schema.VALID_TASK_STATUSES, state="readonly", width=15)
        self.input_widgets[db_schema.COL_TASK_STATUS].grid(row=row_idx, column=1, sticky="w", padx=5, pady=3) # sticky w
        row_idx += 1

        # Description
        desc_lbl = ttk.Label(main_frame, text=_("task_description_label")); desc_lbl.grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget_task_form(desc_lbl, "task_description_label")
        self.input_widgets[db_schema.COL_TASK_DESCRIPTION] = tk.Text(main_frame, height=5, width=40, relief="solid", borderwidth=1)
        self.input_widgets[db_schema.COL_TASK_DESCRIPTION].grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Notes (for updates/completion)
        notes_lbl = ttk.Label(main_frame, text="Notes:"); notes_lbl.grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3) # TODO: Key for "Notes:"
        # self._add_translatable_widget_task_form(notes_lbl, "task_notes_label")
        self.input_widgets[db_schema.COL_TASK_NOTES] = tk.Text(main_frame, height=3, width=40, relief="solid", borderwidth=1)
        self.input_widgets[db_schema.COL_TASK_NOTES].grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Action Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=15, sticky="e")
        self.save_task_btn = ttk.Button(buttons_frame, text=_("task_form_save_button"), command=self._save_task, bootstyle=db_schema.BS_ADD); self.save_task_btn.pack(side="right", padx=5)
        self._add_translatable_widget_task_form(self.save_task_btn, "form_button_save")
        self.cancel_task_btn = ttk.Button(buttons_frame, text=_("form_button_cancel"), command=self.destroy, bootstyle=db_schema.BS_LIGHT); self.cancel_task_btn.pack(side="right", padx=5)
        self._add_translatable_widget_task_form(self.cancel_task_btn, "form_button_cancel")

    def _populate_user_combobox(self, combo_widget):
        populate_user_combobox(combo_widget, db_queries.get_all_users_db, empty_option_text="") # Use the utility function

    def _load_task_data_for_edit(self):
        try:
            # Fetch the single task by ID. get_tasks_db might need adjustment or a new get_task_by_id_db
            task_data_list = db_queries.get_tasks_db() # Get all, then filter. Inefficient for single edit.
            task_data = next((t for t in task_data_list if t[db_schema.COL_TASK_ID] == self.task_id_to_edit), None)
            if not task_data:
                messagebox.showerror("Error", f"Task ID {self.task_id_to_edit} not found.", parent=self)
                self.destroy(); return
            
            self.input_vars[db_schema.COL_TASK_TITLE].set(task_data.get(db_schema.COL_TASK_TITLE, ""))
            # Set assignee: find "Name (ID)" string
            assignee_emp = db_queries._find_employee_by_id(task_data[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID])
            if assignee_emp: self.input_vars[COL_TASK_ASSIGNED_TO_EMP_ID].set(f"{assignee_emp[COL_EMP_NAME]} ({assignee_emp[COL_EMP_ID]})")
            # Set monitor: find "Username (ID)" string
            if task_data.get(COL_TASK_MONITOR_USER_ID):
                monitor_user = get_user_by_id_db(task_data[COL_TASK_MONITOR_USER_ID])
                if monitor_user: self.input_vars[db_schema.COL_TASK_MONITOR_USER_ID].set(f"{monitor_user[db_schema.COL_USER_USERNAME]} (ID: {monitor_user[db_schema.COL_USER_ID]})")

            if task_data.get(COL_TASK_DUE_DATE): self.input_widgets[COL_TASK_DUE_DATE].date = dt_date.fromisoformat(task_data[COL_TASK_DUE_DATE])
            self.input_vars[db_schema.COL_TASK_PRIORITY].set(task_data.get(db_schema.COL_TASK_PRIORITY, "Medium"))
            self.input_vars[db_schema.COL_TASK_STATUS].set(task_data.get(db_schema.COL_TASK_STATUS, "To Do"))
            self.input_widgets[db_schema.COL_TASK_DESCRIPTION].insert("1.0", task_data.get(db_schema.COL_TASK_DESCRIPTION, ""))
            self.input_widgets[db_schema.COL_TASK_NOTES].insert("1.0", task_data.get(db_schema.COL_TASK_NOTES, ""))

        except Exception as e:
            logger.error(f"Error loading task data for edit: {e}", exc_info=True)
            messagebox.showerror("Load Error", f"Could not load task details: {e}", parent=self)
            self.destroy()

    def _save_task(self):
        task_details = {}
        try:
            task_details[db_schema.COL_TASK_TITLE] = self.input_vars[db_schema.COL_TASK_TITLE].get().strip()
            if not task_details[db_schema.COL_TASK_TITLE]: raise InvalidInputError(_("task_title_required_error"))

            assignee_selection = self.input_vars[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID].get()
            task_details[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID] = extract_id_from_combobox_selection(assignee_selection)
            if not task_details[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID]: raise InvalidInputError(_("assignee_employee_required_error"))

            monitor_selection = self.input_vars[db_schema.COL_TASK_MONITOR_USER_ID].get()
            task_details[db_schema.COL_TASK_MONITOR_USER_ID] = extract_id_from_combobox_selection(monitor_selection) # Can be None

            task_details[db_schema.COL_TASK_DUE_DATE] = self.input_widgets[db_schema.COL_TASK_DUE_DATE].entry.get() or None
            task_details[db_schema.COL_TASK_PRIORITY] = self.input_vars[db_schema.COL_TASK_PRIORITY].get()
            task_details[db_schema.COL_TASK_STATUS] = self.input_vars[db_schema.COL_TASK_STATUS].get()
            task_details[db_schema.COL_TASK_DESCRIPTION] = self.input_widgets[db_schema.COL_TASK_DESCRIPTION].get("1.0", tk.END).strip()
            task_details[db_schema.COL_TASK_NOTES] = self.input_widgets[db_schema.COL_TASK_NOTES].get("1.0", tk.END).strip()

            if not self.parent_app or not hasattr(self.parent_app, 'current_user_details') or not self.parent_app.current_user_details:
                raise HRException(_("user_session_missing_cannot_save_task_error")) # Use HRException
            current_user_id = self.parent_app.current_user_details.get(db_schema.COL_USER_ID) # type: ignore
            if current_user_id is None: # More specific check
                raise HRException(_("cannot_save_task_user_id_not_identified_error")) # Use HRException

            if self.mode == 'add':
                db_queries.add_task_db(
                    assigned_to_emp_id=task_details[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID],
                    assigned_by_user_id=current_user_id,
                    monitor_user_id=task_details[db_schema.COL_TASK_MONITOR_USER_ID],
                    title=task_details[db_schema.COL_TASK_TITLE],
                    description=task_details.get(db_schema.COL_TASK_DESCRIPTION),
                    due_date_str=task_details.get(db_schema.COL_TASK_DUE_DATE),
                    priority=task_details[db_schema.COL_TASK_PRIORITY],
                    status=task_details[db_schema.COL_TASK_STATUS],
                    notes=task_details.get(db_schema.COL_TASK_NOTES)
                )
                messagebox.showinfo(_("success_title"), _("task_added_success_message"), parent=self)
            elif self.mode == 'edit':
                # For update, remove fields that are not directly updatable or handled by assigner/creation
                update_payload = {k: v for k, v in task_details.items() if k not in [db_schema.COL_TASK_ASSIGNED_TO_EMP_ID, db_schema.COL_TASK_ASSIGNED_BY_USER_ID]}
                if task_details[COL_TASK_STATUS] == "Completed" and not task_details.get(COL_TASK_COMPLETION_DATE):
                    update_payload[COL_TASK_COMPLETION_DATE] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                update_payload[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID] = task_details[db_schema.COL_TASK_ASSIGNED_TO_EMP_ID]
                db_queries.update_task_db(self.task_id_to_edit, update_payload)
                messagebox.showinfo(_("success_title"), _("task_updated_success_message"), parent=self)

            if self.callback_on_save: self.callback_on_save()
            self.destroy()
        # Corrected exception handling
        except (InvalidInputError, EmployeeNotFoundError, UserNotFoundError, DatabaseOperationError, HRException) as e:
            messagebox.showerror(_("save_error_title"), str(e), parent=self)
        except Exception as e_generic:
            logger.error(f"Unexpected error saving task: {e_generic}", exc_info=True)
            messagebox.showerror(_("unexpected_error_title"), _("unexpected_error_occurred_message", error=e_generic), parent=self)
            
    def _add_translatable_widget_task_form(self, widget, key, attr="text"):
        self.translatable_widgets_task_form.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self):
        form_title = _("task_form_title_add") if self.mode == 'add' else _("task_form_title_edit")
        self.title(form_title)
        for item_info in self.translatable_widgets_task_form:
            widget = item_info["widget"]
            key = item_info["key"]
            # attr = item_info.get("attr", "text") # TaskFormWindow only uses 'text' for now

            if widget.winfo_exists():
                try: widget.config(text=_(key))
                except tk.TclError: pass # Ignore for widgets without text config
        # Update specific button texts if not covered by the loop
        if hasattr(self, 'save_task_btn') and self.save_task_btn.winfo_exists():
            self.save_task_btn.config(text=_("task_form_save_button"))
        if hasattr(self, 'cancel_task_btn') and self.cancel_task_btn.winfo_exists():
            self.cancel_task_btn.config(text=_("form_button_cancel"))
        # Update labels that might not be in translatable_widgets_task_form if they were created directly with _()
        # Example:
        # if hasattr(self, 'title_lbl_ref') and self.title_lbl_ref.winfo_exists(): # Assuming you stored a ref
        # self.title_lbl_ref.config(text=_("task_title_label"))
        # This part depends on how _setup_task_form_widgets stores/references its labels.
        # The current implementation adds them to translatable_widgets_task_form, so the loop should cover them.


class TaskManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("task_management_window_title")) # Add this key
        self.geometry("1000x700") # Adjust as needed
        self.translatable_widgets_task_mgt = []

        self._create_task_management_widgets() # Create the UI
        self._gui_et_load_tasks() # Initial load

    def _add_translatable_widget_task_mgt(self, widget, key, attr="text"):
        self.translatable_widgets_task_mgt.append({"widget": widget, "key": key, "attr": attr})

    def _create_task_management_widgets(self):
        parent_frame = ttk.Frame(self, padding="10")
        parent_frame.pack(expand=True, fill="both")

        # --- Filter Frame ---
        filter_frame_key = "tasks_filter_frame_title"
        filter_frame = ttk.LabelFrame(parent_frame, text=_(filter_frame_key), padding="10")
        filter_frame.pack(side="top", fill="x", pady=5)
        self._add_translatable_widget_task_mgt(filter_frame, filter_frame_key, attr="title")

        assignee_lbl_key = "tasks_assignee_label"
        ttk.Label(filter_frame, text=_(assignee_lbl_key)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_task_mgt(filter_frame.winfo_children()[-1], assignee_lbl_key)
        self.et_assignee_filter_var = tk.StringVar()
        self.et_assignee_filter_combo = AutocompleteCombobox(filter_frame, textvariable=self.et_assignee_filter_var, width=25) # type: ignore
        self.et_assignee_filter_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        populate_employee_combobox(self.et_assignee_filter_combo, db_queries.get_all_employees_db, include_active_only=True, empty_option_text=_("task_all_option"))

        status_lbl_key = "tasks_status_label"
        ttk.Label(filter_frame, text=_(status_lbl_key)).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_task_mgt(filter_frame.winfo_children()[-1], status_lbl_key)
        self.et_status_filter_var = tk.StringVar(value=_("task_all_option"))
        self.et_status_filter_combo = ttk.Combobox(filter_frame, textvariable=self.et_status_filter_var,
                                                 values=[_("task_all_option")] + db_schema.VALID_TASK_STATUSES, state="readonly", width=15)
        self.et_status_filter_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        priority_lbl_key = "tasks_priority_label"
        ttk.Label(filter_frame, text=_(priority_lbl_key)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget_task_mgt(filter_frame.winfo_children()[-1], priority_lbl_key)
        self.et_priority_filter_var = tk.StringVar(value=_("task_all_option"))
        self.et_priority_filter_combo = ttk.Combobox(filter_frame, textvariable=self.et_priority_filter_var,
                                                 values=[_("task_all_option")] + db_schema.VALID_TASK_PRIORITIES, state="readonly", width=15)
        self.et_priority_filter_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        refresh_btn_key = "tasks_refresh_btn_text"
        self.et_refresh_btn = ttk.Button(filter_frame, text=_(refresh_btn_key), command=self._gui_et_load_tasks, bootstyle=db_schema.BS_VIEW_EDIT)
        self.et_refresh_btn.grid(row=1, column=3, padx=5, pady=5, sticky="e")
        self._add_translatable_widget_task_mgt(self.et_refresh_btn, refresh_btn_key)

        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)

        task_list_frame_key = "tasks_list_frame_title"
        task_list_frame = ttk.LabelFrame(parent_frame, text=_(task_list_frame_key), padding="10")
        task_list_frame.pack(fill="both", expand=True, pady=5)
        self._add_translatable_widget_task_mgt(task_list_frame, task_list_frame_key, attr="title")

        self.et_tree_cols = (db_schema.COL_TASK_ID, db_schema.COL_TASK_TITLE, "assignee_name", db_schema.COL_TASK_STATUS, db_schema.COL_TASK_PRIORITY,
                             db_schema.COL_TASK_DUE_DATE, "assigner_username", "monitor_username", db_schema.COL_TASK_CREATION_DATE)
        self.et_task_tree = ttk.Treeview(task_list_frame, columns=self.et_tree_cols, show="headings")
        self._update_task_tree_headers() # Set initial headers

        self.et_task_tree.column(db_schema.COL_TASK_ID, width=40, stretch=tk.NO, anchor="e")
        self.et_task_tree.column(db_schema.COL_TASK_TITLE, width=200, stretch=tk.YES)
        # ... (rest of column configurations from HRAppGUI._create_employee_tasks_view_widgets) ...
        self.et_task_tree.column("assignee_name", width=120)
        self.et_task_tree.column(db_schema.COL_TASK_STATUS, width=80)
        self.et_task_tree.column(db_schema.COL_TASK_PRIORITY, width=70)
        self.et_task_tree.column(db_schema.COL_TASK_DUE_DATE, width=90, anchor="center")
        self.et_task_tree.column("assigner_username", width=100)
        self.et_task_tree.column("monitor_username", width=100)
        self.et_task_tree.column(db_schema.COL_TASK_CREATION_DATE, width=130, anchor="center")

        et_scrollbar_y = ttk.Scrollbar(task_list_frame, orient="vertical", command=self.et_task_tree.yview)
        et_scrollbar_x = ttk.Scrollbar(task_list_frame, orient="horizontal", command=self.et_task_tree.xview)
        self.et_task_tree.configure(yscrollcommand=et_scrollbar_y.set, xscrollcommand=et_scrollbar_x.set)
        self.et_task_tree.pack(side="left", fill="both", expand=True)
        et_scrollbar_y.pack(side="right", fill="y")
        et_scrollbar_x.pack(side="bottom", fill="x")

        self.et_task_tree.bind("<<TreeviewSelect>>", self._gui_et_on_task_select)
        self.et_task_tree.bind("<Double-1>", self._gui_et_edit_selected_task)

        action_frame = ttk.Frame(parent_frame, padding="5")
        action_frame.pack(side="bottom", fill="x", pady=5)

        add_task_btn_key = "tasks_add_btn_text"
        self.et_add_task_btn = ttk.Button(action_frame, text=_(add_task_btn_key), command=self._gui_et_add_task, bootstyle=db_schema.BS_ADD)
        self.et_add_task_btn.pack(side="left", padx=5)
        self._add_translatable_widget_task_mgt(self.et_add_task_btn, add_task_btn_key)

        edit_task_btn_key = "tasks_edit_btn_text"
        self.et_edit_task_btn = ttk.Button(action_frame, text=_(edit_task_btn_key), command=self._gui_et_edit_selected_task, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.et_edit_task_btn.pack(side="left", padx=5)
        self._add_translatable_widget_task_mgt(self.et_edit_task_btn, edit_task_btn_key)

        delete_task_btn_key = "tasks_delete_btn_text"
        self.et_delete_task_btn = ttk.Button(action_frame, text=_(delete_task_btn_key), command=self._gui_et_delete_selected_task, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.et_delete_task_btn.pack(side="left", padx=5)
        self._add_translatable_widget_task_mgt(self.et_delete_task_btn, delete_task_btn_key)

    def _update_task_tree_headers(self):
        if hasattr(self, 'et_task_tree') and self.et_task_tree.winfo_exists():
            self.et_task_tree.heading(db_schema.COL_TASK_ID, text=_("tasks_header_id"))
            self.et_task_tree.heading(db_schema.COL_TASK_TITLE, text=_("tasks_header_title"))
            self.et_task_tree.heading("assignee_name", text=_("tasks_header_assignee"))
            self.et_task_tree.heading(db_schema.COL_TASK_STATUS, text=_("tasks_header_status"))
            self.et_task_tree.heading(db_schema.COL_TASK_PRIORITY, text=_("tasks_header_priority"))
            self.et_task_tree.heading(db_schema.COL_TASK_DUE_DATE, text=_("tasks_header_due_date"))
            self.et_task_tree.heading("assigner_username", text=_("tasks_header_assigner"))
            self.et_task_tree.heading("monitor_username", text=_("tasks_header_monitor"))
            self.et_task_tree.heading(db_schema.COL_TASK_CREATION_DATE, text=_("tasks_header_created_on"))

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("task_management_window_title"))
        self._update_task_tree_headers()
        for item_info in self.translatable_widgets_task_mgt:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")
            if widget.winfo_exists():
                try:
                    if attr_to_update == "text": widget.config(text=_(key))
                    elif attr_to_update == "title": widget.config(text=_(key)) # For LabelFrames
                except tk.TclError: pass

    def _gui_et_load_tasks(self):
        # Copied from HRAppGUI and adapted
        for item in self.et_task_tree.get_children():
            self.et_task_tree.delete(item)
        
        assignee_selection = self.et_assignee_filter_var.get()
        assignee_emp_id = extract_id_from_combobox_selection(assignee_selection) if assignee_selection != _("task_all_option") else None
        
        status_filter = self.et_status_filter_var.get()
        if status_filter == _("task_all_option"): status_filter = None

        priority_filter = self.et_priority_filter_var.get()
        if priority_filter == _("task_all_option"): priority_filter = None

        try:
            tasks = db_queries.get_tasks_db(assignee_emp_id=assignee_emp_id, status=status_filter, priority=priority_filter)
            for task in tasks:
                self.et_task_tree.insert("", "end", iid=task[db_schema.COL_TASK_ID], values=(
                    task[db_schema.COL_TASK_ID], task[db_schema.COL_TASK_TITLE],
                    task.get("assignee_name", "N/A"), task[db_schema.COL_TASK_STATUS],
                    task[db_schema.COL_TASK_PRIORITY], task.get(db_schema.COL_TASK_DUE_DATE, ""),
                    task.get("assigner_username", "N/A"), task.get("monitor_username", "N/A"),
                    task[db_schema.COL_TASK_CREATION_DATE]
                ))
        except (DatabaseOperationError, EmployeeNotFoundError, UserNotFoundError) as e:
            messagebox.showerror(_("error_loading_tasks_title"), str(e), parent=self)
        self._gui_et_on_task_select()

    def _gui_et_on_task_select(self, event=None):
        # Copied from HRAppGUI and adapted
        is_selected = bool(self.et_task_tree.selection())
        self.et_edit_task_btn.config(state="normal" if is_selected else "disabled")
        self.et_delete_task_btn.config(state="normal" if is_selected else "disabled")
        # Details pane logic can be added here if TaskManagementWindow has one

    def _gui_et_add_task(self):
        # Copied from HRAppGUI and adapted
        self.parent_app._create_and_show_toplevel(TaskFormWindow, mode='add', callback_on_save=self._gui_et_load_tasks, tracker_attr_name="active_task_form_window_add")

    def _gui_et_edit_selected_task(self, event=None):
        # Copied from HRAppGUI and adapted
        selected_item_iid = self.et_task_tree.focus()
        if not selected_item_iid:
            messagebox.showwarning(_("edit_task_warning_title"), _("edit_task_select_task_warning"), parent=self)
            return
        task_id = int(selected_item_iid)
        self.parent_app._create_and_show_toplevel(TaskFormWindow, mode='edit', task_id=task_id, callback_on_save=self._gui_et_load_tasks, tracker_attr_name=f"active_task_form_window_edit_{task_id}")

    def _gui_et_delete_selected_task(self):
        # Copied from HRAppGUI and adapted
        selected_item_iid = self.et_task_tree.focus()
        if not selected_item_iid:
            messagebox.showwarning(_("delete_task_warning_title"), _("delete_task_select_task_warning"), parent=self)
            return
        task_id = int(selected_item_iid)
        task_title = self.et_task_tree.item(selected_item_iid, "values")[1]

        if messagebox.askyesno(_("confirm_delete_title"), _("delete_task_confirm_message", task_title=task_title, task_id=task_id), parent=self):
            try:
                db_queries.delete_task_db(task_id)
                messagebox.showinfo(_("success_title"), _("task_deleted_success_message"), parent=self)
                self._gui_et_load_tasks()
            except (DatabaseOperationError, HRException) as e:
                messagebox.showerror(_("delete_error_title"), str(e), parent=self)
        