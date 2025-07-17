# hr_dashboard_project/main.py
import tkinter as tk
import ttkbootstrap as tkb # Added import for ttkbootstrap
from ui.login_window import LoginWindow
import logging
import sqlite3 # For specific database errors
import configparser # For specific configuration file errors
import os
import sys

# Add the project root directory to sys.path to allow importing 'ui', 'data', etc.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tkinter import messagebox
from typing import Optional # Import Optional for type hinting

# --- Project-specific imports ---
# Assuming the structure:
# hr_dashboard_project/
#  ├── main.py
#  ├── config.py
#  ├── data/
#  │   ├── database.py
#  │   └── queries.py
#  ├── ui/
#  │   └── (various UI modules like ApplicationController, HRAppGUI, LoginWindow etc.)
#  └── utils/
#      ├── localization.py
#      └── ...

import config # From the root of hr_dashboard_project
from data import database as db_schema # Import the database module and alias it
from utils import localization # From utils.localization

from ui.application_controller import ApplicationController

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)

def show_loading(root_for_splash: Optional[tk.Tk] = None) -> Optional[tk.Toplevel]:
    """Shows a simple loading splash screen."""
    # If a root is provided and exists, make splash transient to it. Otherwise, create a temporary root.
    parent = root_for_splash if root_for_splash and root_for_splash.winfo_exists() else tk.Tk()
    if parent != root_for_splash: # If we created a temporary root, hide it.
        parent.withdraw()

    splash = tk.Toplevel(parent)
    splash.title("Loading...")
    # Make it transient if it's not the main root itself
    if parent != root_for_splash and root_for_splash and root_for_splash.winfo_exists():
        splash.transient(root_for_splash) # Make it transient to the main app's root if possible
    elif parent == root_for_splash and root_for_splash and root_for_splash.winfo_exists(): # If splash is child of main root
        splash.transient(root_for_splash)

    tk.Label(splash, text="Initializing... Please wait.").pack(padx=20, pady=20)
    splash.resizable(False, False)
    splash.grab_set() # Make it modal
    splash.update() # Force display

    # Center the splash screen
    splash.update_idletasks()
    width = splash.winfo_width()
    height = splash.winfo_height()
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    splash.geometry(f'{width}x{height}+{x}+{y}')

    return splash, parent # Return both splash and its parent (which might be temp)

def initialize_environment():
    """Initializes the application environment (DB, localization, etc.)."""
    # Set logging level based on DEBUG_MODE from config
    if config.DEBUG_MODE:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("DEBUG mode enabled. Logging level set to DEBUG.")
    app_controller = None # Initialize to None
    root = None # Initialize to None
    try:
        logger.info(f"Database will be: {config.DATABASE_NAME}")
        db_schema.init_db()
        # Fetch default language from DB settings, fallback to "en"
        default_lang = db_schema.get_app_setting_db(db_schema.SETTING_DEFAULT_LANGUAGE, "en")
        localization.init_translation(default_lang)
        logger.info(f"Localization initialized with language: {default_lang}")
    except Exception as e: # Catch specific initialization errors if needed
        logger.critical(f"Failed to initialize environment: {e}", exc_info=True)
        # Depending on the severity, you might want to re-raise or sys.exit here
        raise # Re-raise the exception to be caught by main's try-except

def main():
    logger.info("Application starting...")
    splash_window: Optional[tk.Toplevel] = None
    temp_splash_root: Optional[tk.Tk] = None # To manage temporary root for splash if main root not ready
    root: Optional[tk.Tk] = None # Initialize root to None

    try:
        # Show loading screen before heavy initialization
        # We don't have the main 'root' yet, so show_loading will create a temporary one.
        splash_window, temp_splash_root = show_loading()

        initialize_environment() # Heavy lifting

        # Destroy loading screen after initialization
        if splash_window and splash_window.winfo_exists():
            splash_window.destroy()
        if temp_splash_root and temp_splash_root != root and temp_splash_root.winfo_exists(): # Destroy temp root if created
            temp_splash_root.destroy()

        # Use ttkbootstrap.Window for the main root
        # config.DEFAULT_THEME should provide the initial theme name (e.g., "litera")
        root = tkb.Window(themename=config.DEFAULT_THEME)
        app_controller = ApplicationController(root)
        # Set protocol AFTER app_controller is created so it can be referenced
        # This handles the main window's 'X' button.
        root.protocol("WM_DELETE_WINDOW", app_controller.on_close_main_app)

        app_controller.start() # This will show the login window
        logger.info("Root mainloop starting...")
        root.mainloop()

    except sqlite3.Error as db_err:
        logger.critical(f"A critical database error occurred during application startup: {db_err}", exc_info=True)
        if splash_window and splash_window.winfo_exists(): splash_window.destroy() # Ensure splash is closed on error
        if temp_splash_root and temp_splash_root.winfo_exists(): temp_splash_root.destroy()
        messagebox.showerror("Database Startup Error", f"Could not initialize or connect to the database: {db_err}")
        sys.exit(1)
    except configparser.Error as cfg_err:
        logger.critical(f"A critical configuration error occurred during application startup: {cfg_err}", exc_info=True)
        if splash_window and splash_window.winfo_exists(): splash_window.destroy()
        if temp_splash_root and temp_splash_root.winfo_exists(): temp_splash_root.destroy()
        messagebox.showerror("Configuration Error", f"Could not load or parse configuration file: {cfg_err}")
        sys.exit(1)
    except FileNotFoundError as file_err:
        logger.critical(f"A required file was not found during application startup: {file_err}", exc_info=True)
        if splash_window and splash_window.winfo_exists(): splash_window.destroy()
        if temp_splash_root and temp_splash_root.winfo_exists(): temp_splash_root.destroy()
        messagebox.showerror("File Not Found Error", f"Could not start the application because a file is missing: {file_err}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"A critical error occurred during application startup: {e}", exc_info=True)
        if splash_window and splash_window.winfo_exists(): splash_window.destroy()
        if temp_splash_root and temp_splash_root.winfo_exists(): temp_splash_root.destroy()
        messagebox.showerror("Application Startup Error", f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure ttkbootstrap is imported if using ttkb.Window directly in main
    main()