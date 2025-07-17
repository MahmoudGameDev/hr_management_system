# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\vacation_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, date as dt_date, timedelta # type: ignore
# --- Project-specific imports ---
from typing import List, Optional, Dict # Added Dict
from data import database as db_schema # For COL_LR_... constants
from data import queries as db_queries # For database query functions
from utils import localization # For localization module access if needed # Keep this if localization.LANG_MANAGER is used directly
from utils.exceptions import EmployeeNotFoundError, DatabaseOperationError, InvalidInputError # Import custom exceptions
from utils.gui_utils import extract_id_from_combobox_selection, populate_employee_combobox
from .themed_toplevel import ThemedToplevel
from utils.localization import _ # Import _ directly

logger = logging.getLogger(__name__)

class VacationManagementWindow(ThemedToplevel):
    
    TRACKER_NAME = "active_vacation_management_window" # Define tracker name

    def __init__(self, parent, app_instance, default_emp_id: Optional[str] = None, view_mode: Optional[str] = None, manager_id: Optional[str] = None):
 
        super().__init__(parent, app_instance)
        self.title_key = "vacation_management_window_title"
        self.title(_(self.title_key))
        self.geometry("1000x700") # Adjusted size
        self.translatable_widgets_vac_mgt = [] # For this window's translatable widgets

        self.default_emp_id = default_emp_id
        self.view_mode = view_mode
        self.manager_id = manager_id
        self.current_employee_id: Optional[str] = None
        self.employee_combobox_map: Dict[str, str] = {} # To map display names to emp_ids

        self._create_main_layout() # Create main layout frames
        self._populate_employee_combobox() # Initial population
        # Repopulate leave type combobox
        self.leave_type_combo['values'] = [_("leave_type_vacation"), _("leave_type_sick"), _("leave_type_personal"), _("leave_type_unpaid"), _("leave_type_other")]

        self.refresh_ui_for_language() # Initial translation

        # Load data if default_emp_id is provided (after widgets are created)
        if self.default_emp_id and hasattr(self, 'form_employee_combo') and self.form_employee_combo.cget('state') == 'disabled':
            self._on_employee_select_for_leave() # Load their data

    def _create_main_layout(self):
        """Creates the main layout frames for the window."""
        request_form_lf_key = "vacation_submit_request_frame_title"
        self.request_form_frame = ttk.LabelFrame(self, text=_(request_form_lf_key), padding="10")
        self.request_form_frame.pack(side="top", fill="x", padx=10, pady=5)
        self._add_translatable_widget_vac_mgt(self.request_form_frame, request_form_lf_key, attr="title")
        self._create_request_form_widgets(self.request_form_frame)

        list_lf_key = "vacation_existing_requests_frame_title"
        self.list_frame = ttk.LabelFrame(self, text=_(list_lf_key), padding="10")
        self.list_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        self._add_translatable_widget_vac_mgt(self.list_frame, list_lf_key, attr="title")
        self._create_list_widgets(self.list_frame)

    def _add_translatable_widget_vac_mgt(self, widget, key, attr="text"):
        """Helper to register translatable widgets for this window."""
        self.translatable_widgets_vac_mgt.append({"widget": widget, "key": key, "attr": attr})

    def _create_request_form_widgets(self, parent_frame):
        """Creates widgets for the leave request form."""
        emp_lbl_key = "vacation_employee_label"
        emp_lbl = ttk.Label(parent_frame, text=_(emp_lbl_key)); emp_lbl.grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_vac_mgt(emp_lbl, emp_lbl_key)
        
        self.form_employee_var = tk.StringVar() # Use a consistent name
        self.form_employee_combo = ttk.Combobox(parent_frame, textvariable=self.form_employee_var, state="readonly", width=23)
        self.form_employee_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        self.form_employee_combo.bind("<<ComboboxSelected>>", self._on_employee_select_for_leave)

        self.vacation_balance_var = tk.StringVar(value=_("vacation_balance_na_text"))
        balance_lbl = ttk.Label(parent_frame, textvariable=self.vacation_balance_var, font=("Helvetica", 10, "bold"))
        balance_lbl.grid(row=0, column=2, columnspan=2, sticky="w", padx=20, pady=3)

        leave_type_lbl_key = "vacation_leave_type_label"
        leave_type_lbl = ttk.Label(parent_frame, text=_(leave_type_lbl_key)); leave_type_lbl.grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_vac_mgt(leave_type_lbl, leave_type_lbl_key)
        self.leave_type_var = tk.StringVar()
        self.leave_type_combo = ttk.Combobox(parent_frame, textvariable=self.leave_type_var,
                                             values=[_("leave_type_vacation"), _("leave_type_sick"), _("leave_type_personal"), _("leave_type_unpaid"), _("leave_type_other")],
                                             state="readonly", width=23)
        self.leave_type_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        self.leave_type_combo.set(_("leave_type_vacation")) # Default to translated "Vacation"

        start_date_lbl_key = "vacation_start_date_label"
        start_date_lbl = ttk.Label(parent_frame, text=_(start_date_lbl_key)); start_date_lbl.grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_vac_mgt(start_date_lbl, start_date_lbl_key)
        self.leave_start_date_entry = DateEntry(parent_frame, width=23, dateformat='%Y-%m-%d')
        self.leave_start_date_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=3)

        end_date_lbl_key = "vacation_end_date_label"
        end_date_lbl = ttk.Label(parent_frame, text=_(end_date_lbl_key)); end_date_lbl.grid(row=2, column=2, sticky="w", padx=(10,5), pady=3)
        self._add_translatable_widget_vac_mgt(end_date_lbl, end_date_lbl_key)
        self.leave_end_date_entry = DateEntry(parent_frame, width=23, dateformat='%Y-%m-%d')
        self.leave_end_date_entry.grid(row=2, column=3, sticky="ew", padx=5, pady=3)

        reason_lbl_key = "vacation_reason_label"
        reason_lbl = ttk.Label(parent_frame, text=_(reason_lbl_key)); reason_lbl.grid(row=3, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget_vac_mgt(reason_lbl, reason_lbl_key)
        self.leave_reason_text = tk.Text(parent_frame, height=3, width=40, relief="solid", borderwidth=1)
        self.leave_reason_text.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

        check_conflicts_btn_key = "vacation_check_conflicts_button"
        self.check_conflicts_btn = ttk.Button(parent_frame, text=_(check_conflicts_btn_key), command=self._gui_check_colleague_conflicts, bootstyle="info-outline")
        self.check_conflicts_btn.grid(row=4, column=0, pady=10, padx=5, sticky="w") # Changed row
        self._add_translatable_widget_vac_mgt(self.check_conflicts_btn, check_conflicts_btn_key)

        submit_btn_key = "vacation_submit_button"
        self.submit_leave_btn = ttk.Button(parent_frame, text=_(submit_btn_key), command=self._gui_submit_leave_request, bootstyle=db_schema.BS_ADD)
        self.submit_leave_btn.grid(row=4, column=1, columnspan=3, pady=10, sticky="e") # Changed row
        self._add_translatable_widget_vac_mgt(self.submit_leave_btn, submit_btn_key)

        parent_frame.columnconfigure(1, weight=1)
        parent_frame.columnconfigure(3, weight=1)

    def _create_list_widgets(self, parent_frame):
        """Creates widgets for the leave list display."""
        self.leave_tree_cols = (db_schema.COL_LR_ID, db_schema.COL_LR_LEAVE_TYPE,
                                db_schema.COL_LR_START_DATE, db_schema.COL_LR_END_DATE,
                                db_schema.COL_LR_REQUEST_DATE, db_schema.COL_LR_STATUS,
                                db_schema.COL_LR_REASON)
        self.leave_tree = ttk.Treeview(parent_frame, columns=self.leave_tree_cols, show="headings")
        self._update_leave_tree_headers()

        self.leave_tree.column(db_schema.COL_LR_ID, width=60, anchor="e", stretch=tk.NO)
        self.leave_tree.column(db_schema.COL_LR_LEAVE_TYPE, width=100)
        self.leave_tree.column(db_schema.COL_LR_START_DATE, width=100, anchor="center")
        self.leave_tree.column(db_schema.COL_LR_END_DATE, width=100, anchor="center")
        self.leave_tree.column(db_schema.COL_LR_REQUEST_DATE, width=100, anchor="center")
        self.leave_tree.column(db_schema.COL_LR_STATUS, width=100, anchor="center")
        self.leave_tree.column(db_schema.COL_LR_REASON, width=200, stretch=tk.YES)
        self.leave_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.leave_tree.yview)
        self.leave_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _update_leave_tree_headers(self):
        """Updates the headers of the leave treeview based on current language."""
        if hasattr(self, 'leave_tree') and self.leave_tree.winfo_exists():
            self.leave_tree.heading(db_schema.COL_LR_ID, text=_("vacation_header_req_id"))
            self.leave_tree.heading(db_schema.COL_LR_LEAVE_TYPE, text=_("vacation_header_type"))
            self.leave_tree.heading(db_schema.COL_LR_START_DATE, text=_("vacation_header_start_date"))
            self.leave_tree.heading(db_schema.COL_LR_END_DATE, text=_("vacation_header_end_date"))
            self.leave_tree.heading(db_schema.COL_LR_REQUEST_DATE, text=_("vacation_header_requested_on"))
            self.leave_tree.heading(db_schema.COL_LR_STATUS, text=_("vacation_header_status"))
            self.leave_tree.heading(db_schema.COL_LR_REASON, text=_("vacation_header_reason"))

    def refresh_ui_for_language(self): # pragma: no cover
        
        self.title(_(self.title_key))
        self._update_leave_tree_headers()
        for item_info in self.translatable_widgets_vac_mgt: # Use the correct list
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")
            if widget.winfo_exists():
                try:
                    if attr_to_update == "text": widget.config(text=_(key))
                    elif attr_to_update == "title": widget.config(text=_(key)) # For LabelFrames
                except tk.TclError: pass

        # Repopulate leave type combobox with translated values
        self.leave_type_combo['values'] = [_("leave_type_vacation"), _("leave_type_sick"), _("leave_type_personal"), _("leave_type_unpaid"), _("leave_type_other")]
        # Try to preserve selection or set default
        current_type_val = self.leave_type_var.get()
        if current_type_val not in self.leave_type_combo['values']:
            self.leave_type_combo.set(_("leave_type_vacation"))

    def _populate_employee_combobox(self):
        """Populates the employee combobox based on view_mode and default_emp_id."""
        current_selection_text = self.form_employee_var.get() # Preserve current selection if possible
        self.employee_combobox_map.clear() # Clear the map before repopulating

        try:
            if self.default_emp_id:
                employee = db_queries.get_employee_by_id_db(self.default_emp_id)
                if employee:
                    display_name = f"{employee[db_schema.COL_EMP_NAME]} ({employee[db_schema.COL_EMP_ID]})"
                    self.form_employee_combo['values'] = [display_name]
                    self.form_employee_var.set(display_name)
                    self.form_employee_combo.config(state="disabled")
                    self.current_employee_id = self.default_emp_id
                else: # pragma: no cover
                    logger.warning(f"Default employee ID {self.default_emp_id} not found for Vacation Mgt.")
                    self.form_employee_combo['values'] = []
            elif self.view_mode == "manager_team" and self.manager_id:
                team_employees_dicts = db_queries.get_employees_by_manager_db(self.manager_id, include_archived=False)
                populate_employee_combobox(self.form_employee_combo, lambda: team_employees_dicts,
                                           include_active_only=True, default_to_first=True) # Removed combo_map_dict

            else: # Normal mode, load all active employees
                populate_employee_combobox(self.form_employee_combo, db_queries.get_all_employees_db, # Changed to get_all_employees_db
                                           include_active_only=True, default_to_first=True) # Removed combo_map_dict

            # Build the map after combobox is populated
            for display_name_val in self.form_employee_combo.cget('values'):
                emp_id_from_display = extract_id_from_combobox_selection(display_name_val) # This util handles "Name (ID)"
                if emp_id_from_display:
                    self.employee_combobox_map[display_name_val] = emp_id_from_display

            # Try to restore selection if it's still valid
            if current_selection_text and current_selection_text in self.form_employee_combo.cget('values'): # pragma: no cover
                self.form_employee_var.set(current_selection_text)
            elif self.form_employee_combo['values']: # If not, and list is not empty, select first
                self.form_employee_combo.current(0)
            # The employee_combobox_map is now populated directly by populate_employee_combobox
            
            # Trigger select if an item is now selected (either restored or defaulted by populate_employee_combobox)
            if self.form_employee_var.get():
                 self._on_employee_select_for_leave()

    
        except Exception as e:
            logger.error(f"Error populating employee combobox in Vacation Mgt: {e}", exc_info=True)
            messagebox.showerror(_("db_error_title"), _("error_loading_employees_message"), parent=self)

    def _on_employee_select_for_leave(self, event=None):
        effective_emp_id: Optional[str] = None

        if self.default_emp_id and self.form_employee_combo.cget('state') == 'disabled':
            effective_emp_id = self.default_emp_id
        else:
            # This is for manager portal or admin view where combobox is active.
            selected_display_name = self.form_employee_var.get() # Get current value from combobox
            effective_emp_id = extract_id_from_combobox_selection(selected_display_name)

        self.current_employee_id = effective_emp_id # Set the instance attribute based on the determined ID

        if self.current_employee_id:
            # An employee is selected (either default or from combobox)
            try:
                balance = db_queries.get_employee_vacation_balance_db(self.current_employee_id)
                self.vacation_balance_var.set(_("vacation_balance_text", balance=balance)) # Make sure this key exists
            except EmployeeNotFoundError: # pragma: no cover
                self.vacation_balance_var.set(_("vacation_balance_error_text")) # Make sure this key exists
                messagebox.showerror(_("error_title"), _("employee_not_found_for_balance_error", emp_id=self.current_employee_id), parent=self) # Add key
            except Exception as e: # pragma: no cover
                self.vacation_balance_var.set(_("vacation_balance_error_text"))
                logger.error(f"Error fetching vacation balance for {self.current_employee_id}: {e}", exc_info=True)
            
            self._load_leave_requests_to_tree(self.current_employee_id)
        else:
            # No employee is selected
        
            self.vacation_balance_var.set(_("vacation_balance_na_text"))
            self._load_leave_requests_to_tree(None) # Clear tree            

    def _gui_check_colleague_conflicts(self):
        emp_id = self.current_employee_id # Use the stored current_employee_id
        if not emp_id:
            messagebox.showerror(_("input_error_title"), _("vacation_employee_select_error"), parent=self)
            return

        start_date_str = self.leave_start_date_entry.entry.get()
        end_date_str = self.leave_end_date_entry.entry.get()

        if not all([start_date_str, end_date_str]):
            messagebox.showerror(_("input_error_title"), _("vacation_dates_required_for_conflict_error"), parent=self)
            return
        try:
            dt_date.fromisoformat(start_date_str)
            dt_date.fromisoformat(end_date_str)
        except ValueError:
            messagebox.showerror(_("input_error_title"), _("invalid_date_format_yyyy_mm_dd_error"), parent=self)
            return

        employee_details = db_queries.get_employee_by_id_db(emp_id)
        if not employee_details or not employee_details.get(db_schema.COL_EMP_DEPARTMENT_ID):
            messagebox.showinfo(_("vacation_conflict_check_title"), _("vacation_no_department_for_conflict_check_info"), parent=self)
            return
        
        department_id = employee_details[db_schema.COL_EMP_DEPARTMENT_ID]

        try:
            conflicting_leaves = db_queries.get_concurrent_department_leaves(department_id, start_date_str, end_date_str, exclude_employee_id=emp_id)
            if not conflicting_leaves:
                messagebox.showinfo(_("vacation_no_conflicts_title"), _("vacation_no_conflicts_message"), parent=self)
            else:
                conflict_details = _("vacation_conflicts_found_message_prefix") + "\n\n"
                for leave in conflicting_leaves:
                    conflict_details += _("vacation_conflict_detail_item", name=leave[db_schema.COL_EMP_NAME], id=leave[db_schema.COL_LR_EMP_ID], type=leave[db_schema.COL_LR_LEAVE_TYPE], start=leave[db_schema.COL_LR_START_DATE], end=leave[db_schema.COL_LR_END_DATE]) + "\n"
                messagebox.showwarning(_("vacation_conflicts_found_title"), conflict_details, parent=self)
        except Exception as e:
            logger.error(f"Error checking colleague conflicts: {e}", exc_info=True)
            messagebox.showerror(_("error_title"), _("vacation_conflict_check_error", error=e), parent=self)


    def _load_leave_requests_to_tree(self, employee_id: Optional[str]):
        for item in self.leave_tree.get_children():
            self.leave_tree.delete(item)
        if not employee_id: return

        try:
            requests = db_queries.get_leave_requests_for_employee_db(employee_id)
            for req in requests:
                self.leave_tree.insert("", "end", values=(
                    req[db_schema.COL_LR_ID], req[db_schema.COL_LR_LEAVE_TYPE], req[db_schema.COL_LR_START_DATE],
                    req[db_schema.COL_LR_END_DATE], req[db_schema.COL_LR_REQUEST_DATE], req[db_schema.COL_LR_STATUS],
                    req.get(db_schema.COL_LR_REASON, "")
                ))
        except (EmployeeNotFoundError, DatabaseOperationError) as e:
            messagebox.showerror(_("error_title"), _("vacation_error_loading_requests", error=e), parent=self)

    def _gui_submit_leave_request(self):
        emp_id = self.current_employee_id # Use the stored current_employee_id
        if not self.current_employee_id: # Changed to self.current_employee_id for consistency with snippet
            messagebox.showerror(_("input_error_title"), _("error_no_employee_selected_for_leave_submission"), parent=self) # Used user's key
            return

        leave_type = self.leave_type_var.get()
        start_date_str = self.leave_start_date_entry.entry.get()
        end_date_str = self.leave_end_date_entry.entry.get()
        reason = self.leave_reason_text.get("1.0", tk.END).strip()

        if not all([leave_type, start_date_str, end_date_str]):
            messagebox.showerror(_("input_error_title"), _("vacation_missing_fields_error"), parent=self)
            return
        
        try: # Validate dates
            start_obj = dt_date.fromisoformat(start_date_str)
            end_obj = dt_date.fromisoformat(end_date_str)
            if start_obj > end_obj:
                messagebox.showerror(_("input_error_title"), _("vacation_start_after_end_error"), parent=self)
                return
            if start_obj < dt_date.today() and leave_type != _("leave_type_sick"): # Allow backdated sick leave
                 if not messagebox.askyesno(_("vacation_confirm_past_date_title"), _("vacation_confirm_past_date_message"), parent=self):
                     return
        except ValueError:
            messagebox.showerror(_("input_error_title"), _("invalid_date_format_yyyy_mm_dd_error"), parent=self)
            return

        # --- Smart Suggestion/Alert Logic ---
        employee_details = db_queries.get_employee_by_id_db(emp_id)
        department_id = employee_details.get(db_schema.COL_EMP_DEPARTMENT_ID) if employee_details else None

        if department_id:
            try:
                if db_queries.is_department_busy_for_leave(department_id, start_date_str, end_date_str, emp_id):
                    if not messagebox.askyesno(_("vacation_dept_busy_title"), _("vacation_dept_busy_message"), icon='warning', parent=self):                        return # User chose not to submit
            except Exception as e_busy_check:
                logger.error(f"Error during department busy check for leave request: {e_busy_check}", exc_info=True)
                # Decide if to proceed or halt; for now, let's allow submission with a warning
                messagebox.showwarning(_("vacation_busy_check_error_title"), _("vacation_busy_check_error_message"), parent=self)
        # --- End of Smart Suggestion/Alert Logic ---
        try:
            db_queries.add_leave_request_db(
                employee_id=self.current_employee_id, leave_type=leave_type,
                start_date_str=start_date_str, end_date_str=end_date_str, reason=reason
            )
            messagebox.showinfo(_("success_title"), _("vacation_request_submitted_success"), parent=self)
            self._on_employee_select_for_leave() # Refresh list and balance
            # Clear form fields
            self.leave_start_date_entry.date = dt_date.today()
            self.leave_end_date_entry.date = dt_date.today()
            self.leave_reason_text.delete("1.0", tk.END)
            self.leave_type_combo.set("Vacation") # Reset type
        except (InvalidInputError, EmployeeNotFoundError, DatabaseOperationError) as e:
            messagebox.showerror(_("submission_error_title"), str(e), parent=self)
        except Exception as e_generic:
            logger.error(f"Unexpected error submitting leave request: {e_generic}", exc_info=True)
            messagebox.showerror(_("error_title"), _("vacation_submit_unexpected_error", error=e_generic), parent=self)
