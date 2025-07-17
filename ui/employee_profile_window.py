# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\employee_profile_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk
import os
import sys
import subprocess
import logging
from datetime import datetime
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning("PyMuPDF (fitz) not installed. PDF signing features in EmployeeProfileWindow will be limited.")

try:
    from pdfminer.high_level import extract_text
    from pdfminer.pdfparser import PDFSyntaxError
except ImportError:
    extract_text = None # Define as None if import fails
    PDFSyntaxError = None # Define as None if import fails
    logging.warning("pdfminer.six not installed. PDF parsing for CVs will be limited.")

# --- Project-specific imports ---
import config
from data import database as db_schema
from data import queries as db_queries
from utils import localization
from utils import attendance_utils # For Instant Status Assessment
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global
from .themed_toplevel import ThemedToplevel
from .electronic_contract_window import ElectronicContractWindow
from .assign_skill_dialog import AssignSkillDialog # New Import
from utils import image_utils # For QR code generation

logger = logging.getLogger(__name__)

class EmployeeProfileWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, employee_id: str):
        super().__init__(parent, app_instance)
        self.employee_id = employee_id
        self.preview_label: Optional[ttk.Label] = None
        self._profile_photo_ref: Optional[ImageTk.PhotoImage] = None
        self.employee_details = db_queries.get_employee_by_id_db(self.employee_id) # Already correct here, but good to verify
        self.title_key = "profile_window_title" # Store the key for refresh_ui_for_language
        self.today_attendance_status = attendance_utils.get_employee_attendance_status_today(self.employee_id)
        self.translatable_widgets_profile: list = []

        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id)
        self.title(localization._("profile_window_title", name=emp_name_display))
        self.geometry("700x800")

        self.profile_notebook = ttk.Notebook(self)
        self.profile_notebook.pack(expand=True, fill="both", padx=10, pady=10)

        details_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(details_tab, text=localization._("profile_tab_details"))
        self._add_translatable_tab(0, "profile_tab_details")
        self._create_details_display(details_tab)

        documents_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(documents_tab, text=localization._("profile_tab_documents"))
        self._add_translatable_tab(1, "profile_tab_documents")
        self._create_documents_section(documents_tab)

        action_log_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(action_log_tab, text=localization._("profile_tab_action_log"))
        self._add_translatable_tab(2, "profile_tab_action_log")
        self._create_action_log_section(action_log_tab)

        electronic_contract_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(electronic_contract_tab, text=localization._("profile_tab_econtract"))
        self._add_translatable_tab(3, "profile_tab_econtract")
        self._create_electronic_contract_section(electronic_contract_tab)

        # CV Analysis specific variables - MOVED UP
        self.cv_filepath_var = tk.StringVar(value=localization._("profile_cv_no_file_selected"))
        self.cv_extracted_text_var = tk.StringVar()
        
        resume_analysis_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(resume_analysis_tab, text=localization._("profile_tab_cv_analysis"))
        self._add_translatable_tab(4, "profile_tab_cv_analysis")
        self._create_resume_analysis_section(resume_analysis_tab)
        skills_training_tab = ttk.Frame(self.profile_notebook, padding="10")
        self.profile_notebook.add(skills_training_tab, text=localization._("profile_tab_skills_training"))
        self._add_translatable_tab(5, "profile_tab_skills_training") # New tab index
        self._create_skills_training_section(skills_training_tab)

        # CV Analysis specific variables
        self.cv_filepath_var = tk.StringVar(value=localization._("profile_cv_no_file_selected"))
        self.cv_extracted_text_var = tk.StringVar() # This was duplicated, ensure it's defined once
        
    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_profile.append({"widget": widget, "key": key, "attr": attr})

    def _add_translatable_tab(self, tab_index, key):
        self.translatable_widgets_profile.append({"widget": self.profile_notebook, "key": key, "attr": "tab", "index": tab_index})

    def _create_details_display(self, parent_tab):
        emp = self.employee_details
        details_scroll_frame = ttk.Frame(parent_tab)
        details_scroll_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(details_scroll_frame)
        scrollbar = ttk.Scrollbar(details_scroll_frame, orient="vertical", command=canvas.yview)
        details_content_frame = ttk.Frame(canvas, padding="10")

        details_content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=details_content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Today's Attendance Status Section ---
        # Placed before other details for prominence
        status_lf_key = "profile_today_status_label"
        status_frame = ttk.LabelFrame(details_content_frame, text=localization._(status_lf_key), padding="10")
        status_frame.pack(fill="x", pady=(5,10), padx=5)
        self._add_translatable_widget(status_frame, status_lf_key, attr="title")

        self.today_status_var = tk.StringVar(value=self.today_attendance_status.get("status_message", localization._("status_not_available")))
        today_status_display_label = ttk.Label(status_frame, textvariable=self.today_status_var, font=("Helvetica", 10, "bold"))
        today_status_display_label.pack(anchor="w", padx=5, pady=2)
        # --- Show QR Code Button ---
        qr_btn_key = "profile_show_qr_code_btn"
        show_qr_button = ttk.Button(status_frame, text=localization._(qr_btn_key), command=self._gui_show_qr_code_profile, bootstyle="info-outline")
        show_qr_button.pack(side="right", padx=5, pady=2)
        self._add_translatable_widget(show_qr_button, qr_btn_key)
        # This label's text is dynamic via the var, so it doesn't need to be added to translatable_widgets_profile
        # for its text content, but the LabelFrame title is.
        # --- End Today's Attendance Status Section ---

        sections_config = {
            "profile_section_personal_info": [
                (localization._("employee_id_label"), emp.get(db_schema.COL_EMP_ID, 'N/A')),
                (localization._("name_label"), emp.get(db_schema.COL_EMP_NAME, 'N/A')),
                (localization._("gender_icon_label"), emp.get(db_schema.COL_EMP_GENDER, 'N/A')),
                (localization._("marital_status_icon_label"), emp.get(db_schema.COL_EMP_MARITAL_STATUS, 'N/A')),
            ],
            "profile_section_contact_info": [
                (localization._("phone_icon_label"), emp.get(db_schema.COL_EMP_PHONE, 'N/A')),
                (localization._("email_icon_label"), emp.get(db_schema.COL_EMP_EMAIL, 'N/A')),
            ],
            "profile_section_employment_details": [
                (localization._("department_icon_label"), emp.get("department_name", 'Unassigned')),
                (localization._("position_icon_label"), emp.get(db_schema.COL_EMP_POSITION, 'N/A')),
                (localization._("salary_icon_label"), f"${emp.get(db_schema.COL_EMP_SALARY, 0.0):.2f}"),
                (localization._("status_icon_label"), emp.get(db_schema.COL_EMP_STATUS, 'N/A')),
                (localization._("start_date_icon_label"), emp.get(db_schema.COL_EMP_START_DATE, 'N/A')),
                (localization._("termination_date_icon_label"), emp.get(db_schema.COL_EMP_TERMINATION_DATE, 'N/A') or 'N/A'),
            ],
            "profile_section_system_benefits": [
                (localization._("vacation_days_icon_label"), str(emp.get(db_schema.COL_EMP_VACATION_DAYS, 0))),
                (localization._("exclude_vacation_policy_icon_label"), "Yes" if emp.get(db_schema.COL_EMP_EXCLUDE_VACATION_POLICY, 0) == 1 else "No"),
                (localization._("device_user_id_icon_label"), emp.get(db_schema.COL_EMP_DEVICE_USER_ID, 'N/A')),
            ],
            "profile_section_qualifications": [
                 (localization._("education_icon_label"), emp.get(db_schema.COL_EMP_EDUCATION, 'N/A')),
            ]
        }

        photo_section_frame = ttk.LabelFrame(details_content_frame, text=localization._("profile_section_photo"), padding="10")
        photo_section_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(photo_section_frame, "profile_section_photo", attr="title")
        self.preview_label = ttk.Label(photo_section_frame, anchor="center")
        self.preview_label.pack(pady=5, expand=True)

        photo_path = emp.get(db_schema.COL_EMP_PHOTO_PATH)
        if photo_path and os.path.exists(photo_path):
            try:
                original_img = Image.open(photo_path)
                img_for_profile = original_img.copy()
                img_for_profile.thumbnail((200, 200), Image.Resampling.LANCZOS)
                self._profile_photo_ref = ImageTk.PhotoImage(img_for_profile)
                self.preview_label.config(image=self._profile_photo_ref, text="")
            except Exception as e_img:
                self.preview_label.config(image="", text=localization._("profile_no_photo_text"))
                logger.warning(f"Could not load photo for profile {self.employee_id}: {e_img}")
        else:
            self.preview_label.config(image="", text=localization._("profile_no_photo_text"))
        self._add_translatable_widget(self.preview_label, "profile_no_photo_text")

        for section_title_key, fields in sections_config.items():
            section_frame = ttk.LabelFrame(details_content_frame, text=localization._(section_title_key), padding="10")
            section_frame.pack(fill="x", pady=5, padx=5)
            section_frame.columnconfigure(1, weight=1)
            self._add_translatable_widget(section_frame, section_title_key, attr="title")

            for row_idx, (label_text, value_text) in enumerate(fields):
                lbl_widget = ttk.Label(section_frame, text=label_text, anchor="w")
                lbl_widget.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
                val_entry = ttk.Entry(section_frame, width=40)
                val_entry.insert(0, str(value_text))
                val_entry.config(state="readonly")
                val_entry.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)

        history_section_frame = ttk.LabelFrame(details_content_frame, text=localization._("profile_section_emp_history"), padding="10")
        history_section_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(history_section_frame, "profile_section_emp_history", attr="title")
        history_text = tk.Text(history_section_frame, height=5, width=38, wrap="word", relief="solid", borderwidth=1) # Ensure themed

        # Robust insertion for employment history
        history_text_content = emp.get(db_schema.COL_EMP_EMPLOYMENT_HISTORY, 'N/A')
        history_text_content = str(history_text_content if history_text_content is not None else "N/A")
        if '\0' in history_text_content:
            logger.warning("Employment history (profile window) contains null bytes. Replacing with [NULL] for display.")
            history_text_content = history_text_content.replace('\0', '[NULL]') # Or replace with empty string
        history_text.insert("1.0", history_text_content)

        history_text.config(state="disabled")
        history_text.pack(fill="x", expand=True, pady=5)
        palette = get_theme_palette_global(self.parent_app.get_current_theme()) # Use parent_app to get theme
        _theme_text_widget_global(history_text, palette)

        details_content_frame.update_idletasks()

    def _create_documents_section(self, parent_tab):
        # This reuses the logic from HRAppGUI._create_documents_section
        doc_main_frame = ttk.LabelFrame(parent_tab, text=localization._("profile_doc_section_title"), padding="10")
        doc_main_frame.pack(fill="both", expand=True)
        self._add_translatable_widget(doc_main_frame, "profile_doc_section_title", attr="title")

        doc_actions_frame = ttk.Frame(doc_main_frame)
        doc_actions_frame.pack(side="top", fill="x", pady=5)

        # Add Document Button
        add_doc_btn_key = "profile_doc_add_btn"
        self.add_doc_btn_profile = ttk.Button(doc_actions_frame, text=localization._(add_doc_btn_key), command=self._gui_add_document, bootstyle=db_schema.BS_ADD)
        self.add_doc_btn_profile.pack(side="left", padx=5)
        self._add_translatable_widget(self.add_doc_btn_profile, add_doc_btn_key)

        # View Document Button
        view_doc_btn_key = "profile_doc_view_btn"
        self.view_doc_btn_profile = ttk.Button(doc_actions_frame, text=localization._(view_doc_btn_key), command=self._gui_view_document, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.view_doc_btn_profile.pack(side="left", padx=5)
        self._add_translatable_widget(self.view_doc_btn_profile, view_doc_btn_key)

        # Delete Document Button
        delete_doc_btn_key = "profile_doc_delete_btn"
        self.delete_doc_btn_profile = ttk.Button(doc_actions_frame, text=localization._(delete_doc_btn_key), command=self._gui_delete_document, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_doc_btn_profile.pack(side="left", padx=5)
        self._add_translatable_widget(self.delete_doc_btn_profile, delete_doc_btn_key)

        # Sign Document Button
        sign_doc_btn_key = "profile_doc_sign_btn"
        self.sign_doc_btn_profile = ttk.Button(doc_actions_frame, text=localization._(sign_doc_btn_key), command=self._gui_sign_document, state="disabled", bootstyle="success")
        if not fitz:
            self.sign_doc_btn_profile.config(state="disabled")
            ToolTip(self.sign_doc_btn_profile, text=localization._("pdf_signing_lib_not_installed_error")) # Add key
        self.sign_doc_btn_profile.pack(side="left", padx=5)
        self._add_translatable_widget(self.sign_doc_btn_profile, sign_doc_btn_key)

        # Create New Contract Button (already handled by electronic_contract_tab, but can be here too for direct access)
        # create_contract_btn_key = "profile_doc_create_contract_btn"
        # self.create_contract_btn_profile = ttk.Button(doc_actions_frame, text=localization._(create_contract_btn_key), command=self._gui_manage_econtract, bootstyle=db_schema.BS_ADD)
        # self.create_contract_btn_profile.pack(side="left", padx=5)
        # self._add_translatable_widget(self.create_contract_btn_profile, create_contract_btn_key)

        # Treeview for documents
        doc_list_frame = ttk.Frame(doc_main_frame)
        doc_list_frame.pack(fill="both", expand=True, pady=5)

        self.doc_tree_cols_profile = (db_schema.COL_DOC_ID, db_schema.COL_DOC_TYPE, "filename", db_schema.COL_DOC_UPLOAD_DATE)
        self.doc_tree_profile = ttk.Treeview(doc_list_frame, columns=self.doc_tree_cols_profile, show="headings")
        self._update_doc_tree_headers() # Call to set headers for this tree

        self.doc_tree_profile.column(db_schema.COL_DOC_ID, width=60, anchor="e", stretch=tk.NO)
        self.doc_tree_profile.column(db_schema.COL_DOC_TYPE, width=150)
        self.doc_tree_profile.column("filename", width=350, stretch=tk.YES)
        self.doc_tree_profile.column(db_schema.COL_DOC_UPLOAD_DATE, width=120, anchor="center")

        doc_scrollbar = ttk.Scrollbar(doc_list_frame, orient="vertical", command=self.doc_tree_profile.yview)
        self.doc_tree_profile.configure(yscrollcommand=doc_scrollbar.set)
        self.doc_tree_profile.pack(side="left", fill="both", expand=True)
        doc_scrollbar.pack(side="right", fill="y")

        self.doc_tree_profile.bind("<<TreeviewSelect>>", self._on_document_tree_select)
        self._load_documents_to_tree() # Load documents for the current employee

    def _create_action_log_section(self, parent_tab):
        # Similar to _create_documents_section, adapt from main_gui.py
        log_main_frame = ttk.LabelFrame(parent_tab, text=localization._("profile_action_log_section_title"), padding="10")
        log_main_frame.pack(fill="both", expand=True)
        self._add_translatable_widget(log_main_frame, "profile_action_log_section_title", attr="title")

        self.action_log_tree_cols_profile = ("timestamp", "action", "performed_by")
        self.action_log_tree_profile = ttk.Treeview(log_main_frame, columns=self.action_log_tree_cols_profile, show="headings")
        self._update_action_log_tree_headers() # Call to set headers for this tree

        self.action_log_tree_profile.column("timestamp", width=150, anchor="w")
        self.action_log_tree_profile.column("action", width=350, stretch=tk.YES, anchor="w")
        self.action_log_tree_profile.column("performed_by", width=150, anchor="w")

        log_scrollbar = ttk.Scrollbar(log_main_frame, orient="vertical", command=self.action_log_tree_profile.yview)
        self.action_log_tree_profile.configure(yscrollcommand=log_scrollbar.set)
        self.action_log_tree_profile.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        self._load_action_log_to_tree() # Load action log for the current employee

    def _create_electronic_contract_section(self, parent_tab):
        lbl = ttk.Label(parent_tab, text=localization._("profile_econtract_section_title"), font=("Helvetica", 16))
        lbl.pack(pady=20)
        self._add_translatable_widget(lbl, "profile_econtract_section_title")
        btn = ttk.Button(parent_tab, text=localization._("profile_econtract_manage_btn"), command=self._gui_manage_econtract)
        btn.pack()
        self._add_translatable_widget(btn, "profile_econtract_manage_btn")

    def _create_resume_analysis_section(self, parent_tab):
        # --- CV Upload Section ---
        upload_lf_key = "profile_cv_upload_section_title"
        upload_frame = ttk.LabelFrame(parent_tab, text=localization._(upload_lf_key), padding="10")
        upload_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(upload_frame, upload_lf_key, attr="title")
        upload_frame.columnconfigure(1, weight=1)

        select_file_btn_key = "profile_cv_select_file_button"
        self.select_cv_btn = ttk.Button(upload_frame, text=localization._(select_file_btn_key), command=self._gui_browse_cv)
        self.select_cv_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self._add_translatable_widget(self.select_cv_btn, select_file_btn_key)

        self.selected_cv_file_label = ttk.Label(upload_frame, textvariable=self.cv_filepath_var, wraplength=300)
        self.selected_cv_file_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # No need to add selected_cv_file_label to translatable_widgets as its text is dynamic

        parse_btn_key = "profile_cv_parse_btn"
        self.parse_cv_btn = ttk.Button(upload_frame, text=localization._(parse_btn_key), command=self._gui_parse_cv, state="disabled")
        self.parse_cv_btn.grid(row=1, column=0, columnspan=2, pady=5)
        self._add_translatable_widget(self.parse_cv_btn, parse_btn_key)

        # --- Extracted Data Section ---
        extracted_lf_key = "profile_cv_extracted_data_section_title"
        extracted_frame = ttk.LabelFrame(parent_tab, text=localization._(extracted_lf_key), padding="10")
        extracted_frame.pack(fill="both", expand=True, pady=5, padx=5)
        self._add_translatable_widget(extracted_frame, extracted_lf_key, attr="title")

        self.cv_extracted_text_widget = tk.Text(extracted_frame, height=10, wrap="word", relief="solid", borderwidth=1, state="disabled")
        self.cv_extracted_text_widget.pack(fill="both", expand=True, pady=5)
        # Theming for Text widget will be handled by update_local_theme_elements

        # --- Suitability Assessment Section ---
        suitability_lf_key = "profile_cv_suitability_section_title"
        suitability_frame = ttk.LabelFrame(parent_tab, text=localization._(suitability_lf_key), padding="10")
        suitability_frame.pack(fill="x", pady=5, padx=5)
        self._add_translatable_widget(suitability_frame, suitability_lf_key, attr="title")
        suitability_frame.columnconfigure(0, weight=1) # Make job_desc_text expand

        job_desc_lbl_key = "profile_cv_job_desc_label"
        job_desc_label = ttk.Label(suitability_frame, text=localization._(job_desc_lbl_key))
        job_desc_label.pack(anchor="w")
        self._add_translatable_widget(job_desc_label, job_desc_lbl_key)

        self.job_desc_text = tk.Text(suitability_frame, height=5, wrap="word", relief="solid", borderwidth=1)
        self.job_desc_text.pack(fill="x", expand=True, pady=(0,5))
        self.job_desc_text.insert("1.0", localization._("profile_cv_job_desc_placeholder"))
        # Theming for Text widget will be handled by update_local_theme_elements

        assess_btn_key = "profile_cv_assess_btn"
        self.assess_suitability_btn = ttk.Button(suitability_frame, text=localization._(assess_btn_key), command=self._gui_assess_suitability, state="disabled")
        self.assess_suitability_btn.pack(pady=5)
        self._add_translatable_widget(self.assess_suitability_btn, assess_btn_key)

        self.suitability_results_text = tk.Text(suitability_frame, height=4, wrap="word", relief="solid", borderwidth=1, state="disabled")
        self.suitability_results_text.pack(fill="x", expand=True, pady=5)
        self.suitability_results_text.insert("1.0", localization._("profile_cv_suitability_results_placeholder"))
        # Theming for Text widget will be handled by update_local_theme_elements

    def _gui_browse_cv(self):
        filepath = filedialog.askopenfilename(
            title=localization._("profile_cv_select_file_button"), # Reusing button text
            filetypes=[("Text files", "*.txt"), ("PDF files", "*.pdf"), ("Word documents", "*.docx"), ("All files", "*.*")],
            parent=self
        )
        if filepath:
            self.cv_filepath_var.set(f"{localization._('profile_cv_selected_file_label_prefix')} {os.path.basename(filepath)}")
            self._raw_cv_filepath = filepath # Store full path internally
            self.parse_cv_btn.config(state="normal")
            self.assess_suitability_btn.config(state="disabled") # Disable assess until parsed
            self.cv_extracted_text_widget.config(state="normal"); self.cv_extracted_text_widget.delete("1.0", tk.END); self.cv_extracted_text_widget.config(state="disabled")
            self.suitability_results_text.config(state="normal"); self.suitability_results_text.delete("1.0", tk.END); self.suitability_results_text.insert("1.0", localization._("profile_cv_suitability_results_placeholder")); self.suitability_results_text.config(state="disabled")
        else:
            self.cv_filepath_var.set(localization._("profile_cv_no_file_selected"))
            self._raw_cv_filepath = None
            self.parse_cv_btn.config(state="disabled")

    def _gui_parse_cv(self):
        if not hasattr(self, '_raw_cv_filepath') or not self._raw_cv_filepath:
            messagebox.showwarning(localization._("warning_title"), localization._("profile_cv_no_file_selected"), parent=self)
            return

        self.cv_extracted_text_widget.config(state="normal")
        self.cv_extracted_text_widget.delete("1.0", tk.END)
        try:
            # Simplified parsing: just read .txt files for now
            file_path_lower = self._raw_cv_filepath.lower()
            content = ""
            if file_path_lower.endswith(".txt"):
                with open(self._raw_cv_filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_path_lower.endswith(".pdf"):
                try:
                    content = extract_text(self._raw_cv_filepath)
                except PDFSyntaxError:
                    logger.error(f"Invalid PDF file: {self._raw_cv_filepath}", exc_info=True)
                    content = localization._("profile_cv_parse_error", error="Invalid or corrupted PDF file.")
            else:
                content = localization._("profile_cv_parse_error", error="Unsupported file type. Only .txt and .pdf are currently supported.")
            
            if content:
                self.cv_extracted_text_widget.insert("1.0", content)
                self.assess_suitability_btn.config(state="normal")
            else:
                # This case might be hit if PDF parsing returns empty string for a valid but empty PDF
                self.cv_extracted_text_widget.insert("1.0", localization._("profile_cv_parse_error", error="Could not extract text or file is empty."))
                self.assess_suitability_btn.config(state="disabled")
        except Exception as e:
            logger.error(f"Error parsing CV file {self._raw_cv_filepath}: {e}", exc_info=True)
            self.cv_extracted_text_widget.insert("1.0", localization._("profile_cv_parse_error", error=str(e)))
            self.assess_suitability_btn.config(state="disabled")
        finally:
            self.cv_extracted_text_widget.config(state="disabled")

    def _gui_assess_suitability(self):
        cv_text = self.cv_extracted_text_widget.get("1.0", tk.END).strip().lower()
        job_desc_text = self.job_desc_text.get("1.0", tk.END).strip().lower()

        if not cv_text:
            messagebox.showwarning(localization._("warning_title"), "CV text is empty. Please parse a CV first.", parent=self)
            return
        if not job_desc_text or job_desc_text == localization._("profile_cv_job_desc_placeholder").lower():
            messagebox.showwarning(localization._("warning_title"), "Please enter a job description or keywords for assessment.", parent=self)
            return

        # Simplified keyword matching
        keywords = [kw.strip() for kw in job_desc_text.split(',') if kw.strip()] # If comma-separated keywords
        if not keywords: # Assume it's a full job description, split into words
            keywords = job_desc_text.split()
        
        match_count = 0
        matched_keywords = set()
        for keyword in keywords:
            if keyword in cv_text:
                match_count += cv_text.count(keyword) # Count occurrences
                matched_keywords.add(keyword)
        
        score = (len(matched_keywords) / len(keywords)) * 100 if keywords else 0
        
        result_text = f"Suitability Score: {score:.2f}%\n"
        result_text += f"Matched Keywords ({len(matched_keywords)}/{len(keywords)}): {', '.join(matched_keywords) if matched_keywords else 'None'}\n"
        result_text += f"Total keyword occurrences in CV: {match_count}"

        self.suitability_results_text.config(state="normal")
        self.suitability_results_text.delete("1.0", tk.END)
        self.suitability_results_text.insert("1.0", result_text)
        self.suitability_results_text.config(state="disabled")

    def _create_skills_training_section(self, parent_tab):
        # --- Assigned Skills Section ---
        skills_lf_key = "profile_skills_assigned_title"
        skills_frame = ttk.LabelFrame(parent_tab, text=localization._(skills_lf_key), padding="10")
        skills_frame.pack(fill="both", expand=True, pady=5, padx=5)
        self._add_translatable_widget(skills_frame, skills_lf_key, attr="title")

        # Action buttons for skills
        skill_actions_frame = ttk.Frame(skills_frame)
        skill_actions_frame.pack(fill="x", pady=5)

        add_skill_btn_key = "profile_skills_add_btn"
        self.add_skill_to_emp_btn = ttk.Button(skill_actions_frame, text=localization._(add_skill_btn_key), command=self._gui_add_skill_to_employee, bootstyle=db_schema.BS_ADD)
        self.add_skill_to_emp_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.add_skill_to_emp_btn, add_skill_btn_key)

        edit_skill_btn_key = "profile_skills_edit_btn"
        self.edit_emp_skill_btn = ttk.Button(skill_actions_frame, text=localization._(edit_skill_btn_key), command=self._gui_edit_employee_skill, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.edit_emp_skill_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.edit_emp_skill_btn, edit_skill_btn_key)

        remove_skill_btn_key = "profile_skills_remove_btn"
        self.remove_emp_skill_btn = ttk.Button(skill_actions_frame, text=localization._(remove_skill_btn_key), command=self._gui_remove_skill_from_employee, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.remove_emp_skill_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.remove_emp_skill_btn, remove_skill_btn_key)

        # Treeview for assigned skills
        self.emp_skills_tree_cols = ("skill_name", "skill_category", "proficiency_level", "acquisition_date")
        self.emp_skills_tree = ttk.Treeview(skills_frame, columns=self.emp_skills_tree_cols, show="headings")
        self._update_emp_skills_tree_headers()

        self.emp_skills_tree.column("skill_name", width=200, stretch=tk.YES)
        self.emp_skills_tree.column("skill_category", width=150)
        self.emp_skills_tree.column("proficiency_level", width=120)
        self.emp_skills_tree.column("acquisition_date", width=100, anchor="center")

        emp_skills_scrollbar = ttk.Scrollbar(skills_frame, orient="vertical", command=self.emp_skills_tree.yview)
        self.emp_skills_tree.configure(yscrollcommand=emp_skills_scrollbar.set)
        self.emp_skills_tree.pack(side="left", fill="both", expand=True)
        emp_skills_scrollbar.pack(side="right", fill="y")

        self.emp_skills_tree.bind("<<TreeviewSelect>>", self._on_employee_skill_select)
        self._load_employee_skills_to_tree()

        # TODO: Add section for Training History below skills
        
    def _gui_manage_econtract(self):
        # Open ElectronicContractWindow for the current employee
        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            employee_id=self.employee_id,
            tracker_attr_name=f"active_econtract_window_{self.employee_id}" # Unique tracker
        )

    def _gui_add_skill_to_employee(self):
        messagebox.showinfo("Add Skill", "Functionality to add skill to employee to be implemented.", parent=self)
        # This will open a dialog to select from global skills and set proficiency/date.

    def _gui_edit_employee_skill(self):
        messagebox.showinfo("Edit Skill", "Functionality to edit employee skill to be implemented.", parent=self)

    def _gui_remove_skill_from_employee(self):
        messagebox.showinfo("Remove Skill", "Functionality to remove skill from employee to be implemented.", parent=self)

    def refresh_ui_for_language(self): # pragma: no cover
        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id)
        self.title(localization._(self.title_key, name=emp_name_display))

        tab_keys = ["profile_tab_details", "profile_tab_documents", "profile_tab_action_log", "profile_tab_econtract", "profile_tab_cv_analysis"]
        for i, key in enumerate(tab_keys + ["profile_tab_skills_training"]): # Add new tab key
            if self.profile_notebook.winfo_exists():
                 try: self.profile_notebook.tab(i, text=localization._(key))
                 except tk.TclError: pass # Tab might not exist if error during creation

        for item in self.translatable_widgets_profile:
            widget = item["widget"]
            key = item["key"]
            attr = item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title": # For LabelFrames
                        widget.config(text=localization._(key))
                except tk.TclError:
                    pass # Widget might not support text/title or was destroyed

        # Refresh dynamic parts if needed (e.g., photo placeholder text)
        if self.preview_label and self.preview_label.cget("image") == "":
            self.preview_label.config(text=localization._("profile_no_photo_text"))

        # Refresh today's status label (though it's a StringVar, its initial value might need re-translation if set directly)
        if hasattr(self, 'today_status_var'):
            # Re-fetch or re-format the status message if its components are translatable
            self.today_attendance_status = attendance_utils.get_employee_attendance_status_today(self.employee_id) # Re-fetch
            self.today_status_var.set(self.today_attendance_status.get("status_message", localization._("status_not_available")))
        # If document tree or action log tree headers are translatable, update them
        self._update_doc_tree_headers() 
        self._update_action_log_tree_headers()
        self._update_emp_skills_tree_headers() # Refresh skills tree headers

        # Update CV Analysis tab elements
        if hasattr(self, 'cv_filepath_var') and self.cv_filepath_var.get().startswith(localization._('profile_cv_selected_file_label_prefix', prev_lang=True)) or self.cv_filepath_var.get() == localization._('profile_cv_no_file_selected', prev_lang=True):
             # If a file was selected, re-prefix. If not, set "No file selected".
            current_filename = self.cv_filepath_var.get().replace(localization._('profile_cv_selected_file_label_prefix', prev_lang=True), "").strip()
            self.cv_filepath_var.set(localization._('profile_cv_selected_file_label_prefix') + " " + current_filename if current_filename and current_filename != localization._('profile_cv_no_file_selected', prev_lang=True) else localization._('profile_cv_no_file_selected'))

        # self._update_doc_tree_headers_profile() # If this method exists and is needed
        # self._update_action_log_tree_headers_profile() # If this method exists

    # --- Methods for Document Management (to be adapted from HRAppGUI) ---
    def _load_documents_to_tree(self):
        # Adapted from HRAppGUI._load_documents_to_tree
        if not hasattr(self, 'doc_tree_profile') or not self.doc_tree_profile.winfo_exists(): return
        for item in self.doc_tree_profile.get_children(): self.doc_tree_profile.delete(item)
        try:
            documents = db_queries.get_employee_documents_db(self.employee_id)
            for doc in documents:
                filename = os.path.basename(doc[db_schema.COL_DOC_FILE_PATH])
                self.doc_tree_profile.insert("", "end", values=(
                    doc[db_schema.COL_DOC_ID], doc[db_schema.COL_DOC_TYPE], filename, doc[db_schema.COL_DOC_UPLOAD_DATE]
                ), iid=doc[db_schema.COL_DOC_ID])
        except (db_queries.DatabaseOperationError, db_queries.EmployeeNotFoundError) as e:
            messagebox.showerror(localization._("error_loading_documents_title"), str(e), parent=self)
        self._on_document_tree_select() # Update button states

    def _on_document_tree_select(self, event=None):
        # Adapted from HRAppGUI._on_document_tree_select
        if not hasattr(self, 'doc_tree_profile'): return
        is_selected = bool(self.doc_tree_profile.selection())
        if hasattr(self, 'view_doc_btn_profile'): self.view_doc_btn_profile.config(state="normal" if is_selected else "disabled")
        if hasattr(self, 'delete_doc_btn_profile'): self.delete_doc_btn_profile.config(state="normal" if is_selected else "disabled")
        
        can_sign = False
        if is_selected and fitz and hasattr(self, 'doc_tree_profile'):
            selected_item_iid = self.doc_tree_profile.focus()
            item_values = self.doc_tree_profile.item(selected_item_iid, "values")
            if item_values and len(item_values) > 2:
                doc_type = item_values[1]
                filename = item_values[2]
                if filename.lower().endswith(".pdf") and doc_type.lower() == "contract":
                    can_sign = True
        if hasattr(self, 'sign_doc_btn'): self.sign_doc_btn.config(state="normal" if can_sign else "disabled")

    def _gui_add_document(self):
        # Adapted from HRAppGUI._gui_add_document
        filepath = filedialog.askopenfilename(
            title=localization._("doc_mgt_select_file_dialog_title"),
            filetypes=[("PDF files", "*.pdf"), ("Word documents", "*.docx"), ("Images", "*.jpg *.png"), ("All files", "*.*")],
            parent=self
        )
        if not filepath: return
        doc_type = simpledialog.askstring(localization._("doc_mgt_doc_type_dialog_title"), localization._("doc_mgt_doc_type_dialog_prompt"), parent=self)
        if not doc_type: return
        try:
            db_queries.add_employee_document_db(self.employee_id, doc_type, filepath)
            messagebox.showinfo(localization._("success_title"), localization._("document_added_success_message"), parent=self)
            self._load_documents_to_tree()
        except (db_queries.EmployeeNotFoundError, FileNotFoundError, db_queries.DatabaseOperationError) as e:
            messagebox.showerror(localization._("error_adding_document_title"), str(e), parent=self)

    def _gui_view_document(self):
        # Adapted from HRAppGUI._gui_view_document
        if not hasattr(self, 'doc_tree_profile'): return
        selected_item_iid = self.doc_tree_profile.focus()
        if not selected_item_iid: return
        doc_id_to_view = int(selected_item_iid)
        try:
            documents = db_queries.get_employee_documents_db(self.employee_id)
            doc_to_view = next((doc for doc in documents if doc[db_schema.COL_DOC_ID] == doc_id_to_view), None)
            if doc_to_view and os.path.exists(doc_to_view[db_schema.COL_DOC_FILE_PATH]):
                file_path = doc_to_view[db_schema.COL_DOC_FILE_PATH]
                if sys.platform == "win32": os.startfile(file_path)
                elif sys.platform == "darwin": subprocess.call(('open', file_path))
                else: subprocess.call(('xdg-open', file_path))
            else:
                messagebox.showerror(localization._("error_title"), localization._("document_file_not_found_error"), parent=self)
        except Exception as e:
            logger.error(f"Error opening document: {e}")
            messagebox.showerror(localization._("error_title"), localization._("could_not_open_document_error", error=e), parent=self)

    def _gui_delete_document(self):
        # Adapted from HRAppGUI._gui_delete_document
        if not hasattr(self, 'doc_tree_profile'): return
        selected_item_iid = self.doc_tree_profile.focus()
        if not selected_item_iid: return
        doc_id_to_delete = int(selected_item_iid)
        if messagebox.askyesno(localization._("confirm_delete_title"), localization._("confirm_delete_document_message"), parent=self):
            try:
                db_queries.delete_employee_document_db(doc_id_to_delete)
                messagebox.showinfo(localization._("success_title"), localization._("document_deleted_success_message"), parent=self)
                self._load_documents_to_tree()
            except (FileNotFoundError, db_queries.DatabaseOperationError) as e:
                messagebox.showerror(localization._("error_deleting_document_title"), str(e), parent=self)

    def _gui_sign_document(self):
        # Adapted from HRAppGUI._gui_sign_document
        if not fitz:
            messagebox.showerror(localization._("error_title"), localization._("pdf_signing_lib_not_installed_error"), parent=self)
            return
        if not hasattr(self, 'doc_tree_profile'): return
        selected_item_iid = self.doc_tree_profile.focus()
        if not selected_item_iid:
            messagebox.showerror(localization._("error_title"), localization._("no_document_selected_error"), parent=self)
            return
        # ... (rest of the signing logic from HRAppGUI, adapted for self)

    # --- Methods for Action Log (to be adapted from HRAppGUI) ---
    def _load_action_log_to_tree(self):
        # Adapted from HRAppGUI._load_action_log_to_tree
        if not hasattr(self, 'action_log_tree_profile'): return
        for item in self.action_log_tree_profile.get_children(): self.action_log_tree_profile.delete(item)
        try:
            logs = db_queries.get_employee_action_log_db(self.employee_id)
            for log_entry in logs:
                timestamp_str = log_entry[db_schema.COL_EAL_TIMESTAMP]
                try:
                    timestamp_dt = datetime.fromisoformat(timestamp_str)
                    formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    formatted_timestamp = timestamp_str
                self.action_log_tree_profile.insert("", "end", values=(
                    formatted_timestamp, log_entry[db_schema.COL_EAL_ACTION_DESC],
                    log_entry.get("performed_by_username", localization._("system_unknown_user"))
                ))
        except (db_queries.DatabaseOperationError, db_queries.EmployeeNotFoundError) as e:
            messagebox.showerror(localization._("error_loading_action_log_title"), str(e), parent=self)

    def _update_doc_tree_headers(self):
        # Placeholder - copy from main_gui.py if needed for this window
        if hasattr(self, 'doc_tree_profile') and self.doc_tree_profile.winfo_exists():
            self.doc_tree_profile.heading(db_schema.COL_DOC_ID, text=localization._("profile_doc_id_header"))
            self.doc_tree_profile.heading(db_schema.COL_DOC_TYPE, text=localization._("profile_doc_type_header"))
            self.doc_tree_profile.heading("filename", text=localization._("profile_doc_filename_header"))
            self.doc_tree_profile.heading(db_schema.COL_DOC_UPLOAD_DATE, text=localization._("profile_doc_uploaded_header"))

    def _update_action_log_tree_headers(self):
        # Placeholder - copy from main_gui.py if needed for this window
        if hasattr(self, 'action_log_tree_profile') and self.action_log_tree_profile.winfo_exists():
            self.action_log_tree_profile.heading("timestamp", text=localization._("profile_action_log_timestamp_header"))
            self.action_log_tree_profile.heading("action", text=localization._("profile_action_log_action_header"))
            self.action_log_tree_profile.heading("performed_by", text=localization._("profile_action_log_performed_by_header"))

    def _update_emp_skills_tree_headers(self):
        if hasattr(self, 'emp_skills_tree') and self.emp_skills_tree.winfo_exists():
            self.emp_skills_tree.heading("skill_name", text=localization._("profile_skills_header_name"))
            self.emp_skills_tree.heading("skill_category", text=localization._("profile_skills_header_category"))
            self.emp_skills_tree.heading("proficiency_level", text=localization._("profile_skills_header_proficiency"))
            self.emp_skills_tree.heading("acquisition_date", text=localization._("profile_skills_header_acquired_date"))

    def _load_employee_skills_to_tree(self):
        if not hasattr(self, 'emp_skills_tree') or not self.emp_skills_tree.winfo_exists(): return
        for item in self.emp_skills_tree.get_children(): self.emp_skills_tree.delete(item)
        try:
            skills = db_queries.get_employee_skills_db(self.employee_id)
            if not skills:
                # self.emp_skills_tree.insert("", "end", values=(localization._("profile_skills_no_skills_assigned"), "", "", ""))
                return # No need to display "no skills" in the tree, can be a separate label if desired
            for skill in skills:
                self.emp_skills_tree.insert("", "end", iid=skill[db_schema.COL_EMP_SKILL_SKILL_ID], values=( # Use skill_id as IID
                    skill.get(db_schema.COL_SKILL_NAME, "N/A"),
                    skill.get(db_schema.COL_SKILL_CATEGORY, "N/A"),
                    skill.get(db_schema.COL_EMP_SKILL_PROFICIENCY_LEVEL, "N/A"),
                    skill.get(db_schema.COL_EMP_SKILL_ACQUISITION_DATE, "N/A")
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("profile_skills_error_loading", error=e), parent=self)
        self._on_employee_skill_select() # Update button states

    def _on_employee_skill_select(self, event=None):
        if not hasattr(self, 'emp_skills_tree'): return
        is_selected = bool(self.emp_skills_tree.selection())
        if hasattr(self, 'edit_emp_skill_btn'): self.edit_emp_skill_btn.config(state="normal" if is_selected else "disabled")
        if hasattr(self, 'remove_emp_skill_btn'): self.remove_emp_skill_btn.config(state="normal" if is_selected else "disabled")

    def _gui_show_qr_code_profile(self):
        """Shows the QR code for the current employee in a new dialog."""
        if not self.employee_id or not self.employee_details:
            messagebox.showwarning(localization._("warning_title"), "Employee data not loaded.", parent=self)
            return

        emp_name = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id)
        qr_data = self.employee_id # Data to encode in QR

        qr_image_pil = image_utils.create_qr_code_image(qr_data)
        if not qr_image_pil:
            messagebox.showerror(localization._("error_title"), "Failed to generate QR code.", parent=self)
            return

        qr_window = ThemedToplevel(self, self.parent_app)
        qr_window.title(localization._("qr_code_window_title_profile", emp_name=emp_name, emp_id=self.employee_id))
        qr_window.geometry("300x380") # Adjusted for save button

        # Convert PIL image to PhotoImage for Tkinter
        qr_image_pil.thumbnail((250, 250), Image.Resampling.LANCZOS) # Resize for display
        qr_photo_image = ImageTk.PhotoImage(qr_image_pil)

        qr_label = ttk.Label(qr_window, image=qr_photo_image)
        qr_label.image = qr_photo_image # Keep a reference!
        qr_label.pack(pady=10)

        ttk.Label(qr_window, text=f"{emp_name} ({self.employee_id})").pack(pady=5)

        def save_qr():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                title=localization._("qr_code_save_btn_profile"), # Reusing button text as title
                initialfile=f"{self.employee_id}_qr.png",
                parent=qr_window
            )
            if filepath: qr_image_pil.save(filepath)

        save_button = ttk.Button(qr_window, text=localization._("qr_code_save_btn_profile"), command=save_qr, bootstyle=db_schema.BS_ADD)
        save_button.pack(pady=10)

    def update_local_theme_elements(self):
        super().update_local_theme_elements()
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        if hasattr(self, 'cv_extracted_text_widget') and self.cv_extracted_text_widget.winfo_exists():
            _theme_text_widget_global(self.cv_extracted_text_widget, palette)
        if hasattr(self, 'job_desc_text') and self.job_desc_text.winfo_exists():
            _theme_text_widget_global(self.job_desc_text, palette)
        if hasattr(self, 'suitability_results_text') and self.suitability_results_text.winfo_exists():
            _theme_text_widget_global(self.suitability_results_text, palette)
