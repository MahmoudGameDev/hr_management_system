# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\payroll_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText # If payslip details are shown in ScrolledText
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, date as dt_date, timedelta # type: ignore

# --- Project-specific imports ---
from utils import export_utils # For accounting export
from data import database as db_schema # For COL_... constants
from data import queries as db_queries # For payroll related DB functions
from utils.localization import _ # For _()
from utils.gui_utils import extract_id_from_combobox_selection, populate_employee_combobox
from utils.exceptions import EmployeeNotFoundError, InvalidInputError, DatabaseOperationError # Import custom exceptions
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # Import theming utils
from utils import pdf_utils # Import the new pdf_utils
from typing import List, Dict, Optional, Any, Union, Tuple
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

# --- Payroll Window ---
class PayrollWindow(ThemedToplevel):
    TRACKER_NAME = "active_payroll_window" # Define tracker name

    def __init__(self, parent, app_instance, default_emp_id: Optional[str] = None):
        super().__init__(parent, app_instance)
        self.title_key = "payroll_window_title" # For localization
        self.title(_(self.title_key))
        self.geometry("800x650") # Increased size
        
        self.default_emp_id = default_emp_id
        self.translatable_widgets_payroll = [] # For PayrollWindow specific translatable widgets
        self.calculated_payslip_data = None # To store data for saving
        
        self.notebook = ttk.Notebook(self)
        # Pack the notebook early, so its child tab frames have a valid parent path
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        # Create tab frames
        self.generate_payslip_tab = ttk.Frame(self.notebook, padding="10")
        self.rewards_penalties_tab = ttk.Frame(self.notebook, padding="10")
        self.salary_advances_tab = ttk.Frame(self.notebook, padding="10")
        # Add other tabs later: History

        # Create widgets within the tab frames
        # The creation of widgets will now be conditional based on view mode

        # Add tab frames to the notebook
        self.notebook.add(self.generate_payslip_tab, text=_("payroll_tab_generate"))
        self._add_translatable_widget_payroll(self.notebook, "payroll_tab_generate", attr="tab", tab_id=self.generate_payslip_tab)
        self.notebook.add(self.salary_advances_tab, text=_("payroll_tab_advances"))
        self._add_translatable_widget_payroll(self.notebook, "payroll_tab_advances", attr="tab", tab_id=self.salary_advances_tab)
        self.notebook.add(self.rewards_penalties_tab, text=_("payroll_tab_rewards_penalties"))
        self._add_translatable_widget_payroll(self.notebook, "payroll_tab_rewards_penalties", attr="tab", tab_id=self.rewards_penalties_tab)

        if self.default_emp_id:
            self._configure_for_employee_view()
        else:
            self._configure_for_admin_view()

        self.update_idletasks() # Ensure all widgets are processed before ThemedToplevel's after(50) call
        # self._load_payslip_history_tab is not defined in this class, seems like a leftover comment or intended for future.

    def _add_translatable_widget_payroll(self, widget, key: str, attr: str = "text", tab_id: Optional[Any] = None):
        """Helper to register translatable widgets for PayrollWindow."""
        # For PayrollWindow, all registered widgets are simple labels or buttons using 'text'
        # or LabelFrames using 'title'.
        actual_attr = "title" if isinstance(widget, ttk.LabelFrame) else attr
        self.translatable_widgets_payroll.append({"widget": widget, "key": key, "attr": actual_attr, "tab_id": tab_id})

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("payroll_window_title"))
        # Tab texts are updated via _add_translatable_widget_payroll and the loop below
        # The specific logic for setting tab text during init/view_change is handled there.
        # This method will re-apply those translations if the language changes while window is open.


        # Update widgets registered with _add_translatable_widget_payroll
        for item_info in self.translatable_widgets_payroll:
            widget = item_info["widget"]
            key = item_info["key"]
            attr_to_update = item_info.get("attr", "text")
            tab_id_for_refresh = item_info.get("tab_id")
            if widget.winfo_exists():
                try:
                    if attr_to_update == "tab" and isinstance(widget, ttk.Notebook) and tab_id_for_refresh:
                        widget.tab(tab_id_for_refresh, text=_(key))
                    elif attr_to_update == "text": 
                        widget.config(text=_(key))
                    elif attr_to_update == "title": widget.config(text=_(key)) # For LabelFrames
                except tk.TclError: pass # pragma: no cover
        # Update treeview headers for advances tab
        if hasattr(self, 'adv_tree') and self.adv_tree.winfo_exists():
            self.adv_tree.heading(db_schema.COL_ADV_ID, text=_("payroll_adv_header_id"))
            self.adv_tree.heading(db_schema.COL_ADV_DATE, text=_("payroll_adv_header_date"))
            self.adv_tree.heading(db_schema.COL_ADV_AMOUNT, text=_("payroll_adv_header_amount"))
            self.adv_tree.heading(db_schema.COL_ADV_REPAY_AMOUNT_PER_PERIOD, text=_("payroll_adv_header_repay_per_period"))
            self.adv_tree.heading(db_schema.COL_ADV_TOTAL_REPAID, text=_("payroll_adv_header_total_repaid"))
            self.adv_tree.heading(db_schema.COL_ADV_STATUS, text=_("payroll_adv_header_status"))
        # Update treeview headers for rewards/penalties tab
        if hasattr(self, 'rp_tree') and self.rp_tree.winfo_exists():
            self.rp_tree.heading("item_id", text=_("payroll_rp_header_id"))
            self.rp_tree.heading("item_type_col", text=_("payroll_rp_header_item_type"))
            self.rp_tree.heading("description_col", text=_("payroll_rp_header_description"))
            self.rp_tree.heading("amount_col", text=_("payroll_rp_header_amount"))
            self.rp_tree.heading("eff_date_col", text=_("payroll_rp_header_eff_date"))
        
        # If payslip history tree exists (for employee view)
        if hasattr(self, 'payslip_history_tree') and self.payslip_history_tree.winfo_exists():
            self.payslip_history_tree.heading(db_schema.COL_PAY_ID, text=_("payslip_history_header_id"))
            self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_START, text=_("payslip_history_header_period_start"))
            self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_END, text=_("payslip_history_header_period_end"))
            self.payslip_history_tree.heading(db_schema.COL_PAY_NET_PAY, text=_("payslip_history_header_net_pay"))
            self.payslip_history_tree.heading(db_schema.COL_PAY_GENERATION_DATE, text=_("payslip_history_header_generated_on"))

    def _configure_for_employee_view(self):
        """Configures the UI for an employee viewing their own payslips."""
        logger.info(f"Configuring PayrollWindow for employee view (ID: {self.default_emp_id})")
        # For employee view, we might only show a "Payslip History" tab
        # We will reuse the first tab (generate_payslip_tab) for this.

        # Clear any existing widgets from the first tab if it was already configured for admin
        for widget in self.generate_payslip_tab.winfo_children():
            widget.destroy()

        self._create_payslip_history_tab_for_employee(self.generate_payslip_tab) # Reuse the first tab frame
        
        # Hide other tabs or reconfigure them
        if hasattr(self, 'salary_advances_tab') and self.salary_advances_tab.winfo_exists():
            self.notebook.hide(self.salary_advances_tab)
            logger.debug("Hid salary_advances_tab for employee view.")
        if hasattr(self, 'rewards_penalties_tab') and self.rewards_penalties_tab.winfo_exists():
            self.notebook.hide(self.rewards_penalties_tab)
            logger.debug("Hid rewards_penalties_tab for employee view.")
        
        self.notebook.tab(self.generate_payslip_tab, text=_("payroll_tab_my_payslips")) # Rename the first tab
        # The translatable widget for this tab text should be updated if it was already added, or added if new.
        # We can re-register it to ensure it's updated correctly on language change.
        self._add_translatable_widget_payroll(self.notebook, "payroll_tab_my_payslips", attr="tab", tab_id=self.generate_payslip_tab) # This will add or update

    def _configure_for_admin_view(self):
        """Configures the UI for admin/general payroll management."""
        logger.info("Configuring PayrollWindow for admin view")
        self._create_generate_payslip_widgets(self.generate_payslip_tab)
        self._create_rewards_penalties_widgets(self.rewards_penalties_tab)
        self._create_salary_advances_widgets(self.salary_advances_tab)
        
        # Ensure tabs are visible if they were hidden
        if hasattr(self, 'salary_advances_tab') and self.salary_advances_tab.winfo_exists():
            self.notebook.add(self.salary_advances_tab) # Re-add if hidden (or use select if just hidden)
        if hasattr(self, 'rewards_penalties_tab') and self.rewards_penalties_tab.winfo_exists():
            self.notebook.add(self.rewards_penalties_tab)
        # Potentially add a fourth tab for "All Payslip History" for admins
                
    def _create_generate_payslip_widgets(self, tab_frame):
        controls_frame = ttk.Frame(tab_frame)
        controls_frame.pack(side="top", fill="x", pady=5)

        emp_lbl = ttk.Label(controls_frame, text=_("payroll_employee_label")); emp_lbl.pack(side="left", padx=(0, 5)); self._add_translatable_widget_payroll(emp_lbl, "payroll_employee_label")
        self.payroll_employee_var = tk.StringVar()
        self.payroll_employee_combo = ttk.Combobox(controls_frame, textvariable=self.payroll_employee_var, state="readonly", width=30)
        self.payroll_employee_combo.pack(side="left", padx=5)
        self._populate_payroll_employee_dropdown()

        # Default to current month (logic for dates remains the same)
        today = dt_date.today()
        first_day_current_month = today.replace(day=1)
        # Last day of current month: go to first day of next month, then subtract one day
        if today.month == 12:
            last_day_current_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else: # Ensure datetime.timedelta is used
            last_day_current_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        start_lbl = ttk.Label(controls_frame, text=_("payroll_period_start_label")); start_lbl.pack(side="left", padx=(10,5)); self._add_translatable_widget_payroll(start_lbl, "payroll_period_start_label")
        self.period_start_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.period_start_entry.date = first_day_current_month
        self.period_start_entry.pack(side="left", padx=5)

        end_lbl = ttk.Label(controls_frame, text=_("payroll_period_end_label")); end_lbl.pack(side="left", padx=(10,5)); self._add_translatable_widget_payroll(end_lbl, "payroll_period_end_label")
        self.period_end_entry = DateEntry(controls_frame, width=12, dateformat='%Y-%m-%d')
        self.period_end_entry.date = last_day_current_month
        self.period_end_entry.pack(side="left", padx=5)

        self.calculate_btn = ttk.Button(controls_frame, text=_("payroll_calculate_button"), command=self._gui_calculate_payslip, bootstyle=db_schema.BS_ADD)
        self.calculate_btn.pack(side="left", padx=10)

        self._add_translatable_widget_payroll(self.calculate_btn, "payroll_calculate_button")

        # --- Payslip Details Display Area (Replaces Text widget) ---
        self.payslip_details_display_frame = ttk.Frame(tab_frame, padding="10")
        self.payslip_details_display_frame.pack(fill="both", expand=True, pady=10)
        self._create_payslip_display_structure(self.payslip_details_display_frame)

        action_buttons_frame = ttk.Frame(tab_frame)
        action_buttons_frame.pack(side="bottom", fill="x", pady=5)
        self.save_payslip_btn = ttk.Button(action_buttons_frame, text=_("payroll_save_button"), command=self._gui_save_payslip, state="disabled", bootstyle=db_schema.BS_ADD)
        self.save_payslip_btn.pack(side="right", padx=5)
        self._add_translatable_widget_payroll(self.save_payslip_btn, "payroll_save_button")
        self.export_payslip_pdf_btn = ttk.Button(action_buttons_frame, text=_("payroll_export_pdf_button"), command=self._gui_export_payslip_pdf, state="disabled", bootstyle=db_schema.BS_NEUTRAL)
        self.export_payslip_pdf_btn.pack(side="right", padx=5) # Pack next to save
        self._add_translatable_widget_payroll(self.export_payslip_pdf_btn, "payroll_export_pdf_button")

    def _create_payslip_display_structure(self, parent_frame):
        """Creates the structured layout for displaying payslip details."""
        self.payslip_detail_vars = {} # To store StringVars for dynamic labels

        # --- Header Info ---
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill="x", pady=(0,10))
        self.payslip_detail_vars["employee_name_period"] = tk.StringVar(value="Employee: N/A | Period: N/A")
        ttk.Label(header_frame, textvariable=self.payslip_detail_vars["employee_name_period"], font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.payslip_detail_vars["generation_date"] = tk.StringVar(value="Generated: N/A")
        ttk.Label(header_frame, textvariable=self.payslip_detail_vars["generation_date"], font=("Helvetica", 9)).pack(anchor="w")

        # --- Main Content PanedWindow (Earnings/Deductions side-by-side) ---
        content_paned_window = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        content_paned_window.pack(fill="both", expand=True, pady=5)

        # --- Earnings Section ---
        earnings_lf = ttk.LabelFrame(content_paned_window, text=_("payslip_earnings_section_title"), padding="10") # Add key
        content_paned_window.add(earnings_lf, weight=1)
        self._add_translatable_widget_payroll(earnings_lf, "payslip_earnings_section_title", attr="title")
        self.earnings_details_frame = ttk.Frame(earnings_lf) # Frame to hold dynamic earning items
        self.earnings_details_frame.pack(fill="x")

        # --- Deductions Section ---
        deductions_lf = ttk.LabelFrame(content_paned_window, text=_("payslip_deductions_section_title"), padding="10") # Add key
        content_paned_window.add(deductions_lf, weight=1)
        self._add_translatable_widget_payroll(deductions_lf, "payslip_deductions_section_title", attr="title")
        self.deductions_details_frame = ttk.Frame(deductions_lf) # Frame to hold dynamic deduction items
        self.deductions_details_frame.pack(fill="x")

        # --- Summary Section ---
        summary_lf = ttk.LabelFrame(parent_frame, text=_("payslip_summary_section_title"), padding="10") # Add key
        summary_lf.pack(fill="x", pady=(10,0))
        self._add_translatable_widget_payroll(summary_lf, "payslip_summary_section_title", attr="title")
        summary_lf.columnconfigure(1, weight=1)

        row_idx = 0
        summary_fields = [
            ("payslip_gross_salary_label", "gross_salary"),
            ("payslip_total_deductions_label", "total_deductions_combined"), # New var for combined deductions
            ("payslip_net_pay_label", "net_pay")
        ]
        for label_key, var_key in summary_fields:
            lbl = ttk.Label(summary_lf, text=_(label_key), font=("Helvetica", 10, "bold" if "net_pay" in var_key else "normal"))
            lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
            self._add_translatable_widget_payroll(lbl, label_key)
            
            self.payslip_detail_vars[var_key] = tk.StringVar(value="0.00")
            val_lbl = ttk.Label(summary_lf, textvariable=self.payslip_detail_vars[var_key], font=("Helvetica", 10, "bold" if "net_pay" in var_key else "normal"))
            val_lbl.grid(row=row_idx, column=1, sticky="e", padx=5, pady=2)
            row_idx +=1

        # Attendance Info
        self.payslip_detail_vars["attendance_info"] = tk.StringVar(value="Workdays: N/A, Present: N/A")
        ttk.Label(summary_lf, textvariable=self.payslip_detail_vars["attendance_info"], font=("Helvetica", 9, "italic")).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Notes
        notes_lf = ttk.LabelFrame(parent_frame, text=_("payslip_notes_section_title"), padding="5") # Add key
        notes_lf.pack(fill="x", pady=(5,0))
        self._add_translatable_widget_payroll(notes_lf, "payslip_notes_section_title", attr="title")
        self.payslip_notes_text_display = tk.Text(notes_lf, height=2, wrap="word", relief="flat", state="disabled", font=("Helvetica", 9))
        self.payslip_notes_text_display.pack(fill="x", expand=True)
        # Theming for Text widget
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.payslip_notes_text_display, palette)

    def _add_detail_item(self, parent_frame, description: str, amount: float, is_bold: bool = False):
        """Helper to add a description-amount line to a frame."""
        item_frame = ttk.Frame(parent_frame)
        item_frame.pack(fill="x")
        font_style = ("Helvetica", 9, "bold" if is_bold else "normal")
        ttk.Label(item_frame, text=description, font=font_style).pack(side="left", padx=(0,10))
        ttk.Label(item_frame, text=f"{amount:,.2f}", font=font_style).pack(side="right")

    
    def _create_rewards_penalties_widgets(self, tab_frame):
        form_frame = ttk.LabelFrame(tab_frame, text=_("payroll_rp_form_title"), padding="10")
        form_frame.pack(side="top", fill="x", pady=10)
        self._add_translatable_widget_payroll(form_frame, "payroll_rp_form_title")
        
        # Employee Selection
        emp_lbl_rp = ttk.Label(form_frame, text=_("payroll_employee_label")); emp_lbl_rp.grid(row=0, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(emp_lbl_rp, "payroll_employee_label")
        self.rp_employee_var = tk.StringVar()
        self.rp_employee_combo = ttk.Combobox(form_frame, textvariable=self.rp_employee_var, state="readonly", width=35)
        self.rp_employee_combo.bind("<<ComboboxSelected>>", self._on_rp_employee_select)
        self.rp_employee_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=5)

        # Type: Reward or Penalty
        type_lbl_rp = ttk.Label(form_frame, text=_("payroll_rp_type_label")); type_lbl_rp.grid(row=1, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(type_lbl_rp, "payroll_rp_type_label")
        self.rp_type_var = tk.StringVar(value="Reward") # Default to Reward
        reward_radio = ttk.Radiobutton(form_frame, text=_("payroll_rp_reward_radio"), variable=self.rp_type_var, value="Reward")
        reward_radio.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        self._add_translatable_widget_payroll(reward_radio, "payroll_rp_reward_radio")
        penalty_radio = ttk.Radiobutton(form_frame, text=_("payroll_rp_penalty_radio"), variable=self.rp_type_var, value="Penalty")
        penalty_radio.grid(row=1, column=2, sticky="w", pady=5, padx=5)
        self._add_translatable_widget_payroll(penalty_radio, "payroll_rp_penalty_radio")

        # Description
        desc_lbl_rp = ttk.Label(form_frame, text=_("payroll_rp_description_label")); desc_lbl_rp.grid(row=2, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(desc_lbl_rp, "payroll_rp_description_label")
        self.rp_description_entry = ttk.Entry(form_frame, width=40)
        self.rp_description_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5, padx=5)

        # Amount
        amount_lbl_rp = ttk.Label(form_frame, text=_("payroll_rp_amount_label")); amount_lbl_rp.grid(row=3, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(amount_lbl_rp, "payroll_rp_amount_label")
        self.rp_amount_var = tk.StringVar()
        self.rp_amount_entry = ttk.Entry(form_frame, textvariable=self.rp_amount_var, width=15)
        self.rp_amount_entry.grid(row=3, column=1, sticky="w", pady=5, padx=5)

        # Effective Date
        eff_date_lbl_rp = ttk.Label(form_frame, text=_("payroll_rp_eff_date_label")); eff_date_lbl_rp.grid(row=4, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(eff_date_lbl_rp, "payroll_rp_eff_date_label")
        self.rp_eff_date_entry = DateEntry(form_frame, width=15, dateformat='%Y-%m-%d')
        self.rp_eff_date_entry.date = dt_date.today()
        self.rp_eff_date_entry.grid(row=4, column=1, sticky="w", pady=5, padx=5)

        # Add Button
        self.add_rp_btn = ttk.Button(form_frame, text=_("payroll_rp_add_item_button"), command=self._gui_add_reward_penalty, bootstyle=db_schema.BS_ADD)
        self.add_rp_btn.grid(row=5, column=1, columnspan=2, pady=10, sticky="e")
        self._add_translatable_widget_payroll(self.add_rp_btn, "payroll_rp_add_item_button")

        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(2, weight=1)

        # --- Display Area for Existing Rewards/Penalties ---
        rp_display_frame = ttk.LabelFrame(tab_frame, text=_("payroll_rp_existing_items_label"), padding="10") # Add key
        rp_display_frame.pack(fill="both", expand=True, pady=10)
        self._add_translatable_widget_payroll(rp_display_frame, "payroll_rp_existing_items_label", attr="title")

        self.rp_tree_cols = ("item_id", "item_type_col", "description_col", "amount_col", "eff_date_col") # Renamed for clarity
        self.rp_tree = ttk.Treeview(rp_display_frame, columns=self.rp_tree_cols, show="headings")

        self.rp_tree.heading("item_id", text=_("payroll_rp_header_id")) # Add key
        self.rp_tree.heading("item_type_col", text=_("payroll_rp_header_item_type")) # Add key (e.g., "Reward", "Penalty")
        self.rp_tree.heading("description_col", text=_("payroll_rp_header_description")) # Add key
        self.rp_tree.heading("amount_col", text=_("payroll_rp_header_amount")) # Add key
        self.rp_tree.heading("eff_date_col", text=_("payroll_rp_header_eff_date")) # Add key

        self.rp_tree.column("item_id", width=60, anchor="e", stretch=tk.NO)
        self.rp_tree.column("item_type_col", width=100, anchor="w")
        self.rp_tree.column("description_col", width=200, anchor="w", stretch=tk.YES)
        self.rp_tree.column("amount_col", width=100, anchor="e")
        self.rp_tree.column("eff_date_col", width=100, anchor="center")

        self.rp_tree.pack(side="left", fill="both", expand=True)
        rp_scrollbar = ttk.Scrollbar(rp_display_frame, orient="vertical", command=self.rp_tree.yview)
        self.rp_tree.configure(yscrollcommand=rp_scrollbar.set)
        rp_scrollbar.pack(side="right", fill="y")

        # Populate dropdown AFTER all widgets in this tab, including rp_tree, are created
        self._populate_rp_employee_dropdown()

    def _create_payslip_history_tab_for_employee(self, tab_frame):
        """Creates a tab to display payslip history for a single employee."""
        # Clear existing widgets from tab_frame if any
        for widget in tab_frame.winfo_children():
            widget.destroy()

        history_lf_key = "payslip_history_frame_title" # Add key
        history_frame = ttk.LabelFrame(tab_frame, text=_(history_lf_key), padding="10")
        history_frame.pack(fill="both", expand=True, pady=5)
        self._add_translatable_widget_payroll(history_frame, history_lf_key, attr="title")

        cols = (db_schema.COL_PAY_ID, db_schema.COL_PAY_PERIOD_START, db_schema.COL_PAY_PERIOD_END, db_schema.COL_PAY_NET_PAY, db_schema.COL_PAY_GENERATION_DATE)
        self.payslip_history_tree = ttk.Treeview(history_frame, columns=cols, show="headings")
        
        self.payslip_history_tree.heading(db_schema.COL_PAY_ID, text=_("payslip_history_header_id")) # Add key
        self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_START, text=_("payslip_history_header_period_start")) # Add key
        self.payslip_history_tree.heading(db_schema.COL_PAY_PERIOD_END, text=_("payslip_history_header_period_end")) # Add key
        self.payslip_history_tree.heading(db_schema.COL_PAY_NET_PAY, text=_("payslip_history_header_net_pay")) # Add key
        self.payslip_history_tree.heading(db_schema.COL_PAY_GENERATION_DATE, text=_("payslip_history_header_generated_on")) # Add key

        self.payslip_history_tree.column(db_schema.COL_PAY_ID, width=80, anchor="e", stretch=tk.NO)
        self.payslip_history_tree.column(db_schema.COL_PAY_PERIOD_START, width=120, anchor="center")
        self.payslip_history_tree.column(db_schema.COL_PAY_PERIOD_END, width=120, anchor="center")
        self.payslip_history_tree.column(db_schema.COL_PAY_NET_PAY, width=100, anchor="e")
        self.payslip_history_tree.column(db_schema.COL_PAY_GENERATION_DATE, width=150, anchor="center", stretch=tk.YES)

        scrollbar_y = ttk.Scrollbar(history_frame, orient="vertical", command=self.payslip_history_tree.yview)
        self.payslip_history_tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_x = ttk.Scrollbar(history_frame, orient="horizontal", command=self.payslip_history_tree.xview) # Add horizontal scrollbar
        self.payslip_history_tree.configure(xscrollcommand=scrollbar_x.set)

        self.payslip_history_tree.configure(yscrollcommand=scrollbar.set)
        self.payslip_history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # TODO: Add button to view/export selected payslip PDF from history
        self._load_payslip_history_for_employee()

    def _create_salary_advances_widgets(self, tab_frame):
        form_frame = ttk.LabelFrame(tab_frame, text=_("payroll_adv_form_title"), padding="10")
        form_frame.pack(side="top", fill="x", pady=10)
        self._add_translatable_widget_payroll(form_frame, "payroll_adv_form_title")

        # Employee Selection
        emp_lbl_adv = ttk.Label(form_frame, text=_("payroll_employee_label")); emp_lbl_adv.grid(row=0, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(emp_lbl_adv, "payroll_employee_label")
        self.adv_employee_var = tk.StringVar()
        self.adv_employee_combo = ttk.Combobox(form_frame, textvariable=self.adv_employee_var, state="readonly", width=35)
        self.adv_employee_combo.bind("<<ComboboxSelected>>", self._on_adv_employee_select)
        self.adv_employee_combo.grid(row=0, column=1, sticky="ew", pady=5, padx=5) # Grid before populating

        # Advance Date
        adv_date_lbl = ttk.Label(form_frame, text=_("payroll_adv_date_label")); adv_date_lbl.grid(row=1, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(adv_date_lbl, "payroll_adv_date_label")
        self.adv_date_entry = DateEntry(form_frame, width=15, dateformat='%Y-%m-%d')
        self.adv_date_entry.date = dt_date.today()
        self.adv_date_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        # Advance Amount
        adv_amount_lbl = ttk.Label(form_frame, text=_("payroll_adv_amount_label")); adv_amount_lbl.grid(row=2, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(adv_amount_lbl, "payroll_adv_amount_label")
        self.adv_amount_var = tk.StringVar()
        self.adv_amount_entry = ttk.Entry(form_frame, textvariable=self.adv_amount_var, width=15)
        self.adv_amount_entry.grid(row=2, column=1, sticky="w", pady=5, padx=5)

        # Repayment Amount Per Period
        repay_period_lbl = ttk.Label(form_frame, text=_("payroll_adv_repay_per_period_label")); repay_period_lbl.grid(row=3, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(repay_period_lbl, "payroll_adv_repay_per_period_label")
        self.adv_repay_per_period_var = tk.StringVar()
        self.adv_repay_per_period_entry = ttk.Entry(form_frame, textvariable=self.adv_repay_per_period_var, width=15)
        self.adv_repay_per_period_entry.grid(row=3, column=1, sticky="w", pady=5, padx=5)

        # Repayment Start Date
        repay_start_lbl = ttk.Label(form_frame, text=_("payroll_adv_repay_start_date_label")); repay_start_lbl.grid(row=4, column=0, sticky="w", pady=5, padx=5); self._add_translatable_widget_payroll(repay_start_lbl, "payroll_adv_repay_start_date_label")
        self.adv_repay_start_date_entry = DateEntry(form_frame, width=15, dateformat='%Y-%m-%d')
        self.adv_repay_start_date_entry.date = dt_date.today() # Default to today, adjust as needed
        self.adv_repay_start_date_entry.grid(row=4, column=1, sticky="w", pady=5, padx=5)

        # Add Advance Button
        self.add_advance_btn = ttk.Button(form_frame, text=_("payroll_adv_add_button"), command=self._gui_add_salary_advance, bootstyle=db_schema.BS_ADD)
        self.add_advance_btn.grid(row=5, column=1, pady=10, sticky="e")
        self._add_translatable_widget_payroll(self.add_advance_btn, "payroll_adv_add_button")

        form_frame.columnconfigure(1, weight=1)
        # --- Display Area for Existing Advances ---
        adv_display_frame = ttk.LabelFrame(tab_frame, text=_("payroll_adv_existing_advances_label"), padding="10") # Add key
        adv_display_frame.pack(fill="both", expand=True, pady=10)
        self._add_translatable_widget_payroll(adv_display_frame, "payroll_adv_existing_advances_label", attr="title")

        self.adv_tree_cols = (db_schema.COL_ADV_ID, db_schema.COL_ADV_DATE, db_schema.COL_ADV_AMOUNT,
                              db_schema.COL_ADV_REPAY_AMOUNT_PER_PERIOD, db_schema.COL_ADV_TOTAL_REPAID, db_schema.COL_ADV_STATUS)
        self.adv_tree = ttk.Treeview(adv_display_frame, columns=self.adv_tree_cols, show="headings")

        self.adv_tree.heading(db_schema.COL_ADV_ID, text=_("payroll_adv_header_id")) # Add key
        self.adv_tree.heading(db_schema.COL_ADV_DATE, text=_("payroll_adv_header_date")) # Add key
        self.adv_tree.heading(db_schema.COL_ADV_AMOUNT, text=_("payroll_adv_header_amount")) # Add key
        self.adv_tree.heading(db_schema.COL_ADV_REPAY_AMOUNT_PER_PERIOD, text=_("payroll_adv_header_repay_per_period")) # Add key
        self.adv_tree.heading(db_schema.COL_ADV_TOTAL_REPAID, text=_("payroll_adv_header_total_repaid")) # Add key
        self.adv_tree.heading(db_schema.COL_ADV_STATUS, text=_("payroll_adv_header_status")) # Add key

        for col_id in self.adv_tree_cols:
            self.adv_tree.column(col_id, width=100, anchor="center")
        self.adv_tree.column(db_schema.COL_ADV_ID, width=60, anchor="e")
        self.adv_tree.pack(side="left", fill="both", expand=True)
        adv_scrollbar = ttk.Scrollbar(adv_display_frame, orient="vertical", command=self.adv_tree.yview)
        self.adv_tree.configure(yscrollcommand=adv_scrollbar.set)
        adv_scrollbar.pack(side="right", fill="y")

        # Populate dropdown after all widgets in this tab, including adv_tree, are created
        self._populate_adv_employee_dropdown()

    def _populate_adv_employee_dropdown(self):
        try:
            employees = db_queries.get_all_employees_db()
            active_employees = [emp for emp in employees if emp.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE]
            self.adv_employee_combo['values'] = [f"{emp[db_schema.COL_EMP_NAME]} ({emp[db_schema.COL_EMP_ID]})" for emp in active_employees]
            if active_employees:
                self.adv_employee_combo.current(0)
                self._on_adv_employee_select() # Load advances for the default selected employee
            else: # pragma: no cover
                self.adv_employee_combo['values'] = []
                self.adv_employee_var.set("") # Clear selection if no employees

        except Exception as e:
            logger.error(f"Failed to populate Salary Advance employee dropdown: {e}")
            messagebox.showerror("Error", "Could not load employee list for Salary Advances.", parent=self)

    def _populate_rp_employee_dropdown(self):
        try:
            employees = db_queries.get_all_employees_db()
            active_employees = [emp for emp in employees if emp.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE]
            self.rp_employee_combo['values'] = [f"{emp[db_schema.COL_EMP_NAME]} ({emp[db_schema.COL_EMP_ID]})" for emp in active_employees]
            if active_employees:
                self.rp_employee_combo.current(0)
                self._on_rp_employee_select() # Load data for the default selected employee
        except Exception as e:
            logger.error(f"Failed to populate RP employee dropdown: {e}")
            messagebox.showerror("Error", "Could not load employee list for Rewards/Penalties.", parent=self)

    def _populate_payroll_employee_dropdown(self):
        try:
            employees = db_queries.get_all_employees_db() # Assuming this returns active employees or all
            active_employees = [emp for emp in employees if emp.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE]
            if active_employees:
                employee_display_list = [f"{emp[db_schema.COL_EMP_NAME]} ({emp[db_schema.COL_EMP_ID]})" for emp in active_employees]
                self.payroll_employee_combo['values'] = employee_display_list
                if employee_display_list:
                    # self.payroll_employee_combo.current(0) # Already handled by populate_employee_combobox if default_to_first=True
                    # self._on_payroll_employee_select() # TODO: If history tab is added
                    self.payroll_employee_combo.current(0)
            else:
                self.payroll_employee_combo['values'] = []
        except Exception as e:
            logger.error(f"Failed to populate employee dropdown for payroll: {e}")
            messagebox.showerror("Error", "Could not load employee list.", parent=self)

    def _get_employee_id_from_combobox_selection(self, selection_string_var: tk.StringVar) -> Optional[str]:
        """Helper to extract employee ID from 'Name (ID)' string."""
        selected_display = selection_string_var.get()
        if selected_display and "(" in selected_display and ")" in selected_display:
            try:
                return selected_display.split('(')[-1].split(')')[0]
            except IndexError: return None
        return None
    def _get_selected_payroll_employee_id(self) -> Optional[str]:
        return self._get_employee_id_from_combobox_selection(self.payroll_employee_var)

    def _get_selected_adv_employee_id(self) -> Optional[str]:
        return self._get_employee_id_from_combobox_selection(self.adv_employee_var)

    def _get_selected_rp_employee_id(self) -> Optional[str]:
        return self._get_employee_id_from_combobox_selection(self.rp_employee_var)

    def _on_adv_employee_select(self, event=None):
        """Loads existing salary advances for the selected employee."""
        emp_id = self._get_selected_adv_employee_id()
        for item in self.adv_tree.get_children():
            self.adv_tree.delete(item)

        if not emp_id:
            return

        try:
            advances = db_queries.get_salary_advances_for_employee_db(emp_id)
            for adv in advances:
                self.adv_tree.insert("", "end", values=(
                    adv[db_schema.COL_ADV_ID],
                    adv[db_schema.COL_ADV_DATE],
                    f"{adv[db_schema.COL_ADV_AMOUNT]:,.2f}", # Added comma for thousands
                    f"{adv[db_schema.COL_ADV_REPAY_AMOUNT_PER_PERIOD]:.2f}",
                    f"{adv[db_schema.COL_ADV_TOTAL_REPAID]:.2f}",
                    adv[db_schema.COL_ADV_STATUS]
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(_("db_error_title"), str(e), parent=self)

    def _on_rp_employee_select(self, event=None):
        """Loads existing non-recurring rewards and penalties for the selected employee."""
        emp_id = self._get_selected_rp_employee_id()
        for item in self.rp_tree.get_children():
            self.rp_tree.delete(item)

        if not emp_id:
            return

        try:
            rewards = db_queries.get_non_recurring_allowances_for_employee_db(emp_id)
            for reward in rewards:
                # Treeview columns: "item_id", "item_type_col", "description_col", "amount_col", "eff_date_col"
                self.rp_tree.insert("", "end", values=(
                    reward[db_schema.COL_ALLW_ID], _("payroll_rp_reward_radio"), # Use translated "Reward"
                    reward[db_schema.COL_ALLW_TYPE], f"{reward[db_schema.COL_ALLW_AMOUNT]:,.2f}", # Added comma
                    reward[db_schema.COL_ALLW_EFF_DATE]
                ))
            
            penalties = db_queries.get_non_recurring_deductions_for_employee_db(emp_id)
            for penalty in penalties:
                self.rp_tree.insert("", "end", values=(
                    penalty[db_schema.COL_DED_ID], _("payroll_rp_penalty_radio"),
                    penalty[db_schema.COL_DED_TYPE], f"{penalty[db_schema.COL_DED_AMOUNT]:,.2f}", # Added comma
                    penalty[db_schema.COL_DED_EFF_DATE]
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(_("db_error_title"), _("payroll_rp_load_error", error=str(e)), parent=self) # Add key

    def _load_payslip_history_for_employee(self):
        """Loads payslip history for the self.default_emp_id into the history tree."""
        if not self.default_emp_id or not hasattr(self, 'payslip_history_tree') or not self.payslip_history_tree.winfo_exists():
            return

        for item in self.payslip_history_tree.get_children():
            self.payslip_history_tree.delete(item)
        try:
            payslips = db_queries.get_payslips_for_employee_db(self.default_emp_id)
            for payslip in payslips:
                self.payslip_history_tree.insert("", "end", values=(
                    payslip[db_schema.COL_PAY_ID], payslip[db_schema.COL_PAY_PERIOD_START], 
                    payslip[db_schema.COL_PAY_PERIOD_END], f"{payslip[db_schema.COL_PAY_NET_PAY]:,.2f}", 
                    payslip[db_schema.COL_PAY_GENERATION_DATE]
                ))
        except Exception as e: # pragma: no cover
            logger.error(f"Error loading payslip history for employee {self.default_emp_id}: {e}")
            messagebox.showerror(_("error_title"), _("payroll_error_loading_history", error=e), parent=self) # Add key

    def _gui_calculate_payslip(self):
        # Clear previous details
        self._clear_payslip_display()
        self.calculated_payslip_data = None
        self.save_payslip_btn.config(state="disabled")
        self.export_payslip_pdf_btn.config(state="disabled")

        emp_id = self._get_selected_payroll_employee_id()
        start_date_str = self.period_start_entry.entry.get()
        end_date_str = self.period_end_entry.entry.get()

        if not emp_id:
            messagebox.showerror("Input Error", "Please select an employee.", parent=self)
            return
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format. Use YYYY-MM-DD.", parent=self)
            self.payslip_display_text.config(state="disabled"); return

        try:
            self.calculated_payslip_data = db_queries.calculate_payroll_for_employee(emp_id, start_date_str, end_date_str)
            
            self._display_calculated_payslip(self.calculated_payslip_data)
            self.save_payslip_btn.config(state="normal")
            self.export_payslip_pdf_btn.config(state="normal")

        except (EmployeeNotFoundError, InvalidInputError, DatabaseOperationError) as e:
            messagebox.showerror("Calculation Error", str(e), parent=self)
        except Exception as e:
            logger.error(f"Unexpected error calculating payslip: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)
        
    def _clear_payslip_display(self):
        """Clears the structured payslip display area."""
        for var in self.payslip_detail_vars.values():
            var.set("N/A" if "date" in var._name or "period" in var._name else "0.00") # type: ignore
        
        # Clear dynamic items in earnings and deductions frames
        for frame in [self.earnings_details_frame, self.deductions_details_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
        
        # Add default items back (like Basic Salary)
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_basic_salary"), 0.00)
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_overtime_pay"), 0.00)
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_total_allowances"), 0.00, is_bold=True)

        self._add_detail_item(self.deductions_details_frame, _("payslip_item_total_other_deductions"), 0.00)
        self._add_detail_item(self.deductions_details_frame, _("payslip_item_advance_repayment"), 0.00)

        self.payslip_notes_text_display.config(state="normal")
        self.payslip_notes_text_display.delete("1.0", tk.END)
        self.payslip_notes_text_display.config(state="disabled")

    def _display_calculated_payslip(self, data: Dict):
        """Populates the structured payslip display with calculated data."""
        self._clear_payslip_display() # Clear previous before populating

        self.payslip_detail_vars["employee_name_period"].set(f"Employee: {self.payroll_employee_var.get()} | Period: {data[db_schema.COL_PAY_PERIOD_START]} to {data[db_schema.COL_PAY_PERIOD_END]}")
        self.payslip_detail_vars["generation_date"].set(f"Generated: {data[db_schema.COL_PAY_GENERATION_DATE]}")

        # Earnings
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_monthly_ref_salary"), data.get('monthly_reference_salary', 0.0))
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_basic_salary_period"), data[db_schema.COL_PAY_BASIC_SALARY])
        if data.get('overtime_pay', 0) > 0:
            self._add_detail_item(self.earnings_details_frame, _("payslip_item_overtime_pay_hours", hours=data.get('overtime_hours', 0.0)), data['overtime_pay'])
        for item_list_key in ["recurring_allowances_detail", "non_recurring_allowances_detail"]:
            for item in data.get(item_list_key, []):
                desc = f"{item[db_schema.COL_ALLW_TYPE]} ({_('payslip_item_recurring')})" if item_list_key == "recurring_allowances_detail" else f"{item[db_schema.COL_ALLW_TYPE]} ({_('payslip_item_bonus_other')})"
                self._add_detail_item(self.earnings_details_frame, desc, item[db_schema.COL_ALLW_AMOUNT])
        self._add_detail_item(self.earnings_details_frame, _("payslip_item_total_allowances"), data[db_schema.COL_PAY_TOTAL_ALLOWANCES], is_bold=True)

        # Deductions
        for item_list_key in ["recurring_deductions_detail", "non_recurring_deductions_detail"]:
            for item in data.get(item_list_key, []):
                desc = f"{item[db_schema.COL_DED_TYPE]} ({_('payslip_item_recurring')})" if item_list_key == "recurring_deductions_detail" else f"{item[db_schema.COL_DED_TYPE]} ({_('payslip_item_penalty_other')})"
                self._add_detail_item(self.deductions_details_frame, desc, item[db_schema.COL_DED_AMOUNT])
        if data[db_schema.COL_PAY_ADVANCE_REPAYMENT] > 0:
            self._add_detail_item(self.deductions_details_frame, _("payslip_item_advance_repayment"), data[db_schema.COL_PAY_ADVANCE_REPAYMENT])

        # Summary
        self.payslip_detail_vars["gross_salary"].set(f"{data[db_schema.COL_PAY_GROSS_SALARY]:,.2f}")
        total_deductions_combined = data[db_schema.COL_PAY_TOTAL_DEDUCTIONS] + data[db_schema.COL_PAY_ADVANCE_REPAYMENT]
        self.payslip_detail_vars["total_deductions_combined"].set(f"{total_deductions_combined:,.2f}")
        self.payslip_detail_vars["net_pay"].set(f"{data[db_schema.COL_PAY_NET_PAY]:,.2f}")
        self.payslip_detail_vars["attendance_info"].set(f"Workdays: {data.get('expected_workdays_in_period', 'N/A')}, Present: {data.get('actual_days_worked_in_period', 'N/A')}")

        if data.get(db_schema.COL_PAY_NOTES):
            self.payslip_notes_text_display.config(state="normal")
            self.payslip_notes_text_display.insert("1.0", data[db_schema.COL_PAY_NOTES])
            self.payslip_notes_text_display.config(state="disabled")

    def _gui_save_payslip(self):
        if not self.calculated_payslip_data:
            messagebox.showerror("Save Error", "No payslip data calculated to save.", parent=self)
            return
        
        try:
            # Add notes if needed, e.g., from a new Text widget for notes
            self.calculated_payslip_data[db_schema.COL_PAY_NOTES] = self.payslip_notes_text_display.get("1.0", tk.END).strip() # Get notes from display if editable
            payslip_id = db_queries.record_payslip_db(self.calculated_payslip_data)
            messagebox.showinfo(_("success_title"), _("payroll_payslip_saved_success", payslip_id=payslip_id), parent=self) # Use translation key
            # Keep export PDF enabled, but disable save to prevent duplicate DB entries
            self.save_payslip_btn.config(state="disabled") # Disable after saving
            self.calculated_payslip_data = None # Clear cached data
        except (DatabaseOperationError, InvalidInputError) as e:
            messagebox.showerror("Save Error", str(e), parent=self)
        except Exception as e:
            logger.error(f"Unexpected error saving payslip: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred during save: {e}", parent=self)

    def _gui_export_payslip_pdf(self):
        if not self.calculated_payslip_data: # pragma: no cover
            # This case might not be hit if button state is managed well
            messagebox.showerror("Export Error", "No payslip data calculated to export.", parent=self)
            return
        
        emp_id = self.calculated_payslip_data[db_schema.COL_PAY_EMP_ID]
        period_start = self.calculated_payslip_data[db_schema.COL_PAY_PERIOD_START]
        default_filename = f"Payslip_{emp_id}_{period_start}.pdf"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save Payslip as PDF",
            initialfile=default_filename,
            parent=self
        )
        if not filepath:
            return # User cancelled
        try:
            pdf_utils.generate_payslip_pdf(self.calculated_payslip_data, filepath)
            messagebox.showinfo(_("export_success_title"), _("payroll_pdf_export_success", path=filepath), parent=self) # Use translation key
        except Exception as e:
            messagebox.showerror(_("export_error_title"), _("payroll_pdf_export_error", error=e), parent=self) # Use translation key

    def _gui_add_reward_penalty(self):
        emp_id = self._get_selected_rp_employee_id()
        item_type = self.rp_type_var.get() # "Reward" or "Penalty"
        description = self.rp_description_entry.get().strip()
        amount_str = self.rp_amount_var.get()
        eff_date_str = self.rp_eff_date_entry.entry.get()

        if not emp_id:
            messagebox.showerror("Input Error", "Please select an employee.", parent=self)
            return
        if not description:
            messagebox.showerror("Input Error", "Description is required.", parent=self)
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showerror("Input Error", "Amount must be a positive number.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid amount format.", parent=self)
            return
        try:
            datetime.strptime(eff_date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Input Error", "Invalid effective date. Use YYYY-MM-DD.", parent=self)
            return

        try:
            if item_type == "Reward":
                db_queries.add_employee_reward_db(emp_id, description, amount, eff_date_str)
                messagebox.showinfo(_("success_title"), _("payroll_reward_added_success", description=description), parent=self) # Use translation key
            elif item_type == "Penalty":
                db_queries.add_employee_penalty_db(emp_id, description, amount, eff_date_str)
                messagebox.showinfo(_("success_title"), _("payroll_penalty_added_success", description=description), parent=self) # Use translation key
            # Clear fields after adding
            self.rp_description_entry.delete(0, tk.END)
            self.rp_amount_var.set("")
        except (EmployeeNotFoundError, InvalidInputError, DatabaseOperationError) as e:
            messagebox.showerror(_("error_title"), str(e), parent=self) # Use translation key

    def _gui_add_salary_advance(self):
        emp_id = self._get_selected_adv_employee_id()
        adv_date_str = self.adv_date_entry.entry.get()
        adv_amount_str = self.adv_amount_var.get()
        repay_per_period_str = self.adv_repay_per_period_var.get()
        repay_start_date_str = self.adv_repay_start_date_entry.entry.get()

        if not emp_id:
            messagebox.showerror("Input Error", "Please select an employee.", parent=self)
            return
        
        try:
            adv_amount = float(adv_amount_str)
            repay_per_period = float(repay_per_period_str)
            if adv_amount <= 0 or repay_per_period <= 0:
                messagebox.showerror("Input Error", "Amounts must be positive.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Input Error", "Invalid amount format.", parent=self)
            return

        try:
            datetime.strptime(adv_date_str, '%Y-%m-%d')
            datetime.strptime(repay_start_date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Input Error", "Invalid date format. Use YYYY-MM-DD.", parent=self)
            return

        try:
            db_queries.add_salary_advance_db(emp_id, adv_date_str, adv_amount, repay_per_period, repay_start_date_str)
            messagebox.showinfo(_("success_title"), _("payroll_advance_added_success", amount=f"{adv_amount:.2f}"), parent=self) # Use translation key
            # Clear fields
            self.adv_amount_var.set("")
            self.adv_repay_per_period_var.set("")
            # Optionally reset dates or keep them for next entry
            # self.adv_date_var.set(dt_date.today().isoformat())
            # self.adv_repay_start_date_var.set(dt_date.today().isoformat())

        except (EmployeeNotFoundError, InvalidInputError, DatabaseOperationError) as e:
            messagebox.showerror("Error Adding Advance", str(e), parent=self)
        except Exception as e:
            logger.error(f"Unexpected error adding salary advance: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)
            
    def _gui_export_for_accounting(self):
        """Handles the UI for exporting payroll data for accounting software."""
        # For now, we'll directly implement Excel export.
        # Later, this could open a dialog to choose format (Excel, IIF, etc.) and date range.

        # Simple date range selection for now (can be enhanced with DateEntry dialog)
        # Let's assume we export for the currently selected period in the generate tab, if available
        # Or prompt for a new period. For simplicity, let's prompt.

        period_start_str = simpledialog.askstring(localization._("payroll_export_dialog_title"), 
                                                  localization._("payroll_period_start_label"), parent=self)
        if not period_start_str: return

        period_end_str = simpledialog.askstring(localization._("payroll_export_dialog_title"),
                                                localization._("payroll_period_end_label"), parent=self)
        if not period_end_str: return

        try:
            # Validate dates (basic validation)
            datetime.strptime(period_start_str, "%Y-%m-%d")
            datetime.strptime(period_end_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(localization._("input_error_title"), localization._("invalid_date_format_error"), parent=self) # Add key "invalid_date_format_error"
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[(localization._("payroll_export_format_excel"), "*.xlsx"), (localization._("all_files_type_label"), "*.*")],
            title=localization._("payroll_export_dialog_title"),
            parent=self
        )
        if not filepath:
            return

        try:
            with self.app_controller.BusyContextManager(self):
                # Fetch data - This function needs to be created in db_queries.py
                # It should gather all payslip data for the given period,
                # including employee details, earnings, deductions, net pay etc.
                # For now, let's assume it returns a list of dicts.
                payroll_data_for_export = db_queries.get_payroll_data_for_accounting_export(period_start_str, period_end_str)

                if not payroll_data_for_export:
                    messagebox.showinfo(localization._("info_title"), localization._("dashboard_no_data_for_charts"), parent=self) # Re-use key or add specific one
                    return

                success = export_utils.export_payroll_to_excel(payroll_data_for_export, filepath)
            
            if success:
                messagebox.showinfo(localization._("success_title"), localization._("payroll_export_success_message", filepath=filepath), parent=self)
            else:
                messagebox.showerror(localization._("error_title"), localization._("payroll_export_failed_message", error="Excel generation failed."), parent=self)
        except Exception as e:
            logger.error(f"Error during accounting export: {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("payroll_export_failed_message", error=str(e)), parent=self)