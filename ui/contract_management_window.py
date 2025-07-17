# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\contract_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, date as dt_date
from typing import Optional, Dict, List, Any, Union

# --- Project-specific imports ---
from data import database as db_schema # For COL_CONTRACT_... constants
from data import queries as db_queries # For contract DB functions
from utils import localization # For _()
from utils import pdf_utils # Import the new pdf_utils
from utils.gui_utils import populate_employee_combobox, extract_id_from_combobox_selection
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # For theming tk.Text
from .themed_toplevel import ThemedToplevel
from .electronic_contract_window import ElectronicContractWindow # If new contracts are created from here

logger = logging.getLogger(__name__)

class ContractManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, default_emp_id: Optional[str] = None):
        super().__init__(parent, app_instance)
        self.title(localization._("contract_management_window_title")) # Add key
        self.geometry("1000x700") # Adjust as needed
        self.translatable_widgets_contract_mgt = []
        self.default_emp_id = default_emp_id
        self.current_selected_contract_id: Optional[int] = None

        # --- Main Paned Window (Filters/Form on Top, List on Bottom) ---
        main_paned_window = ttkb.PanedWindow(self, orient=tk.VERTICAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Top Pane: Filters and New Contract Button ---
        filter_pane = ttkb.Frame(main_paned_window, padding="10")
        main_paned_window.add(filter_pane, weight=1) # Adjust weight as needed
        self._create_filter_widgets(filter_pane)

        # --- Bottom Pane: Contract List and Action Buttons ---
        list_pane = ttkb.Frame(main_paned_window, padding="10")
        main_paned_window.add(list_pane, weight=3) # List can be larger
        self._create_contract_list_widgets(list_pane)

        if self.default_emp_id:
            self._set_default_employee_filter_contract()
        
        self._load_contracts_to_tree() # Initial load

    def _add_translatable_widget_contract_mgt(self, widget, key, attr="text"):
        self.translatable_widgets_contract_mgt.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("contract_management_window_title"))
        # Update LabelFrame titles, labels, button texts
        if hasattr(self, 'filter_lf') and self.filter_lf.winfo_exists(): self.filter_lf.config(text=localization._("contract_filter_frame_title"))
        if hasattr(self, 'list_lf') and self.list_lf.winfo_exists(): self.list_lf.config(text=localization._("contract_list_frame_title"))
        
        # Update labels in filters
        if hasattr(self, 'employee_filter_label_contract') and self.employee_filter_label_contract.winfo_exists(): self.employee_filter_label_contract.config(text=localization._("contract_filter_employee_label"))
        if hasattr(self, 'status_filter_label_contract') and self.status_filter_label_contract.winfo_exists(): self.status_filter_label_contract.config(text=localization._("contract_filter_status_label"))

        # Update button texts
        if hasattr(self, 'create_new_contract_btn') and self.create_new_contract_btn.winfo_exists(): self.create_new_contract_btn.config(text=localization._("contract_create_new_button"))
        if hasattr(self, 'view_details_btn') and self.view_details_btn.winfo_exists(): self.view_details_btn.config(text=localization._("contract_view_details_button"))
        if hasattr(self, 'edit_contract_btn') and self.edit_contract_btn.winfo_exists(): self.edit_contract_btn.config(text=localization._("contract_edit_button"))
        if hasattr(self, 'approve_contract_btn') and self.approve_contract_btn.winfo_exists(): self.approve_contract_btn.config(text=localization._("contract_approve_button"))
        if hasattr(self, 'reject_contract_btn') and self.reject_contract_btn.winfo_exists(): self.reject_contract_btn.config(text=localization._("contract_reject_button"))

        # Update Treeview headers
        if hasattr(self, 'contract_tree') and self.contract_tree.winfo_exists():
            self._update_contract_tree_headers()
        
        # Repopulate comboboxes if their "All" option is translatable
        if hasattr(self, 'employee_filter_combo_contract'): self._populate_employee_filter_combo_contract()
        if hasattr(self, 'status_filter_combo_contract'): self._populate_status_filter_combo_contract()

    def _create_filter_widgets(self, parent_frame):
        self.filter_lf = ttkb.LabelFrame(parent_frame, text=localization._("contract_filter_frame_title"), padding="10")
        self.filter_lf.pack(fill="x")
        self._add_translatable_widget_contract_mgt(self.filter_lf, "contract_filter_frame_title", attr="title")

        filter_grid_frame = ttk.Frame(self.filter_lf)
        filter_grid_frame.pack(fill="x")
        filter_grid_frame.columnconfigure(1, weight=1) # Employee combo column
        filter_grid_frame.columnconfigure(3, weight=1) # Status combo column

        # Employee Filter
        self.employee_filter_label_contract = ttk.Label(filter_grid_frame, text=localization._("contract_filter_employee_label"))
        self.employee_filter_label_contract.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget_contract_mgt(self.employee_filter_label_contract, "contract_filter_employee_label")
        self.employee_filter_var_contract = tk.StringVar()
        self.employee_filter_combo_contract = populate_employee_combobox(
            filter_grid_frame, tk.StringVar(), db_queries.list_all_employees,
            include_active_only=False, empty_option_text=localization._("contract_filter_all_employees"),
            combo_width=30
        )
        self.employee_filter_combo_contract.config(textvariable=self.employee_filter_var_contract) # Link var
        self.employee_filter_combo_contract.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.employee_filter_combo_contract.bind("<<ComboboxSelected>>", lambda e: self._load_contracts_to_tree())

        # Status Filter
        self.status_filter_label_contract = ttk.Label(filter_grid_frame, text=localization._("contract_filter_status_label"))
        self.status_filter_label_contract.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self._add_translatable_widget_contract_mgt(self.status_filter_label_contract, "contract_filter_status_label")
        self.status_filter_var_contract = tk.StringVar(value=localization._("contract_filter_all_statuses"))
        self.status_filter_combo_contract = ttkb.Combobox(
            filter_grid_frame, textvariable=self.status_filter_var_contract,
            values=[localization._("contract_filter_all_statuses")] + db_schema.VALID_CONTRACT_TYPES + ['Draft', 'Active', 'Expired', 'Terminated', 'Upcoming Renewal', 'Pending Approval', 'Approved', 'Rejected'], # Include lifecycle and approval statuses
            state="readonly", width=20
        )
        self.status_filter_combo_contract.grid(row=0, column=3, sticky="ew", padx=5, pady=5)
        self.status_filter_combo_contract.bind("<<ComboboxSelected>>", lambda e: self._load_contracts_to_tree())

        # New Contract Button
        self.create_new_contract_btn = ttkb.Button(
            self.filter_lf, text=localization._("contract_create_new_button"),
            command=self._gui_create_new_contract_mgt, bootstyle=db_schema.BS_ADD
        )
        self.create_new_contract_btn.pack(side="right", pady=5)
        self._add_translatable_widget_contract_mgt(self.create_new_contract_btn, "contract_create_new_button")

    def _create_contract_list_widgets(self, parent_frame):
        self.list_lf = ttkb.LabelFrame(parent_frame, text=localization._("contract_list_frame_title"), padding="10")
        self.list_lf.pack(fill="both", expand=True)
        self._add_translatable_widget_contract_mgt(self.list_lf, "contract_list_frame_title", attr="title")

        # Treeview for contracts
        self.contract_tree_cols = (
            db_schema.COL_CONTRACT_ID, db_schema.COL_CONTRACT_EMP_ID, "employee_name",
            db_schema.COL_CONTRACT_TYPE, db_schema.COL_CONTRACT_START_DATE,
            db_schema.COL_CONTRACT_CURRENT_END_DATE, db_schema.COL_CONTRACT_LIFECYCLE_STATUS,
            db_schema.COL_CONTRACT_APPROVAL_STATUS, "assigned_approver_username"
        )
        self.contract_tree = ttkb.Treeview(self.list_lf, columns=self.contract_tree_cols, show="headings")
        self._update_contract_tree_headers()

        # Configure columns (adjust widths as needed)
        self.contract_tree.column(db_schema.COL_CONTRACT_ID, width=60, anchor="e", stretch=tk.NO)
        self.contract_tree.column(db_schema.COL_CONTRACT_EMP_ID, width=80, anchor="w")
        self.contract_tree.column("employee_name", width=150, anchor="w")
        self.contract_tree.column(db_schema.COL_CONTRACT_TYPE, width=120, anchor="w")
        self.contract_tree.column(db_schema.COL_CONTRACT_START_DATE, width=100, anchor="center")
        self.contract_tree.column(db_schema.COL_CONTRACT_CURRENT_END_DATE, width=100, anchor="center")
        self.contract_tree.column(db_schema.COL_CONTRACT_LIFECYCLE_STATUS, width=120, anchor="center")
        self.contract_tree.column(db_schema.COL_CONTRACT_APPROVAL_STATUS, width=120, anchor="center")
        self.contract_tree.column("assigned_approver_username", width=120, anchor="w", stretch=tk.YES)

        scrollbar_y = ttkb.Scrollbar(self.list_lf, orient="vertical", command=self.contract_tree.yview)
        self.contract_tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_x = ttkb.Scrollbar(self.list_lf, orient="horizontal", command=self.contract_tree.xview)
        self.contract_tree.configure(xscrollcommand=scrollbar_x.set)

        self.contract_tree.pack(side="top", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        self.contract_tree.bind("<<TreeviewSelect>>", self._on_contract_select)
        self.contract_tree.bind("<Double-1>", lambda e: self._gui_view_contract_details()) # Double click to view

        # Action Buttons below the treeview
        action_buttons_frame = ttkb.Frame(self.list_lf)
        action_buttons_frame.pack(side="bottom", fill="x", pady=5)

        self.view_details_btn = ttkb.Button(action_buttons_frame, text=localization._("contract_view_details_button"), command=self._gui_view_contract_details, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.view_details_btn.pack(side="left", padx=5)
        self._add_translatable_widget_contract_mgt(self.view_details_btn, "contract_view_details_button")

        self.edit_contract_btn = ttkb.Button(action_buttons_frame, text=localization._("contract_edit_button"), command=self._gui_edit_contract, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.edit_contract_btn.pack(side="left", padx=5)
        self._add_translatable_widget_contract_mgt(self.edit_contract_btn, "contract_edit_button")

        self.approve_contract_btn = ttkb.Button(action_buttons_frame, text=localization._("contract_approve_button"), command=lambda: self._gui_approve_reject_contract("Approved"), state="disabled", bootstyle=db_schema.BS_ADD)
        self.approve_contract_btn.pack(side="left", padx=5)
        self._add_translatable_widget_contract_mgt(self.approve_contract_btn, "contract_approve_button")

        self.reject_contract_btn = ttkb.Button(action_buttons_frame, text=localization._("contract_reject_button"), command=lambda: self._gui_approve_reject_contract("Rejected"), state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.reject_contract_btn.pack(side="left", padx=5)
        self._add_translatable_widget_contract_mgt(self.reject_contract_btn, "contract_reject_button")

    def _update_contract_tree_headers(self):
        if hasattr(self, 'contract_tree') and self.contract_tree.winfo_exists():
            self.contract_tree.heading(db_schema.COL_CONTRACT_ID, text=localization._("contract_header_id"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_EMP_ID, text=localization._("contract_header_emp_id"))
            self.contract_tree.heading("employee_name", text=localization._("contract_header_emp_name"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_TYPE, text=localization._("contract_header_type"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_START_DATE, text=localization._("contract_header_start_date"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_CURRENT_END_DATE, text=localization._("contract_header_end_date"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_LIFECYCLE_STATUS, text=localization._("contract_header_lifecycle_status"))
            self.contract_tree.heading(db_schema.COL_CONTRACT_APPROVAL_STATUS, text=localization._("contract_header_approval_status"))
            self.contract_tree.heading("assigned_approver_username", text=localization._("contract_header_approver"))

    def _populate_employee_filter_combo_contract(self):
        # Logic to populate self.employee_filter_combo_contract
        populate_employee_combobox(
            self.employee_filter_combo_contract, tk.StringVar(), db_queries.list_all_employees,
            include_active_only=False, empty_option_text=localization._("contract_filter_all_employees")
        )
        self.employee_filter_combo_contract.config(textvariable=self.employee_filter_var_contract) # Re-link var
        self.employee_filter_combo_contract.set(localization._("contract_filter_all_employees")) # Set default text

    def _populate_status_filter_combo_contract(self):
        # Logic to populate self.status_filter_combo_contract
        self.status_filter_combo_contract['values'] = [localization._("contract_filter_all_statuses")] + db_schema.VALID_CONTRACT_TYPES + ['Draft', 'Active', 'Expired', 'Terminated', 'Upcoming Renewal', 'Pending Approval', 'Approved', 'Rejected']
        self.status_filter_combo_contract.set(localization._("contract_filter_all_statuses")) # Set default text

    def _set_default_employee_filter_contract(self):
        # Logic to set default employee in the filter combobox
        if self.default_emp_id:
            try:
                emp_details = db_queries.view_employee_details(self.default_emp_id)
                if emp_details:
                    display_text = f"{emp_details[db_schema.COL_EMP_NAME]} ({emp_details[db_schema.COL_EMP_ID]})"
                    if display_text in self.employee_filter_combo_contract['values']:
                        self.employee_filter_var_contract.set(display_text)
                        self._load_contracts_to_tree() # Load for the default employee
            except db_queries.EmployeeNotFoundError:
                logger.warning(f"Default employee ID {self.default_emp_id} not found for contract filter.")
            except Exception as e:
                logger.error(f"Error setting default employee filter for contracts: {e}")

    def _load_contracts_to_tree(self):
        for item in self.contract_tree.get_children():
            self.contract_tree.delete(item)
        self.current_selected_contract_id = None
        self._on_contract_select() # Disable buttons

        emp_id_filter = extract_id_from_combobox_selection(self.employee_filter_var_contract.get()) if self.employee_filter_var_contract.get() != localization._("contract_filter_all_employees") else None
        status_filter = self.status_filter_var_contract.get() if self.status_filter_var_contract.get() != localization._("contract_filter_all_statuses") else None

        try:
            # Need a backend function to get contracts with filters and employee/approver names
            # Let's assume db_queries.get_contracts_db exists and supports these filters
            contracts = db_queries.get_contracts_db(
                employee_id=emp_id_filter,
                status=status_filter # This status filter might need refinement (lifecycle vs approval)
            )

            for contract in contracts:
                self.contract_tree.insert("", "end", iid=contract[db_schema.COL_CONTRACT_ID], values=(
                    contract[db_schema.COL_CONTRACT_ID],
                    contract[db_schema.COL_CONTRACT_EMP_ID],
                    contract.get("employee_name", "N/A"), # Assuming join provides this
                    contract.get(db_schema.COL_CONTRACT_TYPE, "N/A"),
                    contract.get(db_schema.COL_CONTRACT_START_DATE, "N/A"),
                    contract.get(db_schema.COL_CONTRACT_CURRENT_END_DATE, "N/A"),
                    contract.get(db_schema.COL_CONTRACT_LIFECYCLE_STATUS, "N/A"),
                    contract.get(db_schema.COL_CONTRACT_APPROVAL_STATUS, "N/A"),
                    contract.get("assigned_approver_username", "N/A") # Assuming join provides this
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("contract_error_loading_list", error=e), parent=self)
        except Exception as e:
            logger.error(f"Unexpected error loading contracts: {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("contract_error_loading_list_unexpected", error=e), parent=self)

    def _on_contract_select(self, event=None):
        selected_item_iid = self.contract_tree.focus()
        is_selected = bool(selected_item_iid)
        self.current_selected_contract_id = int(selected_item_iid) if is_selected else None

        self.view_details_btn.config(state="normal" if is_selected else "disabled")
        self.edit_contract_btn.config(state="normal" if is_selected else "disabled") # Enable edit if selected

        # Approval buttons state depends on selection AND approval status
        can_approve_reject = False
        if is_selected:
            item_values = self.contract_tree.item(selected_item_iid, "values")
            approval_status = item_values[7] if len(item_values) > 7 else "N/A"
            # Check if the current user is the assigned approver (requires fetching contract details)
            # For simplicity, just check if status is 'Pending Approval' for now
            if approval_status == 'Pending Approval':
                 # A more robust check would verify the assigned_approver_user_id matches the current user's ID
                 # This would require fetching the full contract details or storing approver ID in the treeview
                 # For now, enable if Pending Approval. The action method will do the full check.
                 can_approve_reject = True

        self.approve_contract_btn.config(state="normal" if can_approve_reject else "disabled")
        self.reject_contract_btn.config(state="normal" if can_approve_reject else "disabled")

    def _gui_create_new_contract_mgt(self):
        """Opens the ElectronicContractWindow to create a new contract."""
        # Optionally pre-fill employee if one is selected in the filter
        default_emp_id_for_new = extract_id_from_combobox_selection(self.employee_filter_var_contract.get()) if self.employee_filter_var_contract.get() != localization._("contract_filter_all_employees") else None

        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            employee_id=default_emp_id_for_new, # Pass default employee ID
            tracker_attr_name=f"active_electronic_contract_window_new" # Use a generic tracker for new
        )
        # Note: Refreshing the contract list after creation would require a callback from ElectronicContractWindow

    def _gui_view_contract_details(self):
        selected_id = self.current_selected_contract_id
        if not selected_id:
            messagebox.showwarning(localization._("contract_view_details_title"), localization._("contract_select_one_warning"), parent=self)
            return
        
        # Need a dedicated window or dialog to display full contract details (including terms, signatures, etc.)
        # For now, let's just fetch and show basic details in a messagebox or log.
        try:
            contract_details = db_queries.get_contract_details_by_id_db(selected_id) # Assumes this exists
            if contract_details:
                details_str = f"Contract ID: {contract_details[db_schema.COL_CONTRACT_ID]}\n"
                details_str += f"Employee: {contract_details.get('employee_name', 'N/A')} (ID: {contract_details[db_schema.COL_CONTRACT_EMP_ID]})\n"
                details_str += f"Type: {contract_details.get(db_schema.COL_CONTRACT_TYPE, 'N/A')}\n"
                details_str += f"Start Date: {contract_details.get(db_schema.COL_CONTRACT_START_DATE, 'N/A')}\n"
                details_str += f"End Date: {contract_details.get(db_schema.COL_CONTRACT_CURRENT_END_DATE, 'N/A')}\n"
                details_str += f"Lifecycle Status: {contract_details.get(db_schema.COL_CONTRACT_LIFECYCLE_STATUS, 'N/A')}\n"
                details_str += f"Approval Status: {contract_details.get(db_schema.COL_CONTRACT_APPROVAL_STATUS, 'N/A')}\n"
                details_str += f"Approver: {contract_details.get('assigned_approver_username', 'N/A')}\n"
                details_str += f"Custom Terms:\n{contract_details.get(db_schema.COL_CONTRACT_CUSTOM_TERMS, 'N/A')}"
                
                messagebox.showinfo(localization._("contract_details_title", contract_id=selected_id), details_str, parent=self)
                # TODO: Implement a proper modal window for viewing details, including linked PDF and signatures
            else:
                messagebox.showwarning(localization._("contract_view_details_title"), localization._("contract_not_found_warning", contract_id=selected_id), parent=self)

        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("contract_error_loading_details", error=e), parent=self)
        except Exception as e:
            logger.error(f"Unexpected error viewing contract details: {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("contract_error_loading_details_unexpected", error=e), parent=self)

    def _gui_edit_contract(self):
        selected_id = self.current_selected_contract_id
        if not selected_id:
            messagebox.showwarning(localization._("contract_edit_title"), localization._("contract_select_one_warning"), parent=self)
            return
        
        # Open the ElectronicContractWindow in edit mode for the selected contract
        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            contract_id=selected_id, # Pass contract ID for edit mode
            mode='edit', # Indicate edit mode
            callback_on_save=self._load_contracts_to_tree, # Refresh list after save
            tracker_attr_name=f"active_electronic_contract_window_{selected_id}" # Track by contract ID
        )

    def _gui_approve_reject_contract(self, action: str):
        selected_id = self.current_selected_contract_id
        if not selected_id:
            messagebox.showwarning(localization._("contract_approval_title"), localization._("contract_select_one_warning"), parent=self)
            return

        if not self.parent_app.current_user_details:
            messagebox.showerror(localization._("error_title"), localization._("user_session_missing_error"), parent=self)
            return
        current_user_id = self.parent_app.current_user_details.get(db_schema.COL_USER_ID)
        if current_user_id is None:
             messagebox.showerror(localization._("error_title"), localization._("user_id_not_identified_error"), parent=self)
             return

        confirm_message = localization._(f"contract_confirm_{action.lower()}_message", contract_id=selected_id)
        if messagebox.askyesno(localization._(f"contract_confirm_{action.lower()}_title"), confirm_message, parent=self, icon='question'):
            comments = simpledialog.askstring(localization._("contract_approval_comments_title"), localization._("contract_approval_comments_prompt"), parent=self)
            # comments can be None if user cancels
            try:
                # Need a backend function to update contract approval status
                # Let's assume db_queries.update_contract_approval_status_db exists
                db_queries.update_contract_approval_status_db(
                    selected_id, action, comments, current_user_id
                )
                messagebox.showinfo(localization._("success_title"), localization._(f"contract_{action.lower()}_success_message", contract_id=selected_id), parent=self)
                self._load_contracts_to_tree() # Refresh list
            except db_queries.DatabaseOperationError as e:
                messagebox.showerror(localization._("error_title"), localization._(f"contract_error_{action.lower()}", error=e), parent=self)
            except db_queries.HRException as e: # Catch specific HRException from backend (e.g., not pending)
                 messagebox.showwarning(localization._("contract_approval_warning_title"), str(e), parent=self)
            except Exception as e:
                logger.error(f"Unexpected error processing contract approval {action} for ID {selected_id}: {e}", exc_info=True)
                messagebox.showerror(localization._("error_title"), localization._(f"contract_error_{action.lower()}_unexpected", error=e), parent=self)
