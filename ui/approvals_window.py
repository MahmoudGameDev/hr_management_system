# ui/approvals_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, List, Dict, Any
from datetime import datetime

from .themed_toplevel import ThemedToplevel
from utils.localization import _
from utils.gui_utils import extract_id_from_combobox_selection, BusyContext
from data import queries as db_queries
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # Added import
from data import database as db_schema # For constants
from utils.exceptions import DatabaseOperationError, HRException
import logging

logger = logging.getLogger(__name__)

APPROVAL_TYPE_LEAVE = "Leave Requests"
APPROVAL_TYPE_CONTRACT = "Contract Approvals"

class ApprovalsWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("approvals_window_title"))
        self.geometry("1150x800")

        self.current_user_id = self.parent_app.current_user_details.get(db_schema.COL_USER_ID)
        if not self.current_user_id:
            messagebox.showerror(_("error_title"), _("approvals_user_not_identified_error"), parent=self)
            self.destroy()
            return

        self.selected_item_id: Optional[int] = None
        self.selected_item_type: Optional[str] = None
        self.pending_items_cache: List[Dict[str, Any]] = []

        # --- Top Controls ---
        controls_frame = ttk.Frame(self, padding="10")
        controls_frame.pack(side="top", fill="x", pady=5)

        ttk.Label(controls_frame, text=_("approvals_type_label")).pack(side="left", padx=(0, 5))
        self.approval_type_var = tk.StringVar(value=_(APPROVAL_TYPE_LEAVE))
        self.approval_type_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.approval_type_var,
            values=[_(APPROVAL_TYPE_LEAVE), _(APPROVAL_TYPE_CONTRACT)],
            state="readonly",
            width=20
        )
        self.approval_type_combo.pack(side="left", padx=5)
        self.approval_type_combo.bind("<<ComboboxSelected>>", self._on_approval_type_change)

        self.refresh_btn = ttk.Button(controls_frame, text=_("approvals_refresh_button"), command=self._load_pending_items, bootstyle=db_schema.BS_VIEW_EDIT)
        self.refresh_btn.pack(side="left", padx=10)

        # --- Main Content PanedWindow ---
        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Left Pane: Pending Items List ---
        list_pane = ttk.Frame(main_paned_window, padding="5")
        main_paned_window.add(list_pane, weight=1)

        self.items_tree = ttk.Treeview(list_pane, show="headings")
        self.items_tree.pack(side="left", fill="both", expand=True)
        items_scrollbar = ttk.Scrollbar(list_pane, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=items_scrollbar.set)
        items_scrollbar.pack(side="right", fill="y")
        self.items_tree.bind("<<TreeviewSelect>>", self._on_item_select)

        # --- Right Pane: Details and Actions ---
        details_actions_pane = ttk.Frame(main_paned_window, padding="5")
        main_paned_window.add(details_actions_pane, weight=2)

        details_lf = ttk.LabelFrame(details_actions_pane, text=_("approvals_details_label"), padding="10")
        details_lf.pack(fill="both", expand=True, pady=(0, 10))

        self.details_text = tk.Text(details_lf, height=15, wrap="word", relief="solid", borderwidth=1, state="disabled")
        self.details_text.pack(fill="both", expand=True)
        # Theming for self.details_text will be handled by update_local_theme_elements

        actions_lf = ttk.LabelFrame(details_actions_pane, text=_("approvals_actions_label"), padding="10")
        actions_lf.pack(fill="x")

        ttk.Label(actions_lf, text=_("approvals_comments_label")).pack(anchor="w")
        self.comments_entry = ttk.Entry(actions_lf, width=60)
        self.comments_entry.pack(fill="x", pady=(0, 10))

        buttons_frame = ttk.Frame(actions_lf)
        buttons_frame.pack(fill="x")

        self.approve_btn = ttk.Button(buttons_frame, text=_("approvals_approve_button"), command=lambda: self._process_approval("Approved"), state="disabled", bootstyle=db_schema.BS_ADD)
        self.approve_btn.pack(side="left", padx=5)

        self.reject_btn = ttk.Button(buttons_frame, text=_("approvals_reject_button"), command=lambda: self._process_approval("Rejected"), state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.reject_btn.pack(side="left", padx=5)

        self._load_pending_items()
        self.update_idletasks() # Ensure widgets are ready for theming

    def _setup_tree_columns(self, item_type: str):
        for col in self.items_tree.get_children():
            self.items_tree.delete(col)
        
        if item_type == _(APPROVAL_TYPE_LEAVE):
            self.items_tree["columns"] = ("id", "employee_name", "leave_type", "start_date", "end_date", "request_date")
            self.items_tree.heading("id", text=_("approvals_col_id"))
            self.items_tree.heading("employee_name", text=_("approvals_col_employee"))
            self.items_tree.heading("leave_type", text=_("approvals_col_leave_type"))
            self.items_tree.heading("start_date", text=_("approvals_col_start_date"))
            self.items_tree.heading("end_date", text=_("approvals_col_end_date"))
            self.items_tree.heading("request_date", text=_("approvals_col_request_date"))
            self.items_tree.column("id", width=50, anchor="e", stretch=tk.NO)
            self.items_tree.column("employee_name", width=150)
            self.items_tree.column("leave_type", width=100)
        elif item_type == _(APPROVAL_TYPE_CONTRACT):
            self.items_tree["columns"] = ("id", "employee_name", "contract_type", "start_date", "created_at")
            self.items_tree.heading("id", text=_("approvals_col_id"))
            self.items_tree.heading("employee_name", text=_("approvals_col_employee"))
            self.items_tree.heading("contract_type", text=_("approvals_col_contract_type"))
            self.items_tree.heading("start_date", text=_("approvals_col_start_date"))
            self.items_tree.heading("created_at", text=_("approvals_col_created_date"))
            self.items_tree.column("id", width=50, anchor="e", stretch=tk.NO)
            self.items_tree.column("employee_name", width=150)
            self.items_tree.column("contract_type", width=120)

    def _on_approval_type_change(self, event=None):
        self._load_pending_items()

    def _load_pending_items(self):
        selected_type_display = self.approval_type_var.get()
        self._setup_tree_columns(selected_type_display)
        self.pending_items_cache = []
        self.selected_item_id = None
        self.selected_item_type = None
        self._clear_details()
        self.approve_btn.config(state="disabled")
        self.reject_btn.config(state="disabled")

        with BusyContext(self):
            try:
                if selected_type_display == _(APPROVAL_TYPE_LEAVE):
                    self.pending_items_cache = db_queries.get_pending_leave_approvals_for_user_db(self.current_user_id)
                    for item in self.pending_items_cache:
                        self.items_tree.insert("", "end", iid=item[db_schema.COL_LR_ID], values=(
                            item[db_schema.COL_LR_ID],
                            item.get("employee_name", "N/A"),
                            item[db_schema.COL_LR_LEAVE_TYPE],
                            item[db_schema.COL_LR_START_DATE],
                            item[db_schema.COL_LR_END_DATE],
                            item[db_schema.COL_LR_REQUEST_DATE]
                        ))
                elif selected_type_display == _(APPROVAL_TYPE_CONTRACT):
                    self.pending_items_cache = db_queries.get_pending_contract_approvals_for_user_db(self.current_user_id)
                    for item in self.pending_items_cache:
                        self.items_tree.insert("", "end", iid=item[db_schema.COL_CONTRACT_ID], values=(
                            item[db_schema.COL_CONTRACT_ID],
                            item.get("employee_name", "N/A"),
                            item[db_schema.COL_CONTRACT_TYPE],
                            item[db_schema.COL_CONTRACT_START_DATE],
                            item[db_schema.COL_CONTRACT_CREATED_AT]
                        ))
            except DatabaseOperationError as e:
                logger.error(f"Error loading pending approvals: {e}")
                messagebox.showerror(_("error_title"), _("approvals_load_error", error=e), parent=self)

    def _on_item_select(self, event=None):
        selected_tree_item = self.items_tree.focus()
        if not selected_tree_item:
            self.selected_item_id = None
            self.selected_item_type = None
            self._clear_details()
            self.approve_btn.config(state="disabled")
            self.reject_btn.config(state="disabled")
            return

        self.selected_item_id = int(selected_tree_item) # IID is the item ID
        self.selected_item_type = self.approval_type_var.get()
        
        item_details = next((item for item in self.pending_items_cache if item.get(db_schema.COL_LR_ID) == self.selected_item_id or item.get(db_schema.COL_CONTRACT_ID) == self.selected_item_id), None)

        if item_details:
            self._display_item_details(item_details)
            self.approve_btn.config(state="normal")
            self.reject_btn.config(state="normal")
        else:
            self._clear_details()
            self.approve_btn.config(state="disabled")
            self.reject_btn.config(state="disabled")
    
    def update_local_theme_elements(self):
        """Applies theme to non-ttk widgets like tk.Text."""
        super().update_local_theme_elements()  # Call parent's method
        if hasattr(self, 'details_text') and self.details_text.winfo_exists():
            current_theme = self.parent_app.get_current_theme() if self.parent_app else "litera"
            palette = get_theme_palette_global(current_theme)
            _theme_text_widget_global(self.details_text, palette)
        # If self.comments_entry was a tk.Text, you'd theme it here too.
        # Since it's a ttk.Entry, ttkbootstrap handles its theming.
 

    def _clear_details(self):
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.config(state="disabled")
        self.comments_entry.delete(0, tk.END)

    def _display_item_details(self, item: Dict[str, Any]):
        self._clear_details()
        self.details_text.config(state="normal")
        
        if self.selected_item_type == _(APPROVAL_TYPE_LEAVE):
            details_str = _("approvals_leave_details_format",
                            id=item.get(db_schema.COL_LR_ID),
                            employee=item.get("employee_name", "N/A"),
                            type=item.get(db_schema.COL_LR_LEAVE_TYPE),
                            start=item.get(db_schema.COL_LR_START_DATE),
                            end=item.get(db_schema.COL_LR_END_DATE),
                            reason=item.get(db_schema.COL_LR_REASON, _("approvals_no_reason_provided")),
                            requested_on=item.get(db_schema.COL_LR_REQUEST_DATE))
            # Check for department busy status
            try:
                emp_details = db_queries.get_employee_by_id_db(item[db_schema.COL_LR_EMP_ID])
                dept_id = emp_details.get(db_schema.COL_EMP_DEPARTMENT_ID)
                if dept_id and db_queries.is_department_busy_for_leave(dept_id, item[db_schema.COL_LR_START_DATE], item[db_schema.COL_LR_END_DATE], item[db_schema.COL_LR_EMP_ID]):
                    details_str += f"\n\n{_('approvals_dept_busy_warning')}"
            except Exception as e_busy:
                logger.warning(f"Could not check department busy status for leave {item.get(db_schema.COL_LR_ID)}: {e_busy}")

        elif self.selected_item_type == _(APPROVAL_TYPE_CONTRACT):
            # Fetch full contract details if needed, or use cached if sufficient
            full_contract_details = db_queries.get_contract_details_by_id_db(item.get(db_schema.COL_CONTRACT_ID))
            if full_contract_details:
                item = full_contract_details # Use full details

            details_str = _("approvals_contract_details_format",
                            id=item.get(db_schema.COL_CONTRACT_ID),
                            employee=item.get("employee_name", "N/A"),
                            type=item.get(db_schema.COL_CONTRACT_TYPE),
                            start=item.get(db_schema.COL_CONTRACT_START_DATE),
                            end=item.get(db_schema.COL_CONTRACT_CURRENT_END_DATE, _("approvals_not_applicable")),
                            duration_years=item.get(db_schema.COL_CONTRACT_INITIAL_DURATION_YEARS, _("approvals_not_applicable")),
                            auto_renew= _("yes") if item.get(db_schema.COL_CONTRACT_IS_AUTO_RENEWABLE) else _("no"),
                            renewal_term=item.get(db_schema.COL_CONTRACT_RENEWAL_TERM_YEARS, _("approvals_not_applicable")),
                            notice_days=item.get(db_schema.COL_CONTRACT_NOTICE_PERIOD_DAYS, _("approvals_not_applicable")),
                            custom_terms=item.get(db_schema.COL_CONTRACT_CUSTOM_TERMS, _("approvals_none_text"))
                            )
        else:
            details_str = _("approvals_select_item_prompt")

        self.details_text.insert("1.0", details_str)
        self.details_text.config(state="disabled")

    def _process_approval(self, new_status: str):
        if self.selected_item_id is None or self.selected_item_type is None:
            messagebox.showwarning(_("warning_title"), _("approvals_no_item_selected_warning"), parent=self)
            return

        comments = self.comments_entry.get().strip()
        confirm_action = _("approvals_confirm_approve_action") if new_status == "Approved" else _("approvals_confirm_reject_action")
        
        if not messagebox.askyesno(_("approvals_confirm_action_title"), confirm_action, parent=self):
            return

        with BusyContext(self):
            try:
                success = False
                if self.selected_item_type == _(APPROVAL_TYPE_LEAVE):
                    success = db_queries.update_leave_request_approval_status_db(
                        self.selected_item_id, new_status, comments, self.current_user_id
                    )
                elif self.selected_item_type == _(APPROVAL_TYPE_CONTRACT):
                    success = db_queries.update_contract_approval_status_db(
                        self.selected_item_id, new_status, comments, self.current_user_id
                    )
                
                if success:
                    messagebox.showinfo(_("success_title"), _("approvals_action_success_message", action=new_status.lower()), parent=self)
                    self._load_pending_items() # Refresh list
                else: # Should not happen if DB functions raise exceptions on failure
                    messagebox.showerror(_("error_title"), _("approvals_action_failed_message", action=new_status.lower()), parent=self)

            except (DatabaseOperationError, HRException) as e:
                logger.error(f"Error processing approval for item {self.selected_item_id} ({self.selected_item_type}): {e}")
                messagebox.showerror(_("error_title"), _("approvals_processing_error", error=e), parent=self)
            except Exception as e_generic:
                logger.error(f"Unexpected error processing approval: {e_generic}", exc_info=True)
                messagebox.showerror(_("error_title"), _("approvals_unexpected_processing_error", error=e_generic), parent=self)

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("approvals_window_title"))
        
        # Update controls_frame labels and buttons
        self.approval_type_combo.master.winfo_children()[0].config(text=_("approvals_type_label")) # Assuming label is first child
        self.approval_type_combo['values'] = [_(APPROVAL_TYPE_LEAVE), _(APPROVAL_TYPE_CONTRACT)]
        self.approval_type_var.set(_(APPROVAL_TYPE_LEAVE) if self.approval_type_var.get() == APPROVAL_TYPE_LEAVE else _(APPROVAL_TYPE_CONTRACT)) # Re-set based on current logical value
        self.refresh_btn.config(text=_("approvals_refresh_button"))

        # Update LabelFrame titles
        self.details_text.master.config(text=_("approvals_details_label")) # details_lf
        self.comments_entry.master.master.config(text=_("approvals_actions_label")) # actions_lf

        # Update actions_lf labels and buttons
        self.comments_entry.master.winfo_children()[0].config(text=_("approvals_comments_label")) # Assuming label is first child
        self.approve_btn.config(text=_("approvals_approve_button"))
        self.reject_btn.config(text=_("approvals_reject_button"))

        # Reload/re-setup tree columns to update headers
        self._setup_tree_columns(self.approval_type_var.get())
        # Re-load data to reflect any language changes in data itself (if applicable, usually not for IDs/dates)
        self._load_pending_items() 
        # If an item is selected, re-display its details
        if self.selected_item_id:
            item_details = next((item for item in self.pending_items_cache if item.get(db_schema.COL_LR_ID) == self.selected_item_id or item.get(db_schema.COL_CONTRACT_ID) == self.selected_item_id), None)
            if item_details:
                self._display_item_details(item_details)