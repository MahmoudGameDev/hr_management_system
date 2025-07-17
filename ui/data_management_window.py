# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\data_management_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # For archive cutoff date
import logging
import os
from datetime import datetime, date as dt_date, timedelta

# --- Project-specific imports ---
from data import database as db_schema # For constants if needed
from data import queries as db_queries # For backup, restore, archive functions
from utils import localization # For _()
from utils.file_utils import create_backup_db, restore_database_from_backup # Assuming these are moved or accessible
from .themed_toplevel import ThemedToplevel
import config # For default backup directory

logger = logging.getLogger(__name__)

class DataManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("data_management_window_title")) # Add key
        self.geometry("600x450") # Adjust as needed
        self.translatable_widgets_data_mgt = []

        main_frame = ttkb.Frame(self, padding="15")
        main_frame.pack(expand=True, fill="both")

        # --- Backup Section ---
        backup_lf_key = "data_mgt_backup_frame_title"
        backup_frame = ttkb.LabelFrame(main_frame, text=localization._(backup_lf_key), padding="10")
        backup_frame.pack(fill="x", pady=10)
        self._add_translatable_widget(backup_frame, backup_lf_key, attr="title")

        backup_btn_key = "data_mgt_backup_button"
        self.backup_btn = ttkb.Button(backup_frame, text=localization._(backup_btn_key), command=self._gui_create_backup, bootstyle=db_schema.BS_ADD)
        self.backup_btn.pack(pady=5)
        self._add_translatable_widget(self.backup_btn, backup_btn_key)

        # --- Restore Section ---
        restore_lf_key = "data_mgt_restore_frame_title"
        restore_frame = ttkb.LabelFrame(main_frame, text=localization._(restore_lf_key), padding="10")
        restore_frame.pack(fill="x", pady=10)
        self._add_translatable_widget(restore_frame, restore_lf_key, attr="title")
        
        restore_btn_key = "data_mgt_restore_button"
        self.restore_btn = ttkb.Button(restore_frame, text=localization._(restore_btn_key), command=self._gui_restore_backup, bootstyle=db_schema.BS_DELETE_FINISH) # Danger style for restore
        self.restore_btn.pack(pady=5)
        self._add_translatable_widget(self.restore_btn, restore_btn_key)

        # --- Data Archiving Section ---
        archive_lf_key = "data_mgt_archive_frame_title"
        archive_frame = ttkb.LabelFrame(main_frame, text=localization._(archive_lf_key), padding="10")
        archive_frame.pack(fill="x", pady=10)
        self._add_translatable_widget(archive_frame, archive_lf_key, attr="title")
        archive_frame.columnconfigure(1, weight=1)

        cutoff_lbl_key = "data_mgt_archive_cutoff_label"
        ttk.Label(archive_frame, text=localization._(cutoff_lbl_key)).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self._add_translatable_widget(archive_frame.grid_slaves(row=0,column=0)[0], cutoff_lbl_key)
        
        self.archive_cutoff_date_entry = DateEntry(archive_frame, width=12, dateformat='%Y-%m-%d')
        self.archive_cutoff_date_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        # Set a sensible default, e.g., 1 year ago
        self.archive_cutoff_date_entry.date = dt_date.today() - timedelta(days=365)

        archive_btn_key = "data_mgt_archive_button"
        self.archive_btn = ttkb.Button(archive_frame, text=localization._(archive_btn_key), command=self._gui_archive_data, bootstyle=db_schema.BS_VIEW_EDIT)
        self.archive_btn.grid(row=0, column=2, padx=10, pady=5)
        self._add_translatable_widget(self.archive_btn, archive_btn_key)

        # --- Status/Log Area (Optional) ---
        # status_lf_key = "data_mgt_status_log_frame_title"
        # status_frame = ttkb.LabelFrame(main_frame, text=localization._(status_lf_key), padding="10")
        # status_frame.pack(fill="both", expand=True, pady=10)
        # self.status_log_text = tk.Text(status_frame, height=5, wrap="word", state="disabled")
        # self.status_log_text.pack(fill="both", expand=True)
        # palette = get_theme_palette_global(self.parent_app.get_current_theme())
        # _theme_text_widget_global(self.status_log_text, palette)

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_data_mgt.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("data_management_window_title"))
        for item in self.translatable_widgets_data_mgt:
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

    def _gui_create_backup(self):
        backup_dir = config.BACKUP_DIR # Use from config
        os.makedirs(backup_dir, exist_ok=True)
        
        default_filename = f"hr_system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database Backup", "*.db"), ("All files", "*.*")],
            initialdir=backup_dir,
            initialfile=default_filename,
            title=localization._("data_mgt_backup_dialog_title"),
            parent=self
        )
        if not filepath:
            return

        try:
            # Assuming create_backup_db is moved to file_utils or db_queries
            backup_path = create_backup_db(custom_filename=os.path.basename(filepath), backup_directory=os.path.dirname(filepath))
            if backup_path: # Parent should be self
                messagebox.showinfo(localization._("success_title"), localization._("data_mgt_backup_success_message", path=backup_path), parent=self)
            else:
                messagebox.showerror(localization._("error_title"), localization._("data_mgt_backup_failed_message"), parent=self)
        except Exception as e:
            logger.error(f"Error creating backup: {e}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("data_mgt_backup_error", error=e), parent=self)

    def _gui_restore_backup(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database Backup", "*.db"), ("All files", "*.*")],
            initialdir=config.BACKUP_DIR,
            title=localization._("data_mgt_restore_dialog_title"),
            parent=self
        )
        if not filepath:
            return

        if messagebox.askyesno(
            localization._("data_mgt_restore_confirm_title"),
            localization._("data_mgt_restore_confirm_message"),
            icon='warning', parent=self
        ):
            try:
                # Assuming restore_database_from_backup is moved to file_utils or db_queries
                if restore_database_from_backup(filepath): # This function should handle closing current connections
                    messagebox.showinfo(localization._("success_title"), localization._("data_mgt_restore_success_message"), parent=self) # Parent should be self
                    # Critical: Application needs to re-initialize with the new DB.
                    # This might mean restarting the app or re-initializing ApplicationController.
                    # For now, just inform the user.
                    messagebox.showinfo(localization._("info_title"), localization._("data_mgt_restart_required_message"), parent=self)
                    self.parent_app.on_close_main_app() # Trigger app close/restart sequence
                else:
                    messagebox.showerror(localization._("error_title"), localization._("data_mgt_restore_failed_message"), parent=self)
            except Exception as e:
                logger.error(f"Error restoring backup: {e}", exc_info=True)
                messagebox.showerror(localization._("error_title"), localization._("data_mgt_restore_error", error=e), parent=self)

    def _gui_archive_data(self):
        cutoff_date_str = self.archive_cutoff_date_entry.entry.get()
        if not cutoff_date_str:
            messagebox.showwarning(localization._("input_error_title"), localization._("data_mgt_archive_select_cutoff_warning"), parent=self)
            return
        try:
            dt_date.fromisoformat(cutoff_date_str) # Validate date
        except ValueError:
            messagebox.showerror(localization._("input_error_title"), localization._("invalid_date_format_yyyy_mm_dd_error"), parent=self)
            return

        confirm_msg = localization._("data_mgt_archive_confirm_message", date=cutoff_date_str)
        if messagebox.askyesno(localization._("data_mgt_archive_confirm_title"), confirm_msg, icon='warning', parent=self):
            try:
                archived_count = db_queries.archive_terminated_employees_db(cutoff_date_str)
                messagebox.showinfo(localization._("success_title"), localization._("data_mgt_archive_success_message", count=archived_count), parent=self)
                # Optionally refresh main employee list if it's visible and affected
                if self.parent_app and hasattr(self.parent_app, 'main_gui') and self.parent_app.main_gui:
                    self.parent_app.main_gui.load_employees_into_treeview()
            except (db_queries.InvalidInputError, db_queries.DatabaseOperationError) as e:
                messagebox.showerror(localization._("error_title"), str(e), parent=self)
            except Exception as e:
                logger.error(f"Unexpected error during data archiving: {e}", exc_info=True)
                messagebox.showerror(localization._("error_title"), localization._("data_mgt_archive_error", error=e), parent=self)
