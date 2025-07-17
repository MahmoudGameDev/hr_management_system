# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\themed_tk_window.py
import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import logging

from utils import localization # For _()
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global, _theme_widget_recursively_global
import config

logger = logging.getLogger(__name__)

class ThemedTkWindow(ttkb.Window):
    """
    A base class for the main application window that handles theme application
    and language updates for its direct children and specific registered widgets.
    """
    def __init__(self, themename=None, parent_app=None, *args, **kwargs):
        # Determine initial theme
        initial_theme = themename if themename else config.DEFAULT_THEME
        try:
            super().__init__(themename=initial_theme, *args, **kwargs)
        except tk.TclError: # Fallback if theme is invalid
            logger.warning(f"Theme '{initial_theme}' not found. Falling back to a default ttkbootstrap theme.")
            super().__init__(themename="litera", *args, **kwargs) # Or another safe default

        self.parent_app = parent_app # Should be ApplicationController instance
        self.current_theme = self.style.theme_name() # Get the actual theme applied
        self.translatable_widgets = [] # For registering widgets that need language updates

        # Defer initial full theme application to ensure all widgets are created
        self.after(100, self._deferred_initial_theme_application)

    def _deferred_initial_theme_application(self):
        if self.winfo_exists():
            self.apply_instance_theme() # Apply custom theming to non-ttk widgets
            if hasattr(self, 'refresh_ui_for_language'): # If the subclass has this method
                self.refresh_ui_for_language()

    def _add_translatable_widget(self, widget, key, attr="text"):
        """Registers a widget and its text key for language updates."""
        self.translatable_widgets.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self): # pragma: no cover
        """Updates text of registered translatable widgets."""
        logger.debug(f"Refreshing UI for language in {self.__class__.__name__}")
        if hasattr(self, 'title_key') and self.title_key: # For main window title
             self.title(localization._(self.title_key))

        for item in self.translatable_widgets:
            widget = item["widget"]
            key = item["key"]
            attr = item["attr"]
            if widget.winfo_exists():
                try:
                    if attr == "text":
                        widget.config(text=localization._(key))
                    elif attr == "title": # For things like LabelFrame
                         widget.config(text=localization._(key))
                    # Add more attributes as needed (e.g., for menu items)
                except tk.TclError as e:
                    logger.warning(f"TclError updating widget for key '{key}': {e}")
                except Exception as e:
                    logger.error(f"Error updating widget for key '{key}': {e}")

    def apply_instance_theme(self):
        """
        Applies the current logical theme (e.g., "light" or "dark") to this
        window instance's background and its non-ttk child widgets.
        The actual ttkbootstrap theme (e.g., "cosmo", "darkly") is managed separately.
        """
        palette = get_theme_palette_global(self.current_theme)
        if self.winfo_exists():
            self.config(bg=palette['bg_main'])
            _theme_widget_recursively_global(self, palette, _theme_text_widget_global)