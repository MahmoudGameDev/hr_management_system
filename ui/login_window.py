# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\login_window.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb
import logging

# Project-specific imports
from utils import localization
from utils.theming_utils import get_theme_palette_global, _theme_widget_recursively_global, _theme_text_widget_global
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from controller.auth_controller import AuthController

logger = logging.getLogger(__name__)

class LoginWindow(ttkb.Toplevel):  # Keep ttkbootstrap.Toplevel for proper styling
    def __init__(self, master: tk.Tk, auth_controller: 'AuthController', app_controller: 'ApplicationController'):
        print("DEBUG: LoginWindow: Initializing...")
        
        # Initialize with ttkbootstrap.Toplevel for proper styling
        super().__init__(master=master, transient=master)
        
        # Set theme explicitly
        if hasattr(self, 'style') and hasattr(self.style, 'theme_use'):
            self.style.theme_use("litera")
            print(f"DEBUG: LoginWindow: Set theme to 'litera'. Current style theme: {self.style.theme.name}")
        
        self.auth_controller = auth_controller
        self.app_controller = app_controller
        self.translatable_widgets_login: list = []

        self.title(localization._("login_window_title"))
        self.geometry("350x250+200+200")
        self.minsize(350, 220)
        self.resizable(False, False)
        
        # Withdraw initially to prevent flicker
        self.withdraw()

        print("DEBUG: LoginWindow: Creating widgets.")
        self._create_widgets()
        print("DEBUG: LoginWindow: Setting WM_DELETE_WINDOW protocol.")
        self.protocol("WM_DELETE_WINDOW", self._custom_close_handler)

        # Force geometry update and show window
        self.update_idletasks()
        
        theme_name_for_debug = "no style attribute"
        if hasattr(self, 'style') and self.style:
            if hasattr(self.style, 'theme') and self.style.theme and hasattr(self.style.theme, 'name'):
                theme_name_for_debug = self.style.theme.name
            else:
                theme_name_for_debug = "theme name unknown"
        print(f"DEBUG: LoginWindow.__init__ complete. Initial geometry: {self.geometry()}, Theme: {theme_name_for_debug}")
        
        # Show and make modal with proper timing
        # This 'after' job will now be tracked by ThemedToplevel's overridden 'after' method
        # and cancelled by its _cancel_all_after_jobs if the window is destroyed.
        self._show_modal_after_id = self.after(10, self._show_and_make_modal) 


    def _show_and_make_modal(self):
        """Show the window and make it modal."""
        theme_name_for_debug_modal = "no style attribute"
        if hasattr(self, 'style') and self.style:
            if hasattr(self.style, 'theme') and self.style.theme and hasattr(self.style.theme, 'name'):
                theme_name_for_debug_modal = self.style.theme.name
            else:
                theme_name_for_debug_modal = "theme name unknown" # Should not happen if theme_use succeeded
        print(f"DEBUG: LoginWindow: Executing _show_and_make_modal. Current theme: {theme_name_for_debug_modal}")

        try:
            # Ensure geometry is properly set
            self.geometry("350x250+200+200")
            self.update_idletasks()
            
            # Apply custom theming if needed
            self._apply_custom_theming()
            
            # Make window visible and modal
            self.deiconify()
            self.lift()
            self.focus_force()
            self.transient(self.master)  # Set to be on top of its master
            self.grab_set()
            self.lift()  # Bring to front
            # Force final update
            self.update()
            
            print(f"DEBUG: LoginWindow: _show_and_make_modal completed. Final Geometry: {self.geometry()}, W: {self.winfo_width()}, H: {self.winfo_height()}, Viewable: {self.winfo_viewable()}")
        except Exception as e:
            print(f"DEBUG: LoginWindow: Error in _show_and_make_modal: {e}")
            logger.error(f"Error in _show_and_make_modal: {e}", exc_info=True)

    def _apply_custom_theming(self):
        """Apply custom theming from the app controller."""
        try:
            theme_to_apply = "light"  # Default
            if self.app_controller and hasattr(self.app_controller, 'get_current_theme'):
                theme_to_apply = self.app_controller.get_current_theme()
            
            palette = get_theme_palette_global(theme_to_apply)
            if self.winfo_exists():
                self.config(bg=palette['bg_main'])
                _theme_widget_recursively_global(self, palette, _theme_text_widget_global)
        except Exception as e:
            print(f"DEBUG: LoginWindow: Error applying custom theming: {e}")
            logger.error(f"Error applying custom theming: {e}", exc_info=True)

    def _custom_close_handler(self):
        """Custom close handler for the LoginWindow."""
        if self.app_controller and hasattr(self.app_controller, 'on_close_main_app'):
            self.app_controller.on_close_main_app()
        else:
            self.destroy()

    def _add_translatable_widget_login(self, widget, key, attr="text"):
        """Helper to register translatable widgets for LoginWindow."""
        self.translatable_widgets_login.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self):
        """Update all translatable text elements in the Login window."""
        self.title(localization._("login_window_title"))
        for item_info in self.translatable_widgets_login:
            widget = item_info["widget"]
            key = item_info["key"]
            # attr = item_info.get("attr", "text") # LoginWindow only uses 'text' for now
            # For LoginWindow, all registered widgets are simple labels or buttons using 'text'

            if widget.winfo_exists():
                try: 
                    widget.config(text=localization._(key))
                except tk.TclError: 
                    pass

    def _create_widgets(self):
        main_frame = ttkb.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")

        login_frame = ttkb.Frame(main_frame)
        login_frame.pack(expand=True)

        username_label = ttkb.Label(login_frame, text=localization._("login_username_label"))
        username_label.pack(pady=(0, 5))
        self._add_translatable_widget_login(username_label, "login_username_label")
        self.username_var = tk.StringVar()
        self.username_entry = ttkb.Entry(login_frame, textvariable=self.username_var, width=30)
        self.username_entry.pack(pady=(0, 10))
        self.username_entry.focus_set()

        password_label = ttkb.Label(login_frame, text=localization._("login_password_label"))
        password_label.pack(pady=(0, 5))
        self._add_translatable_widget_login(password_label, "login_password_label")
        self.password_var = tk.StringVar()
        self.password_entry = ttkb.Entry(login_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(pady=(0, 10))
        self.password_entry.bind("<Return>", self._attempt_login)

        login_button = ttkb.Button(login_frame, text=localization._("login_button_text"), command=self._attempt_login, bootstyle="primary")
        login_button.pack(pady=10)
        self._add_translatable_widget_login(login_button, "login_button_text")

    def _attempt_login(self, event=None):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            messagebox.showwarning(localization._("login_failed_title"), localization._("login_empty_fields_warning"), parent=self)
            return

        # Delegate login attempt to AuthController
        self.auth_controller.login(username, password)
        # AuthController will call app_controller.on_login_success or on_login_failed
        # on_login_failed should handle UI updates like clearing password and showing error.
        # If login is successful, on_login_success will destroy this window.

    def _on_closing(self):
        """Custom close handler for the LoginWindow."""
        if self.app_controller and hasattr(self.app_controller, 'on_close_main_app'):
            self.app_controller.on_close_main_app()
        else:
            self.destroy()
