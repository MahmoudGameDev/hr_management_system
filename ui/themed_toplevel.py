# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\themed_toplevel.py
import tkinter as tk
import ttkbootstrap as ttkb
import logging
from typing import Optional, TYPE_CHECKING, Callable, Any # Import TYPE_CHECKING, Callable, and Any

# Project-specific imports - adjust paths based on the new structure
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global, _theme_widget_recursively_global

logger = logging.getLogger(__name__)


# --- Base Themed Toplevel Window ---
class ThemedToplevel(tk.Toplevel):
    def __init__(self, parent, app_instance, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        print(f"DEBUG: ThemedToplevel: Initializing {self.__class__.__name__}")

        self.parent_app = app_instance # This should be the ApplicationController instance
        self.withdraw() # Withdraw initially to prevent flicker
        self.transient(parent)
        self.translatable_widgets: list = [] # Initialize list for translatable widgets
        self.active_theme = self.parent_app.get_current_theme() if self.parent_app else "litera"
        self._after_ids = {} # Store general after IDs: {'job_name': after_id}
        self.after_id_deferred_theme = None # Specifically for _deferred_theme_update
        self._direct_after_ids = set() # Store IDs of 'after' jobs scheduled directly on this instance

        # self.grab_set() # Moved to _deferred_theme_update
        
        # The WM_DELETE_WINDOW protocol will now be set by ApplicationController._create_and_show_toplevel
        # self.protocol("WM_DELETE_WINDOW", self._custom_close_handler_themed_toplevel) 

        # self.lift()      # Moved to _deferred_theme_update
        # Ensure the window and its initial children are processed by Tkinter
        # before scheduling further theme updates.
        # self.update_idletasks() # Process geometry changes - will be done in deferred
        self.protocol("WM_DELETE_WINDOW", self._custom_close_handler_themed_toplevel) # Renamed for clarity
        # Defer the local theme update to allow all child widgets to be fully created
        print(f"DEBUG: ThemedToplevel: Scheduling _deferred_theme_update for {self.__class__.__name__}")
        self.after_id_deferred_theme = self.after(50, self._deferred_theme_update) # Store ID

    def _schedule_after(self, job_name: str, ms: int, callback):
        """Schedules an 'after' job and stores its ID for cancellation."""
        # Cancel previous job with the same name if it exists
        if job_name in self._after_ids and self._after_ids[job_name]:
            try:
                self.after_cancel(self._after_ids[job_name])
            except tk.TclError: # Might already be cancelled or invalid
                pass
        new_id = self.after(ms, callback)
        self._after_ids[job_name] = new_id
        logger.debug(f"Scheduled 'after' job '{job_name}' with ID {new_id} for {self.__class__.__name__}")
        return new_id

    def _deferred_theme_update(self):
        print(f"DEBUG: ThemedToplevel: Executing _deferred_theme_update for {self.__class__.__name__}")
        if self.winfo_exists():
            try:
                # self.update_idletasks() # Subclass (e.g., LoginWindow) should have handled its own geometry and update_idletasks - KEEP COMMENTED
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling update_local_theme_elements.")
                self.update_local_theme_elements() # Now apply custom theme elements - RE-ENABLED
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling lift()")
                self.lift()      # Bring to front
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling deiconify()")
                self.deiconify() # Make visible
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): AFTER deiconify(). Is visible: {self.winfo_viewable()}")
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling self.update() to force drawing.")
                self.update() # Force window to draw and process geometry
                # self.center_on_parent() # If you have this method, call after deiconify and size is known
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling grab_set()")
                self.grab_set() # Make it modal now, after deiconify and update
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Calling focus_force()")
                self.focus_force() # Ensure focus
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): _deferred_theme_update completed. Window should be visible.")
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Geometry after deiconify: {self.geometry()}")
            except Exception as e: # pragma: no cover
                logger.error(f"Error in _deferred_theme_update for {self.__class__.__name__}: {e}", exc_info=True)
                print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): EXCEPTION in _deferred_theme_update: {e}")
        else: # pragma: no cover
            logger.warning(f"ThemedToplevel ({self.__class__.__name__}): Window no longer exists in _deferred_theme_update.")
            print(f"DEBUG: ThemedToplevel ({self.__class__.__name__}): Window no longer exists in _deferred_theme_update.")

    def update_local_theme_elements(self):
        """Applies theme to the Toplevel window and its non-ttk children. Gets theme from the main app controller."""
        theme_to_apply = "light" # Default
        # Determine theme based on parent_app (which should be ApplicationController)
        if self.parent_app:
            if hasattr(self.parent_app, 'get_current_theme'): # Check if parent_app is ApplicationController
                theme_to_apply = self.parent_app.get_current_theme()
            # Fallback for older pattern where HRAppGUI might be passed, though ApplicationController is preferred
            elif hasattr(self.parent_app, 'current_theme'): # This might be HRAppGUI instance
                 theme_to_apply = self.parent_app.current_theme

        palette = get_theme_palette_global(theme_to_apply)
        if self.winfo_exists():
            self.config(bg=palette['bg_main'])
            # Theme non-ttk widgets recursively (e.g., tk.Text, tk.Canvas)
            _theme_widget_recursively_global(self, palette, _theme_text_widget_global)

    def after(self, ms, func=None, *args):
        """Override tkinter.Misc.after to track job IDs scheduled directly on this instance."""
        if not self.winfo_exists():
            logger.warning(f"Attempted to call 'after' on a destroyed ThemedToplevel: {self.title()}")
            return None # Or raise an error
        
        after_id = super().after(ms, func, *args)
        self._direct_after_ids.add(after_id)
        logger.debug(f"ThemedToplevel '{self.title()}' scheduled direct 'after' job {after_id}. Tracked IDs: {self._direct_after_ids}")
        return after_id

    def after_cancel(self, id):
        """Override tkinter.Misc.after_cancel to also untrack."""
        super().after_cancel(id)
        self._direct_after_ids.discard(id) # Remove if it was a direct 'after' job
        
        # For _after_ids (which is a dict: {'job_name': after_id}), find and remove the entry
        # where 'id' is the value (the after_id).
        job_name_to_remove = None
        for name, after_id_val in self._after_ids.items():
            if after_id_val == id:
                job_name_to_remove = name
                break
        if job_name_to_remove:
            del self._after_ids[job_name_to_remove]
        logger.debug(f"ThemedToplevel '{self.title()}' cancelled 'after' job {id}.")

    def _schedule_after(self, delay_ms: int, callback: Callable, *args):
        """Schedules a callback using 'after' and stores its ID for cancellation."""
        after_id = super().after(delay_ms, callback, *args)
        
    def _cancel_all_after_jobs(self):
        """Cancels all 'after' jobs scheduled by this Toplevel instance."""
        logger.debug(f"Cancelling all 'after' jobs for {self.__class__.__name__} ({self.title() if self.winfo_exists() else 'N/A'})")
        if self.after_id_deferred_theme:
            try:
                self.after_cancel(self.after_id_deferred_theme)
                logger.debug(f"Cancelled _deferred_theme_update (ID: {self.after_id_deferred_theme}) for {self.__class__.__name__}")
                self.after_id_deferred_theme = None
            except tk.TclError: pass # May already be invalid

        for job_name, after_id in list(self._after_ids.items()): # Iterate over a copy
            if after_id:
                try:
                    self.after_cancel(after_id)
                    logger.debug(f"Cancelled job '{job_name}' (ID: {after_id}) for {self.__class__.__name__}")
                except tk.TclError: # Might already be cancelled or invalid
                    pass
        self._direct_after_ids.clear()

    def _custom_close_handler_themed_toplevel(self):
        """Handles the closing of the Toplevel window."""
        self._cancel_all_after_jobs() # Cancel jobs before calling parent's handler or destroying
        
        # Delegate to ApplicationController's handler if it exists
        if self.parent_app and hasattr(self.parent_app, '_handle_toplevel_close'):
            # This handler is a fallback. The ApplicationController should ideally set a more specific
            # WM_DELETE_WINDOW protocol that calls its _handle_toplevel_close with the correct tracker_name.
            # If this method is called, it means the controller's specific protocol might not have been set
            # or was overridden. We attempt to find the tracker name. # Corrected comment
            tracker_name_for_this_window = None
            if hasattr(self.parent_app, 'active_windows'):
                for name, window_instance_tracked in self.parent_app.active_windows.items():
                    if window_instance_tracked == self:
                        tracker_name_for_this_window = name
                        break
            logger.debug(f"ThemedToplevel '{self.title()}' custom_close_handler invoking parent_app._handle_toplevel_close. Tracker: {tracker_name_for_this_window}")
            # Call the controller's method. If tracker_name_for_this_window is None,
            # the controller's handler will still attempt to manage based on instance.
            self.parent_app._handle_toplevel_close(self, tracker_name_for_this_window)
        else:
            logger.warning(f"Could not call _on_toplevel_close for {self.title()}. Destroying directly.")
            self.destroy()

    def _add_translatable_widget(self, widget, key: str, attr: str = "text",
                                 is_title: bool = False, is_menu: bool = False,
                                 menu_index: Optional[int] = None,
                                 is_notebook_tab: bool = False, tab_id: Optional[Any] = None):
        """Registers a widget and its translation details."""
        self.translatable_widgets.append({
            "widget": widget, "key": key, "attr": attr,
            "is_title": is_title, "is_menu": is_menu, "menu_index": menu_index,
            "is_notebook_tab": is_notebook_tab, "tab_id": tab_id
        })

    def refresh_ui_for_language(self): # pragma: no cover
        """Updates text of registered translatable widgets in this Toplevel."""
        logger.debug(f"Refreshing UI for language in {self.__class__.__name__} ({self.title()})")
        # Update window title if it's managed via a key (subclasses might override this)
        if hasattr(self, 'title_key') and self.title_key:
             self.title(localization._(self.title_key))

        for item_info in self.translatable_widgets:
            widget = item_info["widget"]
            key = item_info["key"]
            attr = item_info["attr"]
            if widget.winfo_exists():
                try:
                    if item_info.get("is_notebook_tab") and isinstance(widget, ttk.Notebook) and item_info.get("tab_id"):
                        widget.tab(item_info["tab_id"], text=localization._(key))
                    elif attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title" and isinstance(widget, ttk.LabelFrame): # LabelFrame uses 'text' for title
                        widget.config(text=localization._(key))
                except tk.TclError as e:
                    logger.warning(f"TclError updating widget for key '{key}' in {self.title()}: {e}")
                except Exception as e_gen:
                    logger.error(f"General error updating widget for key '{key}' in {self.title()}: {e_gen}")

    def destroy(self):
        """Overrides Toplevel.destroy to ensure custom cleanup."""
        logger.debug(f"Destroying ThemedToplevel: {self.title() if self.winfo_exists() else 'N/A'}")
        self._cancel_all_after_jobs() # Ensure all after jobs are cancelled
        super().destroy()