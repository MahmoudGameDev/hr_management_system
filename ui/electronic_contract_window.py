# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\electronic_contract_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from ttkbootstrap.tooltip import ToolTip
import os
import logging
from datetime import datetime, date as dt_date, timedelta
from typing import Optional, Dict

from PIL import Image, ImageTk, ImageDraw, ImageGrab # For signature canvas and grabbing
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning("PyMuPDF (fitz) not installed. PDF signing features will be limited.")

import config # For DOCUMENTS_BASE_DIR
from data import database as db_schema
from data import queries as db_queries
from utils import localization
from utils.file_utils import secure_delete_file # If used for temp signature files
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global
from utils.pdf_utils import generate_contract_pdf, embed_image_in_pdf
from utils.gui_utils import extract_id_from_combobox_selection, populate_user_combobox # Added populate_user_combobox

from .themed_toplevel import ThemedToplevel

# --- Project-specific imports ---
from .components import AutocompleteCombobox # For manager selection

logger = logging.getLogger(__name__)

class ElectronicContractWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, employee_id: str, contract_id: Optional[int] = None, mode: str = 'new', callback_on_save=None):
        super().__init__(parent, app_instance)
        self.employee_id = employee_id
        self.contract_id_to_edit = contract_id
        self.mode = mode # 'new' or 'edit'
        self.callback_on_save = callback_on_save

        self.employee_details = db_queries.get_employee_by_id_db(self.employee_id) # Corrected function name
        window_title_key = "econtract_window_title_edit" if self.mode == 'edit' else "econtract_window_title_new"
        self.title(localization._(window_title_key, emp_name=self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id)))
        
        self.translatable_widgets_econtract = []
        self.geometry("800x900")

        main_paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        details_pane = ttk.Frame(main_paned_window, padding="10")
        main_paned_window.add(details_pane, weight=1)
        self._create_contract_details_widgets(details_pane)

        signatures_pane = ttk.Frame(main_paned_window, padding="10")
        main_paned_window.add(signatures_pane, weight=1)
        self._create_signature_widgets(signatures_pane)

        actions_pane = ttk.Frame(main_paned_window, padding="10")
        main_paned_window.add(actions_pane, weight=0)
        self._create_action_buttons(actions_pane)

        self.generated_pdf_path: Optional[str] = None
        self.employee_signature_image_path: Optional[str] = None
        self.manager_signature_image_path: Optional[str] = None

        self._populate_employee_data()
        self._toggle_renewal_term_active()

        if self.mode == 'edit' and self.contract_id_to_edit:
            self._load_contract_for_edit()

    def _add_translatable_widget_econtract(self, widget, key, attr="text"):
        self.translatable_widgets_econtract.append({"widget": widget, "key": key, "attr": attr})
        
    def _create_contract_details_widgets(self, parent_frame):
        details_lf = ttk.LabelFrame(parent_frame, text=localization._("econtract_details_section_title"), padding="10")
        details_lf.pack(fill="both", expand=True)
        self._add_translatable_widget_econtract(details_lf, "econtract_details_section_title", attr="title")
        details_lf.columnconfigure(1, weight=1)

        self.contract_vars = {}
        row_idx = 0

        # Employee Info (Read-only)
        emp_info_lbl_static = ttk.Label(details_lf, text=localization._("nav_employees_btn_text")); emp_info_lbl_static.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(emp_info_lbl_static, "nav_employees_btn_text")
        self.employee_info_label = ttk.Label(details_lf, text="")
        self.employee_info_label.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Contract Type
        contract_type_lbl = ttk.Label(details_lf, text=localization._("econtract_type_label")); contract_type_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(contract_type_lbl, "econtract_type_label")
        self.contract_vars["contract_type"] = tk.StringVar()
        self.contract_type_combo = ttk.Combobox(details_lf, textvariable=self.contract_vars["contract_type"], values=db_schema.VALID_CONTRACT_TYPES, state="readonly", width=30)
        self.contract_type_combo.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Position
        pos_lbl = ttk.Label(details_lf, text=localization._("position_icon_label")); pos_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(pos_lbl, "position_icon_label")
        self.contract_vars["position"] = tk.StringVar()
        ttk.Entry(details_lf, textvariable=self.contract_vars["position"], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Salary
        salary_lbl = ttk.Label(details_lf, text=localization._("salary_icon_label")); salary_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(salary_lbl, "salary_icon_label")
        self.contract_vars["salary"] = tk.StringVar()
        ttk.Entry(details_lf, textvariable=self.contract_vars["salary"], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Start Date
        start_date_lbl = ttk.Label(details_lf, text=localization._("start_date_icon_label")); start_date_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(start_date_lbl, "start_date_icon_label")
        self.start_date_entry = DateEntry(details_lf, width=12, dateformat='%Y-%m-%d')
        self.start_date_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # End Date
        end_date_lbl = ttk.Label(details_lf, text=localization._("econtract_end_date_label")); end_date_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(end_date_lbl, "econtract_end_date_label")
        self.end_date_entry = DateEntry(details_lf, width=12, dateformat='%Y-%m-%d')
        self.end_date_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        self.end_date_entry.entry.delete(0, tk.END)
        row_idx += 1

        # Initial Duration (Years)
        duration_lbl = ttk.Label(details_lf, text=localization._("econtract_initial_duration_label")); duration_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(duration_lbl, "econtract_initial_duration_label")
        self.contract_vars["initial_duration_years"] = tk.StringVar(value="1")
        ttk.Spinbox(details_lf, from_=0, to=20, textvariable=self.contract_vars["initial_duration_years"], width=5).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Is Auto-Renewable
        auto_renew_lbl = ttk.Label(details_lf, text=localization._("econtract_auto_renewable_label")); auto_renew_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(auto_renew_lbl, "econtract_auto_renewable_label")
        self.contract_vars["is_auto_renewable"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(details_lf, variable=self.contract_vars["is_auto_renewable"], command=self._toggle_renewal_term_active).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Renewal Term (Years)
        renewal_term_lbl = ttk.Label(details_lf, text=localization._("econtract_renewal_term_label")); renewal_term_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(renewal_term_lbl, "econtract_renewal_term_label")
        self.contract_vars["renewal_term_years"] = tk.StringVar(value="1")
        self.renewal_term_spinbox = ttk.Spinbox(details_lf, from_=0, to=10, textvariable=self.contract_vars["renewal_term_years"], width=5, state="disabled")
        self.renewal_term_spinbox.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Notice Period (Days)
        notice_period_lbl = ttk.Label(details_lf, text=localization._("econtract_notice_period_label")); notice_period_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_econtract(notice_period_lbl, "econtract_notice_period_label")
        self.contract_vars["notice_period_days"] = tk.StringVar(value="30")
        ttk.Spinbox(details_lf, from_=0, to=180, increment=15, textvariable=self.contract_vars["notice_period_days"], width=5).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Custom Conditions
        custom_cond_lbl = ttk.Label(details_lf, text=localization._("econtract_custom_conditions_label")); custom_cond_lbl.grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget_econtract(custom_cond_lbl, "econtract_custom_conditions_label")
        self.contract_custom_terms_text = tk.Text(details_lf, height=6, width=40, relief="solid", borderwidth=1)
        self.contract_custom_terms_text.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.contract_custom_terms_text, palette)

    def _create_signature_widgets(self, parent_frame):
        signatures_lf = ttk.LabelFrame(parent_frame, text=localization._("econtract_signatures_section_title"), padding="10")
        signatures_lf.pack(fill="both", expand=True)
        self._add_translatable_widget_econtract(signatures_lf, "econtract_signatures_section_title", attr="title")
        signatures_lf.columnconfigure(0, weight=1)
        signatures_lf.columnconfigure(1, weight=1)

        # --- Employee Signature ---
        emp_sig_frame = ttk.LabelFrame(signatures_lf, text=localization._("econtract_emp_sig_label"), padding="10")
        emp_sig_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._add_translatable_widget_econtract(emp_sig_frame, "econtract_emp_sig_label", attr="title")
        emp_sig_frame.columnconfigure(0, weight=1)

        self.emp_sig_canvas = tk.Canvas(emp_sig_frame, bg="white", height=150, relief="solid", borderwidth=1)
        self.emp_sig_canvas.pack(fill="both", expand=True)
        self.emp_sig_canvas.bind("<Button-1>", self._start_draw)
        self.emp_sig_canvas.bind("<B1-Motion>", self._draw)
        
        emp_sig_clear_btn = ttk.Button(emp_sig_frame, text=localization._("econtract_clear_sig_btn"), command=lambda: self._clear_canvas(self.emp_sig_canvas), bootstyle=db_schema.BS_LIGHT)
        emp_sig_clear_btn.pack(pady=5)
        self._add_translatable_widget_econtract(emp_sig_clear_btn, "econtract_clear_sig_btn")
        
        emp_sig_upload_btn = ttk.Button(emp_sig_frame, text=localization._("econtract_upload_sig_btn"), command=lambda: self._upload_signature(is_employee=True), bootstyle=db_schema.BS_NEUTRAL)
        emp_sig_upload_btn.pack(pady=5)
        self._add_translatable_widget_econtract(emp_sig_upload_btn, "econtract_upload_sig_btn")

        # --- Management Signature ---
        manager_sig_frame = ttk.LabelFrame(signatures_lf, text=localization._("econtract_manager_sig_label"), padding="10")
        manager_sig_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._add_translatable_widget_econtract(manager_sig_frame, "econtract_manager_sig_label", attr="title")
        manager_sig_frame.columnconfigure(0, weight=1)

        manager_signer_lbl = ttk.Label(manager_sig_frame, text=localization._("econtract_signed_by_user_label"))
        manager_signer_lbl.pack(pady=(0,5))
        self._add_translatable_widget_econtract(manager_signer_lbl, "econtract_signed_by_user_label")
        
        self.manager_signer_var = tk.StringVar()
        self.manager_signer_combo = AutocompleteCombobox(manager_sig_frame, textvariable=self.manager_signer_var, width=30)
        self._populate_user_combobox(self.manager_signer_combo)
        self.manager_signer_combo.pack(pady=5)

        self.manager_sig_canvas = tk.Canvas(manager_sig_frame, bg="white", height=150, relief="solid", borderwidth=1)
        self.manager_sig_canvas.pack(fill="both", expand=True)
        self.manager_sig_canvas.bind("<Button-1>", self._start_draw)
        self.manager_sig_canvas.bind("<B1-Motion>", self._draw)
        
        manager_sig_clear_btn = ttk.Button(manager_sig_frame, text=localization._("econtract_clear_sig_btn"), command=lambda: self._clear_canvas(self.manager_sig_canvas), bootstyle=db_schema.BS_LIGHT)
        manager_sig_clear_btn.pack(pady=5)
        self._add_translatable_widget_econtract(manager_sig_clear_btn, "econtract_clear_sig_btn") # Reusing key

        manager_sig_upload_btn = ttk.Button(manager_sig_frame, text=localization._("econtract_upload_sig_btn"), command=lambda: self._upload_signature(is_employee=False), bootstyle=db_schema.BS_NEUTRAL)
        manager_sig_upload_btn.pack(pady=5)
        self._add_translatable_widget_econtract(manager_sig_upload_btn, "econtract_upload_sig_btn") # Reusing key

        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        canvas_bg = palette.get('bg_main', 'white')
        self.emp_sig_canvas.config(bg=canvas_bg)
        self.manager_sig_canvas.config(bg=canvas_bg)
        self.last_x, self.last_y = None, None

    def _create_action_buttons(self, parent_frame):
        actions_lf = ttk.LabelFrame(parent_frame, text=localization._("econtract_actions_section_title"), padding="10")
        actions_lf.pack(fill="x")
        self._add_translatable_widget_econtract(actions_lf, "econtract_actions_section_title", attr="title")

        self.create_pdf_btn = ttk.Button(actions_lf, text=localization._("econtract_create_pdf_btn"), command=self._gui_create_contract_pdf, bootstyle=db_schema.BS_ADD)
        self.create_pdf_btn.pack(side="left", padx=5)
        self._add_translatable_widget_econtract(self.create_pdf_btn, "econtract_create_pdf_btn")

        self.sign_employee_btn = ttk.Button(actions_lf, text=localization._("econtract_sign_emp_btn"), command=self._gui_sign_employee, state="disabled", bootstyle="success")
        self.sign_employee_btn.pack(side="left", padx=5)
        self._add_translatable_widget_econtract(self.sign_employee_btn, "econtract_sign_emp_btn")

        self.sign_manager_btn = ttk.Button(actions_lf, text=localization._("econtract_sign_manager_btn"), command=self._gui_sign_manager, state="disabled", bootstyle="success")
        self.sign_manager_btn.pack(side="left", padx=5)
        self._add_translatable_widget_econtract(self.sign_manager_btn, "econtract_sign_manager_btn")

        self.save_signed_contract_btn = ttk.Button(actions_lf, text=localization._("econtract_save_signed_btn"), command=self._gui_save_signed_contract, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.save_signed_contract_btn.pack(side="left", padx=5)
        self._add_translatable_widget_econtract(self.save_signed_contract_btn, "econtract_save_signed_btn")

    def _populate_employee_data(self):
        emp = self.employee_details
        emp_info = f"{emp.get(db_schema.COL_EMP_NAME, 'N/A')} (ID: {emp.get(db_schema.COL_EMP_ID, 'N/A')})"
        self.employee_info_label.config(text=emp_info)

        self.contract_vars["position"].set(emp.get(db_schema.COL_EMP_POSITION, ""))
        self.contract_vars["salary"].set(f"{emp.get(db_schema.COL_EMP_SALARY, 0.0):.2f}")
        if emp.get(db_schema.COL_EMP_START_DATE):
            try:
                self.start_date_entry.date = dt_date.fromisoformat(emp[db_schema.COL_EMP_START_DATE])
            except ValueError:
                logger.warning(f"Invalid start date format for employee {self.employee_id}: {emp[db_schema.COL_EMP_START_DATE]}")
                self.start_date_entry.date = dt_date.today() # Fallback
        else:
            self.start_date_entry.date = dt_date.today() # Default if no start date

    def _populate_user_combobox(self, combo_widget): # pragma: no cover
        populate_user_combobox(combo_widget, db_queries.get_all_users_db, empty_option_text="") # Use the utility function

    def _toggle_renewal_term_active(self):
        if hasattr(self, 'renewal_term_spinbox'):
            if self.contract_vars["is_auto_renewable"].get():
                self.renewal_term_spinbox.config(state="normal")
            else:
                self.renewal_term_spinbox.config(state="disabled")
                self.contract_vars["renewal_term_years"].set("0")

    def _calculate_end_date(self, *args):
        try:
            start_date_str = self.start_date_entry.entry.get()
            duration_years_str = self.contract_vars["initial_duration_years"].get()
            if start_date_str and duration_years_str.isdigit():
                start_date = dt_date.fromisoformat(start_date_str)
                duration_years = int(duration_years_str)
                if duration_years > 0:
                    end_date = start_date.replace(year=start_date.year + duration_years)
                    self.end_date_entry.entry.delete(0, tk.END)
                    self.end_date_entry.entry.insert(0, end_date.isoformat())
        except ValueError:
            pass # Invalid date or duration

    def _start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _draw(self, event):
        if self.last_x and self.last_y:
            canvas = event.widget
            canvas.create_line(self.last_x, self.last_y, event.x, event.y,
                               width=2, fill="black", capstyle=tk.ROUND, smooth=tk.TRUE)
            self.last_x, self.last_y = event.x, event.y

    def _clear_canvas(self, canvas):
        canvas.delete("all")
        self.last_x, self.last_y = None, None
        if canvas == self.emp_sig_canvas:
            self.employee_signature_image_path = None
        elif canvas == self.manager_sig_canvas:
            self.manager_signature_image_path = None

    def _get_canvas_image_data(self, canvas) -> Optional[bytes]:
        try:
            self.update_idletasks()
            x = self.winfo_rootx() + canvas.winfo_x()
            y = self.winfo_rooty() + canvas.winfo_y()
            x1 = x + canvas.winfo_width()
            y1 = y + canvas.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, x1, y1))
            from io import BytesIO
            byte_arr = BytesIO()
            img.save(byte_arr, format='PNG')
            return byte_arr.getvalue()
        except ImportError: # pragma: no cover
            messagebox.showerror(localization._("error_title"), localization._("pillow_not_found_error"), parent=self)
            return None
        except Exception as e: # pragma: no cover
            logger.error(f"Error capturing canvas image: {e}")
            messagebox.showerror(localization._("error_title"), localization._("failed_to_capture_signature_error", error=e), parent=self)
            return None

    def _upload_signature(self, is_employee: bool):
        filepath = filedialog.askopenfilename(
            title=localization._("econtract_select_signature_image_title"),
            filetypes=[(localization._("image_files_filter_text"), "*.png *.jpg *.jpeg"), (localization._("all_files_filter_text"), "*.*")],
            parent=self
        )
        if not filepath: return

        try:
            img = Image.open(filepath)
            canvas_widget = self.emp_sig_canvas if is_employee else self.manager_sig_canvas
            img.thumbnail((canvas_widget.winfo_width(), canvas_widget.winfo_height()), Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(img)

            self._clear_canvas(canvas_widget)
            canvas_widget.create_image(0, 0, image=photo_img, anchor="nw")
            canvas_widget.image = photo_img # Keep reference

            if is_employee:
                self.employee_signature_image_path = filepath
            else:
                self.manager_signature_image_path = filepath
        except Exception as e: # pragma: no cover
            logger.error(f"Error loading uploaded signature image: {e}")
            messagebox.showerror(localization._("error_title"), localization._("could_not_load_image_error", error=e), parent=self)

    def _gui_create_contract_pdf(self):
        contract_data = {
            "contract_type": self.contract_vars["contract_type"].get().strip(),
            "position": self.contract_vars["position"].get().strip(),
            "salary": self.contract_vars["salary"].get().strip(),
            "start_date": self.start_date_entry.entry.get().strip(),
            "current_end_date": self.end_date_entry.entry.get().strip() or None,
            "initial_duration_years": self.contract_vars["initial_duration_years"].get().strip(),
            "is_auto_renewable": self.contract_vars["is_auto_renewable"].get(),
            "renewal_term_years": self.contract_vars["renewal_term_years"].get().strip(),
            "notice_period_days": self.contract_vars["notice_period_days"].get().strip(),
            "custom_terms": self.contract_custom_terms_text.get("1.0", tk.END).strip() or None
        }

        if not all([contract_data["contract_type"], contract_data["position"], contract_data["salary"], contract_data["start_date"]]):
            messagebox.showerror(localization._("input_error_title"), localization._("econtract_missing_fields_error"), parent=self)
            return
        try:
            float(contract_data["salary"])
            dt_date.fromisoformat(contract_data["start_date"])
            if contract_data["current_end_date"]: dt_date.fromisoformat(contract_data["current_end_date"])
            if not contract_data["initial_duration_years"].isdigit() or int(contract_data["initial_duration_years"]) < 0: raise ValueError()
            if contract_data["is_auto_renewable"] and (not contract_data["renewal_term_years"].isdigit() or int(contract_data["renewal_term_years"]) <= 0): raise ValueError()
            if not contract_data["notice_period_days"].isdigit() or int(contract_data["notice_period_days"]) < 0: raise ValueError()
        except ValueError:
            messagebox.showerror(localization._("input_error_title"), localization._("econtract_invalid_format_error"), parent=self)
            return

        emp_doc_dir = os.path.join(config.DOCUMENTS_BASE_DIR, self.employee_id)
        os.makedirs(emp_doc_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"{self.employee_id}_Contract_{timestamp}.pdf"
        self.generated_pdf_path = os.path.join(emp_doc_dir, suggested_filename)

        try:
            generate_contract_pdf(self.employee_details, contract_data, self.generated_pdf_path)
            if not os.path.exists(self.generated_pdf_path): # pragma: no cover
                logger.error(f"PDF file not found at '{self.generated_pdf_path}' post-generation.")
                raise FileNotFoundError("PDF file not found post-generation.")
            messagebox.showinfo(localization._("success_title"), localization._("contract_pdf_generated_success_message", filepath=self.generated_pdf_path), parent=self)
            self.sign_employee_btn.config(state="normal")
            self.sign_manager_btn.config(state="normal")
            self.save_signed_contract_btn.config(state="normal")
        except Exception as e: # pragma: no cover
            logger.error(f"Error generating contract PDF: {e}", exc_info=True)
            messagebox.showerror(localization._("generation_error_title"), localization._("failed_to_generate_contract_pdf_error", error=e), parent=self)
            self.generated_pdf_path = None
            self.sign_employee_btn.config(state="disabled"); self.sign_manager_btn.config(state="disabled"); self.save_signed_contract_btn.config(state="disabled")

    def _gui_sign_employee(self):
        if not self.generated_pdf_path or not os.path.exists(self.generated_pdf_path):
            messagebox.showwarning(localization._("signing_error_title"), localization._("create_contract_pdf_first_warning"), parent=self)
            return
        sig_image_data = self._get_canvas_image_data(self.emp_sig_canvas)
        if sig_image_data is None and not self.employee_signature_image_path:
            messagebox.showwarning(localization._("signing_error_title"), localization._("draw_or_upload_employee_signature_warning"), parent=self)
            return
        try:
            if sig_image_data:
                self.employee_signature_image_path = db_queries.save_signature_image_to_file(sig_image_data, self.employee_id, signer_type="employee")
            if not self.employee_signature_image_path or not os.path.exists(self.employee_signature_image_path): # pragma: no cover
                raise FileNotFoundError("Employee signature image file not found after saving/upload.")
            doc_info = fitz.open(self.generated_pdf_path); last_page_index = len(doc_info) - 1; doc_info.close()
            embed_image_in_pdf(self.generated_pdf_path, self.employee_signature_image_path, last_page_index, sig_width=150, sig_height=75, position="bottom-right", margin=50)
            messagebox.showinfo(localization._("success_title"), localization._("employee_signature_added_pdf_success_message"), parent=self)
        except Exception as e: # pragma: no cover
            logger.error(f"Error signing contract (employee): {e}", exc_info=True)
            messagebox.showerror(localization._("signing_error_title"), localization._("failed_to_add_employee_signature_error", error=e), parent=self)

    def _gui_sign_manager(self):
        if not self.generated_pdf_path or not os.path.exists(self.generated_pdf_path):
            messagebox.showwarning(localization._("signing_error_title"), localization._("create_contract_pdf_first_warning"), parent=self)
            return
        manager_selection = self.manager_signer_var.get()
        manager_user_id = extract_id_from_combobox_selection(manager_selection)
        if not manager_user_id:
            messagebox.showwarning(localization._("signing_error_title"), localization._("select_signing_manager_warning"), parent=self)
            return
        sig_image_data = self._get_canvas_image_data(self.manager_sig_canvas)
        if sig_image_data is None and not self.manager_signature_image_path:
            messagebox.showwarning(localization._("signing_error_title"), localization._("draw_or_upload_manager_signature_warning"), parent=self)
            return
        try:
            if sig_image_data:
                self.manager_signature_image_path = db_queries.save_signature_image_to_file(sig_image_data, self.employee_id, signer_type="manager")
            if not self.manager_signature_image_path or not os.path.exists(self.manager_signature_image_path): # pragma: no cover
                raise FileNotFoundError("Manager signature image file not found after saving/upload.")
            doc_info = fitz.open(self.generated_pdf_path); last_page_index = len(doc_info) - 1; doc_info.close()
            embed_image_in_pdf(self.generated_pdf_path, self.manager_signature_image_path, last_page_index, sig_width=150, sig_height=75, position="bottom-left", margin=50)
            messagebox.showinfo(localization._("success_title"), localization._("manager_signature_added_pdf_success_message"), parent=self)
        except Exception as e: # pragma: no cover
            logger.error(f"Error signing contract (manager): {e}", exc_info=True)
            messagebox.showerror(localization._("signing_error_title"), localization._("failed_to_add_manager_signature_error", error=e), parent=self)

    def _gui_save_signed_contract(self):
        if not self.generated_pdf_path or not os.path.exists(self.generated_pdf_path):
            messagebox.showwarning(localization._("save_error_title"), localization._("no_signed_contract_to_save_warning"), parent=self)
            return

        contract_details_for_db = {
            db_schema.COL_CONTRACT_EMP_ID: self.employee_id,
            db_schema.COL_CONTRACT_TYPE: self.contract_vars["contract_type"].get().strip(),
            db_schema.COL_CONTRACT_START_DATE: self.start_date_entry.entry.get().strip(),
            db_schema.COL_CONTRACT_INITIAL_DURATION_YEARS: int(self.contract_vars["initial_duration_years"].get()) if self.contract_vars["initial_duration_years"].get().isdigit() else None,
            db_schema.COL_CONTRACT_CURRENT_END_DATE: self.end_date_entry.entry.get().strip() or None,
            db_schema.COL_CONTRACT_IS_AUTO_RENEWABLE: 1 if self.contract_vars["is_auto_renewable"].get() else 0,
            db_schema.COL_CONTRACT_RENEWAL_TERM_YEARS: int(self.contract_vars["renewal_term_years"].get()) if self.contract_vars["is_auto_renewable"].get() and self.contract_vars["renewal_term_years"].get().isdigit() else None,
            db_schema.COL_CONTRACT_NOTICE_PERIOD_DAYS: int(self.contract_vars["notice_period_days"].get()) if self.contract_vars["notice_period_days"].get().isdigit() else 30,
            db_schema.COL_CONTRACT_CUSTOM_TERMS: self.contract_custom_terms_text.get("1.0", tk.END).strip() or None
        }

        try:
            doc_id = db_queries.add_employee_document_db(self.employee_id, contract_details_for_db[db_schema.COL_CONTRACT_TYPE], self.generated_pdf_path)
            contract_details_for_db[db_schema.COL_CONTRACT_DOC_ID] = doc_id

            db_queries.add_contract_record_db(contract_details_for_db)

            if self.employee_signature_image_path and os.path.exists(self.employee_signature_image_path):
                db_queries.record_contract_signing_db(doc_id, signer_emp_id=self.employee_id, signer_user_id=None, signature_image_path=self.employee_signature_image_path, signing_notes="Signed by Employee")
            manager_selection = self.manager_signer_var.get()
            manager_user_id = extract_id_from_combobox_selection(manager_selection)
            if self.manager_signature_image_path and os.path.exists(self.manager_signature_image_path) and manager_user_id:
                db_queries.record_contract_signing_db(doc_id, signer_emp_id=None, signer_user_id=int(manager_user_id), signature_image_path=self.manager_signature_image_path, signing_notes="Signed by Management")

            db_schema.increment_app_counter(db_schema.COUNTER_CONTRACTS_SIGNED_ELECTRONICALLY)
            messagebox.showinfo(localization._("success_title"), localization._("signed_contract_saved_success_message", doc_id=doc_id), parent=self)
            self.save_signed_contract_btn.config(state="disabled")
            if self.callback_on_save: self.callback_on_save() # Refresh main GUI if callback provided
            self.destroy() # Close window on successful save
        except Exception as e: # pragma: no cover
            logger.error(f"Error saving signed contract: {e}", exc_info=True)
            messagebox.showerror(localization._("save_error_title"), localization._("failed_to_save_signed_contract_error", error=e), parent=self)

    def _load_contract_for_edit(self):
        if not self.contract_id_to_edit: return
        try:
            contract = db_queries.get_contract_details_by_id_db(self.contract_id_to_edit)
            if not contract:
                messagebox.showerror(localization._("error_title"), localization._("contract_not_found_error", contract_id=self.contract_id_to_edit), parent=self)
                self.destroy(); return

            self.contract_vars["contract_type"].set(contract.get(db_schema.COL_CONTRACT_TYPE, ""))
            self.contract_vars["position"].set(contract.get(db_schema.COL_CONTRACT_POSITION, self.employee_details.get(db_schema.COL_EMP_POSITION, ""))) # Position might be in contract or employee
            self.contract_vars["salary"].set(str(contract.get(db_schema.COL_CONTRACT_SALARY, self.employee_details.get(db_schema.COL_EMP_SALARY, "")))) # Salary might be in contract or employee
            
            if contract.get(db_schema.COL_CONTRACT_START_DATE): self.start_date_entry.date = dt_date.fromisoformat(contract[db_schema.COL_CONTRACT_START_DATE])
            if contract.get(db_schema.COL_CONTRACT_CURRENT_END_DATE): self.end_date_entry.date = dt_date.fromisoformat(contract[db_schema.COL_CONTRACT_CURRENT_END_DATE])
            
            self.contract_vars["initial_duration_years"].set(str(contract.get(db_schema.COL_CONTRACT_INITIAL_DURATION_YEARS, "1")))
            self.contract_vars["is_auto_renewable"].set(bool(contract.get(db_schema.COL_CONTRACT_IS_AUTO_RENEWABLE, False)))
            self.contract_vars["renewal_term_years"].set(str(contract.get(db_schema.COL_CONTRACT_RENEWAL_TERM_YEARS, "1")))
            self.contract_vars["notice_period_days"].set(str(contract.get(db_schema.COL_CONTRACT_NOTICE_PERIOD_DAYS, "30")))
            
            self.contract_custom_terms_text.delete("1.0", tk.END)
            self.contract_custom_terms_text.insert("1.0", contract.get(db_schema.COL_CONTRACT_CUSTOM_TERMS, ""))
            
            self._toggle_renewal_term_active()

            # If contract has a document_id, set generated_pdf_path and enable signing buttons
            doc_id = contract.get(db_schema.COL_CONTRACT_DOC_ID)
            if doc_id:
                doc_details = db_queries.get_document_details_by_id_db(doc_id) # New backend function needed
                if doc_details and os.path.exists(doc_details[db_schema.COL_DOC_FILE_PATH]):
                    self.generated_pdf_path = doc_details[db_schema.COL_DOC_FILE_PATH]
                    self.sign_employee_btn.config(state="normal")
                    self.sign_manager_btn.config(state="normal")
                    self.save_signed_contract_btn.config(state="normal") # Or "Update Contract"
                    # TODO: Load existing signatures onto canvases if paths are stored in contract_signatures

            # Disable fields if contract is not in 'Draft' or 'Pending Approval'
            if contract.get(db_schema.COL_CONTRACT_APPROVAL_STATUS) not in ['Draft', 'Pending Approval']:
                for child in self.winfo_children(): # Iterate through all children of the Toplevel
                    if isinstance(child, ttk.Frame): # Assuming details_lf and signatures_lf are direct children or in a main frame
                        for widget in child.winfo_children(): # Iterate through widgets in LabelFrames
                            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Text, ttk.Checkbutton, DateEntry)):
                                try: widget.config(state="disabled")
                                except tk.TclError: pass
                self.create_pdf_btn.config(state="disabled")
                self.sign_employee_btn.config(state="disabled")
                self.sign_manager_btn.config(state="disabled")
                # Save button might become "View PDF" or be disabled
                self.save_signed_contract_btn.config(text=localization._("econtract_view_pdf_btn"), command=self._view_existing_pdf) # Change to view

        except Exception as e: # pragma: no cover
            logger.error(f"Error loading contract for edit (ID: {self.contract_id_to_edit}): {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("econtract_error_loading_for_edit", error=e), parent=self)

    def _view_existing_pdf(self):
        if self.generated_pdf_path and os.path.exists(self.generated_pdf_path):
            try:
                if os.name == 'nt': os.startfile(self.generated_pdf_path)
                elif os.name == 'posix': subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', self.generated_pdf_path))
            except Exception as e: # pragma: no cover
                messagebox.showerror(localization._("error_title"), localization._("could_not_open_pdf_error", error=e), parent=self)
        else:
            messagebox.showwarning(localization._("info_title"), localization._("no_pdf_associated_with_contract_warning"), parent=self)

    def refresh_ui_for_language(self): # pragma: no cover
        window_title_key = "econtract_window_title_edit" if self.mode == 'edit' else "econtract_window_title_new"
        self.title(localization._(window_title_key, emp_name=self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id)))
        for item in self.translatable_widgets_econtract:
            widget = item["widget"]
            key = item["key"]
            attr = item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title":
                         widget.config(text=localization._(key))
                except tk.TclError: pass

# Note: The actual implementation of the placeholder methods above (_create_signature_widgets, etc.)
# will be taken from the `ElectronicContractWindow` class in `hr_management_system.py`
# and adapted for this new file structure.