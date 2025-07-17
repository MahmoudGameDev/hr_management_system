# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\document_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
# from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used # No DateEntry needed here
import logging
from datetime import datetime #, date as dt_date # dt_date not used
from typing import Optional #, Dict, List, Any, Union # Other typings not used directly
# --- Project-specific imports ---
from data import database as db_schema
from data import queries as db_queries
from utils import localization
from utils import pdf_utils # Not directly used, but ElectronicContractWindow might use it
from utils.gui_utils import populate_employee_combobox, extract_id_from_combobox_selection # Not used here
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global
from .themed_toplevel import ThemedToplevel
from .electronic_contract_window import ElectronicContractWindow # This import should now work
# For opening files
import os
import sys
import subprocess # For cross-platform file opening
# ... rest of the DocumentManagementWindow class
import tkinter as tk
from PIL import Image, ImageTk, UnidentifiedImageError # For signature image handling
import fitz  # PyMuPDF # For PDF signing
# --- Project-specific imports ---
from utils.file_utils import secure_delete_file # If used
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # For theming non-ttk widgets (if any remain)
logger = logging.getLogger(__name__)

class DocumentManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, employee_id: str):
        super().__init__(parent, app_instance)
        self.employee_id = employee_id
        self.employee_details = db_queries.get_employee_by_id_db(employee_id) # Fetch for display
        
        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id) if self.employee_details else self.employee_id
        self.title(localization._("document_management_window_title", employee_name=emp_name_display)) # Add key
        self.geometry("750x500") # Adjust as needed
        self.translatable_widgets_docs = []

        # --- Main Frame ---
        main_frame = ttkb.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # --- Actions Frame ---
        actions_frame = ttkb.Frame(main_frame)
        actions_frame.pack(side="top", fill="x", pady=5)

        add_btn_key = "doc_mgt_add_button"
        self.add_doc_btn = ttkb.Button(actions_frame, text=localization._(add_btn_key), command=self._gui_add_document, bootstyle=db_schema.BS_ADD)
        self.add_doc_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.add_doc_btn, add_btn_key)

        view_btn_key = "doc_mgt_view_button"
        self.view_doc_btn = ttkb.Button(actions_frame, text=localization._(view_btn_key), command=self._gui_view_document, state="disabled", bootstyle=db_schema.BS_VIEW_EDIT)
        self.view_doc_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.view_doc_btn, view_btn_key)

        delete_btn_key = "doc_mgt_delete_button"
        self.delete_doc_btn = ttkb.Button(actions_frame, text=localization._(delete_btn_key), command=self._gui_delete_document, state="disabled", bootstyle=db_schema.BS_DELETE_FINISH)
        self.delete_doc_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.delete_doc_btn, delete_btn_key)

        # --- New Contract Button ---
        create_contract_btn_key = "doc_mgt_create_contract_button"
        self.create_contract_btn = ttkb.Button(actions_frame, text=localization._(create_contract_btn_key), command=self._gui_create_new_contract, bootstyle=db_schema.BS_ADD)
        self.create_contract_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.create_contract_btn, create_contract_btn_key)

        sign_btn_key = "doc_mgt_sign_button"
        self.sign_doc_btn = ttkb.Button(actions_frame, text=localization._(sign_btn_key), command=self._gui_sign_document, state="disabled", bootstyle="success")
        if not fitz: # If fitz is not imported
            self.sign_doc_btn.config(state="disabled")
            # ToolTip(self.sign_doc_btn, text="PDF signing library (PyMuPDF) not installed.") # Tooltip requires import
        self.sign_doc_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.sign_doc_btn, sign_btn_key)

        # --- Document List Treeview ---
        list_lf_key = "doc_mgt_list_frame_title"
        list_frame = ttkb.LabelFrame(main_frame, text=localization._(list_lf_key), padding="10")
        list_frame.pack(fill="both", expand=True, pady=5)
        self._add_translatable_widget(list_frame, list_lf_key, attr="title")

        self.doc_tree_cols = (db_schema.COL_DOC_ID, db_schema.COL_DOC_TYPE, "filename", db_schema.COL_DOC_UPLOAD_DATE) # Removed notes from tree view
        self.doc_tree = ttkb.Treeview(list_frame, columns=self.doc_tree_cols, show="headings")
        self._update_doc_tree_headers() # Set initial headers

        self.doc_tree.column(db_schema.COL_DOC_ID, width=60, anchor="e", stretch=tk.NO)
        self.doc_tree.column(db_schema.COL_DOC_TYPE, width=150)
        self.doc_tree.column("filename", width=350, stretch=tk.YES) # Increased width
        self.doc_tree.column(db_schema.COL_DOC_UPLOAD_DATE, width=120, anchor="center")

        scrollbar = ttkb.Scrollbar(list_frame, orient="vertical", command=self.doc_tree.yview)
        self.doc_tree.configure(yscrollcommand=scrollbar.set)
        self.doc_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.doc_tree.bind("<<TreeviewSelect>>", self._on_document_select)

        self._load_documents_to_tree()

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_docs.append({"widget": widget, "key": key, "attr": attr})

    def _update_doc_tree_headers(self):
        if hasattr(self, 'doc_tree') and self.doc_tree.winfo_exists():
            self.doc_tree.heading(db_schema.COL_DOC_ID, text=localization._("doc_mgt_header_id"))
            self.doc_tree.heading(db_schema.COL_DOC_TYPE, text=localization._("doc_mgt_header_type"))
            self.doc_tree.heading("filename", text=localization._("doc_mgt_header_filename"))
            self.doc_tree.heading(db_schema.COL_DOC_UPLOAD_DATE, text=localization._("doc_mgt_header_uploaded"))

    def refresh_ui_for_language(self): # pragma: no cover
        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id) if self.employee_details else self.employee_id
        self.title(localization._("document_management_window_title", employee_name=emp_name_display))
        self._update_doc_tree_headers()
        for item in self.translatable_widgets_docs:
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

    def _load_documents_to_tree(self):
        for item in self.doc_tree.get_children():
            self.doc_tree.delete(item)
        try:
            documents = db_queries.get_employee_documents_db(self.employee_id)
            for doc in documents:
                filename = os.path.basename(doc[db_schema.COL_DOC_FILE_PATH])
                self.doc_tree.insert("", "end", values=(
                    doc[db_schema.COL_DOC_ID], doc[db_schema.COL_DOC_TYPE], filename, doc[db_schema.COL_DOC_UPLOAD_DATE]
                ), iid=doc[db_schema.COL_DOC_ID]) # Use doc_id as item ID for easier retrieval
        except (db_queries.DatabaseOperationError, db_queries.EmployeeNotFoundError) as e:
            messagebox.showerror(localization._("error_loading_documents_title"), str(e), parent=self)
        self._on_document_select() # Reset button states

    def _on_document_select(self, event=None):
        is_selected = bool(self.doc_tree.selection())
        self.view_doc_btn.config(state="normal" if is_selected else "disabled")
        self.delete_doc_btn.config(state="normal" if is_selected else "disabled")
        can_sign = False
        if is_selected and fitz: # Only check if fitz is available
            selected_item_iid = self.doc_tree.focus()
            item_values = self.doc_tree.item(selected_item_iid, "values")
            # Values: doc_id, doc_type, filename, upload_date
            if item_values:
                doc_type = item_values[1]
                filename = item_values[2]
                if filename.lower().endswith(".pdf") and doc_type.lower() == "contract":
                    can_sign = True
        self.sign_doc_btn.config(state="normal" if can_sign else "disabled")

    def _gui_add_document(self):
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
        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid: return

        doc_id_to_view = int(selected_item_iid)
        try:
            # Fetch the document details including the file path
            documents = db_queries.get_employee_documents_db(self.employee_id)
            doc_to_view = next((doc for doc in documents if doc[db_schema.COL_DOC_ID] == doc_id_to_view), None)
            
            if doc_to_view and os.path.exists(doc_to_view[db_schema.COL_DOC_FILE_PATH]):
                file_path = doc_to_view[db_schema.COL_DOC_FILE_PATH]
                if sys.platform == "win32": # Windows
                    os.startfile(file_path)
                elif sys.platform == "darwin": # macOS
                    subprocess.call(('open', file_path))
                else: # linux variants
                    subprocess.call(('xdg-open', file_path))
            else:
                messagebox.showerror(localization._("error_title"), localization._("document_file_not_found_error"), parent=self)
        except Exception as e:
            logger.error(f"Error opening document: {e}")
            messagebox.showerror(localization._("error_title"), localization._("could_not_open_document_error", error=e), parent=self)

    def _gui_delete_document(self):
        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid: return

        doc_id_to_delete = int(selected_item_iid)

        if messagebox.askyesno(localization._("confirm_delete_title"), localization._("confirm_delete_document_message"), parent=self):
            try:
                db_queries.delete_employee_document_db(doc_id_to_delete)
                messagebox.showinfo(localization._("success_title"), localization._("document_deleted_success_message"), parent=self)
                self._load_documents_to_tree()
            except (FileNotFoundError, db_queries.DatabaseOperationError) as e:
                messagebox.showerror(localization._("error_deleting_document_title"), str(e), parent=self)

    def _gui_create_new_contract(self):
        """Opens the ElectronicContractWindow to create a new contract for this employee."""
        # Use the ApplicationController's helper to create and track the window
        self.parent_app._create_and_show_toplevel(
            ElectronicContractWindow,
            employee_id=self.employee_id,
            tracker_attr_name=f"active_electronic_contract_window_{self.employee_id}" # Track per employee
        )

    def _gui_sign_document(self):
        if not fitz:
            messagebox.showerror(localization._("error_title"), localization._("pdf_signing_lib_not_installed_error"), parent=self)
            return

        selected_item_iid = self.doc_tree.focus()
        if not selected_item_iid:
            messagebox.showerror(localization._("error_title"), localization._("no_document_selected_error"), parent=self)
            return

        doc_id_to_sign = int(selected_item_iid)
        try:
            documents = db_queries.get_employee_documents_db(self.employee_id)
            doc_to_sign = next((doc for doc in documents if doc[db_schema.COL_DOC_ID] == doc_id_to_sign), None)
            if not doc_to_sign: # pragma: no cover
                messagebox.showerror(localization._("error_title"), localization._("document_not_found_in_db_error"), parent=self)
                return

            pdf_path = doc_to_sign[db_schema.COL_DOC_FILE_PATH]
            if not pdf_path.lower().endswith(".pdf"): # Should be caught by button state, but double check
                messagebox.showerror(localization._("error_title"), localization._("document_not_pdf_error"), parent=self)
                return

            # Open the PDF to get page count
            try:
                doc_info = fitz.open(pdf_path)
                num_pages = len(doc_info)
                doc_info.close()
            except Exception as e_pdf_info:
                 logger.error(f"Error getting PDF page count for signing: {e_pdf_info}")
                 messagebox.showerror(localization._("signing_error_title"), localization._("could_not_read_pdf_info_error"), parent=self)
                 return

            page_num_str = simpledialog.askstring(
                localization._("page_number_for_signature_dialog_title"),
                localization._("page_number_for_signature_dialog_prompt", num_pages=num_pages),
                parent=self
            )
            if not page_num_str: return
            try:
                page_num_to_sign = int(page_num_str) - 1 # Convert to 0-indexed
                if not (0 <= page_num_to_sign < num_pages):
                    messagebox.showerror(localization._("error_title"), localization._("invalid_page_number_error", num_pages=num_pages), parent=self)
                    return
            except ValueError:
                messagebox.showerror(localization._("error_title"), localization._("invalid_page_number_entered_error"), parent=self)
                return

            signature_image_path = filedialog.askopenfilename(
                title=localization._("select_signature_image_dialog_title"),
                filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
                parent=self
            )
            if not signature_image_path: return

            # Embed the signature
            # Need to decide size and position - for now, hardcode last page bottom-right
            db_queries.embed_image_in_pdf(pdf_path, signature_image_path, page_num_to_sign, sig_width=150, sig_height=75, position="bottom-right", margin=50) # Adjust size/position

            messagebox.showinfo(localization._("success_title"), localization._("document_signed_success_message"), parent=self)
            # Optionally refresh the document list to show the modified date/time if needed
            self._load_documents_to_tree()

        except Exception as e:
            logger.error(f"Error signing document: {e}", exc_info=True)
            messagebox.showerror(localization._("signing_error_title"), localization._("error_occurred_signing_error", error=e), parent=self)