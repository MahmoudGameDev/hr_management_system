# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\zkteco_management_window.py
import tkinter as tk
from typing import Optional
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
import logging
import queue
import threading
from datetime import datetime
from utils import zkteco_utils # Import the new ZKTeco utilities
# --- Project-specific imports ---
import config
from data import database as db_schema
from data import queries as db_queries # For get_app_setting_db
from utils import localization # For _()
from .themed_toplevel import ThemedToplevel
logger = logging.getLogger(__name__)

class ZKTecoManagementWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance)
        self.title(localization._("zkteco_management_window_title")) # Add key
        self.geometry("700x500") # Adjust as needed
        self.translatable_widgets_zk = []
        self.task_queue = queue.Queue() # For threaded tasks

        # --- UI Variables ---
        self.device_name_var = tk.StringVar(value=localization._("zk_device_default_name")) # Add key
        self.last_sync_var = tk.StringVar(value=localization._("status_not_available_short")) # Add key
        self.device_status_var = tk.StringVar(value=localization._("zk_status_unknown")) # Add key
        self.sync_message_var = tk.StringVar(value=localization._("status_ready")) # Add key
        self.sync_log_data = [] # Stores tuples of (timestamp, status, message)
        self.auto_sync_enabled_var = tk.BooleanVar(value=False) # Placeholder

        # --- Main container frame for the panel ---
        panel_container = ttkb.Frame(self, padding="15")
        panel_container.pack(expand=True, fill="both")

        # --- Device Info Section ---
        info_frame_key = "device_sync_info_frame_title"
        info_frame = ttkb.LabelFrame(panel_container, text=localization._(info_frame_key), padding="10")
        info_frame.pack(fill="x", pady=(0, 10))
        info_frame.columnconfigure(1, weight=1) # Make value column expand
        self._add_translatable_widget(info_frame, info_frame_key, attr="title")

        row_idx = 0
        assoc_device_lbl_key = "device_sync_assoc_device_label"
        assoc_device_lbl = ttkb.Label(info_frame, text=localization._(assoc_device_lbl_key))
        assoc_device_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(assoc_device_lbl, assoc_device_lbl_key)
        ttkb.Label(info_frame, textvariable=self.device_name_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        last_sync_lbl_key = "device_sync_last_sync_label"
        last_sync_lbl = ttkb.Label(info_frame, text=localization._(last_sync_lbl_key))
        last_sync_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(last_sync_lbl, last_sync_lbl_key)
        ttkb.Label(info_frame, textvariable=self.last_sync_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        status_lbl_key = "device_sync_status_label"
        status_lbl = ttkb.Label(info_frame, text=localization._(status_lbl_key))
        status_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(status_lbl, status_lbl_key)
        ttkb.Label(info_frame, textvariable=self.device_status_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # --- Action Buttons ---
        actions_frame = ttkb.Frame(info_frame)
        actions_frame.grid(row=row_idx, column=0, columnspan=2, pady=10, sticky="ew")

        test_conn_btn_key = "device_sync_test_conn_btn"
        self.test_conn_btn = ttkb.Button(actions_frame, text=localization._(test_conn_btn_key), command=self._gui_test_zk_connection, bootstyle=db_schema.BS_VIEW_EDIT)
        self.test_conn_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.test_conn_btn, test_conn_btn_key)

        resync_btn_key = "device_sync_resync_btn"
        self.resync_btn = ttkb.Button(actions_frame, text=localization._(resync_btn_key), command=self.gui_sync_from_zkteco, bootstyle=db_schema.BS_ADD)
        ToolTip(self.resync_btn, text=localization._("zk_tooltip_sync_logs")) # Add key
        self.resync_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.resync_btn, resync_btn_key)

        auto_sync_key = "device_sync_auto_sync_toggle"
        self.toggle_auto_sync_btn = ttkb.Checkbutton(actions_frame, text=localization._(auto_sync_key), variable=self.auto_sync_enabled_var, bootstyle="round-toggle", command=self._gui_toggle_auto_sync)
        self.toggle_auto_sync_btn.pack(side="left", padx=15)
        self._add_translatable_widget(self.toggle_auto_sync_btn, auto_sync_key)

        # --- Progress and Status Messages ---
        progress_status_frame = ttkb.Frame(panel_container)
        progress_status_frame.pack(fill="x", pady=5)

        self.sync_progressbar = ttkb.Progressbar(progress_status_frame, mode="determinate", length=300)
        self.sync_progressbar.pack(side="left", padx=5, expand=True, fill="x")
        
        self.sync_message_label = ttkb.Label(progress_status_frame, textvariable=self.sync_message_var, width=40, anchor="w")
        self.sync_message_label.pack(side="left", padx=5)

        # --- Sync Log Section ---
        log_frame_key = "device_sync_log_frame_title"
        log_frame = ttkb.LabelFrame(panel_container, text=localization._(log_frame_key), padding="10")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self._add_translatable_widget(log_frame, log_frame_key, attr="title")

        self.sync_log_tree = ttkb.Treeview(log_frame, columns=("timestamp", "status", "message"), show="headings", height=5)
        self._update_zk_log_tree_headers() # Set initial headers

        self.sync_log_tree.column("timestamp", width=150, anchor="w")
        self.sync_log_tree.column("status", width=80, anchor="w")
        self.sync_log_tree.column("message", width=400, stretch=tk.YES)

        log_scrollbar = ttkb.Scrollbar(log_frame, orient="vertical", command=self.sync_log_tree.yview)
        self.sync_log_tree.configure(yscrollcommand=log_scrollbar.set)
        
        self.sync_log_tree.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        self._update_sync_status_display() # Initial update

    def _add_translatable_widget(self, widget, key, attr="text"):
        self.translatable_widgets_zk.append({"widget": widget, "key": key, "attr": attr})

    def _update_zk_log_tree_headers(self):
        if hasattr(self, 'sync_log_tree') and self.sync_log_tree.winfo_exists():
            self.sync_log_tree.heading("timestamp", text=localization._("zk_log_header_timestamp")) # Add key
            self.sync_log_tree.heading("status", text=localization._("zk_log_header_status")) # Add key
            self.sync_log_tree.heading("message", text=localization._("zk_log_header_details")) # Add key

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("zkteco_management_window_title"))
        self._update_zk_log_tree_headers()
        # Update default name var if it's a key
        self.device_name_var.set(localization._("zk_device_default_name"))
        # Update status vars if their initial values are keys
        if self.last_sync_var.get() == localization._("status_not_available_short", prev_lang=True): # Check if it was the placeholder
            self.last_sync_var.set(localization._("status_not_available_short"))
        if self.device_status_var.get() == localization._("zk_status_unknown", prev_lang=True):
            self.device_status_var.set(localization._("zk_status_unknown"))
        if self.sync_message_var.get() == localization._("status_ready", prev_lang=True):
            self.sync_message_var.set(localization._("status_ready"))

        for item in self.translatable_widgets_zk:
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

    # --- Placeholder methods for ZKTeco functionality ---
    # You will copy the content of _gui_test_zk_connection, gui_sync_from_zkteco, etc.
    # from HRAppGUI into these methods, adjusting 'self' references.

    def _gui_test_zk_connection(self):
        ip = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_IP, config.ZKTECO_DEVICE_IP)
        port_str = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_PORT, str(config.ZKTECO_DEVICE_PORT))
        try: port = int(port_str)
        except ValueError:
            messagebox.showerror("Config Error", f"Invalid ZKTeco port: {port_str}", parent=self); return

        if hasattr(self, 'resync_btn'): self.resync_btn.config(state="disabled")
        if hasattr(self, 'test_conn_btn'): self.test_conn_btn.config(state="disabled")
        if hasattr(self, 'sync_progressbar'): self.sync_progressbar.start()
        self.config(cursor="watch") # Use self for Toplevel
        self._update_sync_status_display(message="Testing connection...")

        thread = threading.Thread(target=self._perform_zk_test_connection_threaded, args=(ip, port, self.task_queue))
        thread.daemon = True
        thread.start()
        self._check_zk_sync_status() # Start polling
    def gui_sync_from_zkteco(self):
        # Use IP and Port from config.py
        ip = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_IP, config.ZKTECO_DEVICE_IP)
        port_str = db_schema.get_app_setting_db(db_schema.SETTING_ZKTECO_DEVICE_PORT, str(config.ZKTECO_DEVICE_PORT))
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Configuration Error", 
                                 f"Invalid ZKTeco port configured in settings: '{port_str}'. Please correct it in App Settings.", parent=self)
            return

        if not ip or ip == "192.168.1.201" or not port: # Check for default/missing config
            messagebox.showwarning("ZKTeco Sync", 
                                   f"ZKTeco device IP/Port not configured or using default placeholder.\n"
                                   f"Current IP: {ip}, Port: {port}\n"
                                   "Please configure in settings.ini or via Application Settings if available.",
                                   parent=self)
            return

        if hasattr(self, 'resync_btn'): self.resync_btn.config(state="disabled")
        if hasattr(self, 'test_conn_btn'): self.test_conn_btn.config(state="disabled")
        if hasattr(self, 'sync_progressbar'): self.sync_progressbar.start() # For indeterminate mode
        self.config(cursor="watch") # Use self for Toplevel
        self.sync_message_var.set("Attempting to sync from ZKTeco device... Please wait.") # Use local sync_message_var
        self.update_idletasks() # Use self for Toplevel

        # Start the sync in a new thread
        # Pass self.task_queue to the threaded function
        thread = threading.Thread(target=self._perform_zk_sync_threaded, args=(ip, port, self.task_queue), daemon=True)
        thread.daemon = True # So it exits when main app exits
        thread.start()

        # Start polling the queue for completion
        self._check_zk_sync_status()
        # --- New View Creation Methods (Placeholders or actual UI setup) ---
        # These methods are called once by _setup_main_ui to build the content of each tab.
    
    def _perform_zk_test_connection_threaded(self, ip: str, port: int, q_comm: queue.Queue):
        """Worker function to test ZKTeco connection in a separate thread."""
        conn_test = None
        try: # Use the utility function
            conn_test = zkteco_utils.connect_to_zkteco_device(ip, port, timeout=5) # Use a short timeout for test
            # conn_test = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False) # Old direct call
            conn_test.connect()
            device_time = conn_test.get_time() # Simple command to test
            q_comm.put({"type": "test_connection", "success": True, "message": f"Successfully connected. Device time: {device_time}"})
        except Exception as e:
            q_comm.put({"type": "test_connection", "success": False, "message": f"Connection failed: {e}"})
        finally:
            if conn_test and conn_test.is_connect:
                zkteco_utils.disconnect_from_zkteco_device(conn_test) # Use utility

    def _check_zk_sync_status(self): pass
    def _update_sync_status_display(self, status: Optional[str] = None, last_sync_time: Optional[str] = None, message: Optional[str] = None): pass
    
    def _create_device_sync_section(self, parent_frame):
        """Creates the UI for the Device Sync tab."""
        # Main container frame for the panel
        panel_container = ttk.Frame(parent_frame, padding="15")
        panel_container.pack(expand=True, fill="both")

        # Device Info Section
        info_frame_key = "device_sync_info_frame_title" # Key needed
        info_frame = ttk.LabelFrame(panel_container, text=_(info_frame_key), padding="10")
        info_frame.pack(fill="x", pady=(0, 10))
        info_frame.columnconfigure(1, weight=1) # Make value column expand
        self._add_translatable_widget(info_frame, info_frame_key)

        row_idx = 0
        assoc_device_lbl_key = "device_sync_assoc_device_label" # Key needed
        assoc_device_lbl = ttk.Label(info_frame, text=_(assoc_device_lbl_key))
        assoc_device_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(assoc_device_lbl, assoc_device_lbl_key)
        ttk.Label(info_frame, textvariable=self.device_name_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        last_sync_lbl_key = "device_sync_last_sync_label" # Key needed
        last_sync_lbl = ttk.Label(info_frame, text=_(last_sync_lbl_key))
        last_sync_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(last_sync_lbl, last_sync_lbl_key)
        ttk.Label(info_frame, textvariable=self.last_sync_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        status_lbl_key = "device_sync_status_label" # Key needed
        status_lbl = ttk.Label(info_frame, text=_(status_lbl_key))
        status_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget(status_lbl, status_lbl_key)
        ttk.Label(info_frame, textvariable=self.device_status_var).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Action Buttons
        actions_frame = ttk.Frame(info_frame)
        actions_frame.grid(row=row_idx, column=0, columnspan=2, pady=10, sticky="ew")

        test_conn_btn_key = "device_sync_test_conn_btn" # Key needed
        self.test_conn_btn = ttk.Button(actions_frame, text=_(test_conn_btn_key), command=self._gui_test_zk_connection, bootstyle=BS_VIEW_EDIT)
        self.test_conn_btn.pack(side="left", padx=5)

        self._add_translatable_widget(self.test_conn_btn, test_conn_btn_key)

        resync_btn_key = "device_sync_resync_btn" # Key needed
        self.resync_btn = ttk.Button(actions_frame, text=_(resync_btn_key), command=self.gui_sync_from_zkteco, bootstyle=BS_ADD)
        ToolTip(self.resync_btn, text="Fetch new attendance logs from the ZKTeco device.")
        self.resync_btn.pack(side="left", padx=5)
        self._add_translatable_widget(self.resync_btn, resync_btn_key)


        # Auto Sync Toggle (Placeholder functionality)
        auto_sync_key = "device_sync_auto_sync_toggle" # Key needed
        self.toggle_auto_sync_btn = ttk.Checkbutton(actions_frame, text=_(auto_sync_key), variable=self.auto_sync_enabled_var, bootstyle="round-toggle", command=self._gui_toggle_auto_sync)
        self.toggle_auto_sync_btn.pack(side="left", padx=15)
        self._add_translatable_widget(self.toggle_auto_sync_btn, auto_sync_key)

        # Progress and Status Messages
        progress_status_frame = ttk.Frame(panel_container)
        progress_status_frame.pack(fill="x", pady=5)

        self.sync_progressbar = ttk.Progressbar(progress_status_frame, mode="determinate", length=300) # Or 'indeterminate'
        self.sync_progressbar.pack(side="left", padx=5, expand=True, fill="x")
        
        self.sync_message_label = ttk.Label(progress_status_frame, textvariable=self.sync_message_var, width=40, anchor="w") # Fixed width for status
        self.sync_message_label.pack(side="left", padx=5)

        # Sync Log Section
        log_frame_key = "device_sync_log_frame_title" # Key needed
        log_frame = ttk.LabelFrame(panel_container, text=_(log_frame_key), padding="10")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self._add_translatable_widget(log_frame, log_frame_key)


        self.sync_log_tree = ttk.Treeview(log_frame, columns=("timestamp", "status", "message"), show="headings", height=5)
        self.sync_log_tree.heading("timestamp", text="Timestamp")
        self.sync_log_tree.heading("status", text="Status")
        self.sync_log_tree.heading("message", text="Details")

        self.sync_log_tree.column("timestamp", width=150, anchor="w")
        self.sync_log_tree.column("status", width=80, anchor="w")
        self.sync_log_tree.column("message", width=400, stretch=tk.YES)

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.sync_log_tree.yview)
        self.sync_log_tree.configure(yscrollcommand=log_scrollbar.set)
        
        self.sync_log_tree.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        self._update_sync_status_display() # Initial update
    
    def _gui_toggle_auto_sync(self):
        # Placeholder for auto-sync logic
        if self.auto_sync_enabled_var.get():
            messagebox.showinfo("Auto Sync", "Automatic synchronization enabled (feature pending).", parent=self.root)
            # Here you would typically save this setting and start a scheduler
        else:
            messagebox.showinfo("Auto Sync", "Automatic synchronization disabled.", parent=self.root)
            # Save setting and stop scheduler

    def _update_sync_status_display(self, status: Optional[str] = None, last_sync_time: Optional[str] = None, message: Optional[str] = None):
        """Updates the device sync status labels."""
        if status: self.device_status_var.set(status)
        if last_sync_time: self.last_sync_var.set(last_sync_time)
        if message: self.sync_message_var.set(message)

    def _add_to_sync_log(self, status_icon: str, message: str):
        """Adds an entry to the sync log display, keeping only the last 5."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.sync_log_data.insert(0, (timestamp, status_icon, message))
        if len(self.sync_log_data) > 5:
            self.sync_log_data.pop()

        # Refresh treeview
        for item in self.sync_log_tree.get_children():
            self.sync_log_tree.delete(item)
        # Insert newest at the top of the tree
        for log_entry in self.sync_log_data: 
            self.sync_log_tree.insert("", 0, values=log_entry)