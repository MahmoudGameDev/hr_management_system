# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\about_dialog.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging

# --- Project-specific imports ---
import config # For app version, contact info etc.
from utils.localization import _ # Import the _ function directly
from data import database as db_schema # Import database for BS_ constants
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class AboutDialog(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(_("about_dialog_title"))
        self.geometry("650x350") # Increased size for more info
        self.resizable(False, False)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")

        # Program Name
        self.program_name_label_static = ttk.Label(main_frame, text=_("about_program_name_label"))
        self.program_name_label_static.grid(row=0, column=0, sticky="e", pady=3, padx=(0,5))
        self.program_name_value = ttk.Label(main_frame, text=_("app_title")) # Use existing key
        self.program_name_value.grid(row=0, column=1, sticky="w", pady=3, padx=5)

        # Version
        self.version_label_static = ttk.Label(main_frame, text=_("about_version_label"))
        self.version_label_static.grid(row=1, column=0, sticky="e", pady=3, padx=(0,5))
        self.version_value = ttk.Label(main_frame, text="2.4.0") # Hardcoded version
        self.version_value.grid(row=1, column=1, sticky="w", pady=3, padx=5)

        # Developer
        self.developer_label_static = ttk.Label(main_frame, text=_("about_developer_label"))
        self.developer_label_static.grid(row=2, column=0, sticky="e", pady=3, padx=(0,5))
        self.developer_value = ttk.Label(main_frame, text="Mahmoud Ammar Sheikh Alkar")
        self.developer_value.grid(row=2, column=1, sticky="w", pady=3, padx=5)

        # Copyright
        self.copyright_label_static = ttk.Label(main_frame, text=_("about_copyright_label"))
        self.copyright_label_static.grid(row=3, column=0, sticky="e", pady=3, padx=(0,5))
        self.copyright_value = ttk.Label(main_frame, text="© 2023-2024 Mahmoud Ammar Sheikh Alkar. All rights reserved.")
        self.copyright_value.grid(row=3, column=1, sticky="w", pady=3, padx=5)

        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)

        # Technical Support Section Header
        self.tech_support_header_label = ttk.Label(main_frame, text=_("about_tech_support_header"), font=("Helvetica", 10, "bold"))
        self.tech_support_header_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(5,2))

        # Support Email
        self.support_email_label_static = ttk.Label(main_frame, text=_("about_support_email_label"))
        self.support_email_label_static.grid(row=6, column=0, sticky="e", pady=3, padx=(0,5))
        self.support_email_value = ttk.Label(main_frame, text="mahmoud.ammar.sh@gmail.com") # Actual email
        self.support_email_value.grid(row=6, column=1, sticky="w", pady=3, padx=5)

        # Support Phone
        self.support_phone_label_static = ttk.Label(main_frame, text=_("about_support_phone_label"))
        self.support_phone_label_static.grid(row=7, column=0, sticky="e", pady=3, padx=(0,5))
        self.support_phone_value = ttk.Label(main_frame, text="+963991787315") # Actual phone
        self.support_phone_value.grid(row=7, column=1, sticky="w", pady=3, padx=5)

        # Separator before close button
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=8, column=0, columnspan=2, sticky="ew", pady=10) # Parent should be self

        self.close_button = ttk.Button(main_frame, text=_("about_close_btn"), command=self.destroy, bootstyle=db_schema.BS_LIGHT)
        self.close_button.grid(row=9, column=0, columnspan=2, pady=(5,0))

        # Make the second column (values) expand
        main_frame.columnconfigure(1, weight=1)


    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("about_dialog_title"))
        # Update static labels if their keys were stored, or re-config them
        self.program_name_label_static.config(text=_("about_program_name_label"))
        self.program_name_value.config(text=_("app_title"))
        self.version_label_static.config(text=_("about_version_label"))
        self.developer_label_static.config(text=_("about_developer_label"))
        self.copyright_label_static.config(text=_("about_copyright_label"))
        self.tech_support_header_label.config(text=_("about_tech_support_header"))
        self.support_email_label_static.config(text=_("about_support_email_label"))
        self.support_phone_label_static.config(text=_("about_support_phone_label"))
        self.close_button.config(text=_("about_close_btn"))
        
    def _add_translatable_widget_about(self, widget, key):
        """Helper to register translatable widgets for AboutDialog."""
        self.translatable_widgets_about.append((widget, key))

    def refresh_ui_for_language(self):
        self.title(_("settings_window_title"))