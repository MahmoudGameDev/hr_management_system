# c:\Users\mahmo\OneDrive\Documents\ai\HR\version\utils\theming_utils.py
import logging
import tkinter as tk # Required for winfo_exists, etc.
from typing import Optional, Any # Added Optional and Any

logger = logging.getLogger(__name__)

HRAppGUI_static_themes = {
    "light": {
        "bg_main": "#EAEAEA", "bg_secondary": "#FFFFFF", "fg_primary": "#000000",
        "fg_secondary": "#333333", "button_bg": "#E1E1E1", "button_fg": "#000000",
        "button_active_bg": "#C0C0C0", "entry_bg": "#FFFFFF", "entry_fg": "#000000",
        "tree_bg": "#FFFFFF", "tree_fg": "#000000", "tree_selected_bg": "#3399FF",
        "tree_selected_fg": "#FFFFFF", "tree_heading_bg": "#D5D5D5",
        "tree_heading_fg": "#000000", "disabled_fg": "#A0A0A0",
    },
    "dark": {
        "bg_main": "#2E2E2E", "bg_secondary": "#3C3C3C", "fg_primary": "#E0E0E0",
        "fg_secondary": "#B0B0B0", "button_bg": "#555555", "button_fg": "#FFFFFF",
        "button_active_bg": "#6A6A6A", "entry_bg": "#4F4F4F", "entry_fg": "#FFFFFF",
        "tree_bg": "#333333", "tree_fg": "#D0D0D0", "tree_selected_bg": "#007ACC",
        "tree_selected_fg": "#FFFFFF", "tree_heading_bg": "#5A5A5A",
        "tree_heading_fg": "#FFFFFF", "disabled_fg": "#A0A0A0",
    }
}

def get_theme_palette_global(theme_name="light"):
    return HRAppGUI_static_themes.get(theme_name, HRAppGUI_static_themes["light"])

def _theme_text_widget_global(text_widget, palette):
    """Applies theme to a tk.Text widget."""
    if text_widget.winfo_exists():
        text_widget.config(
            background=palette.get('entry_bg', '#FFFFFF'),
            foreground=palette.get('entry_fg', '#000000'),
            insertbackground=palette.get('entry_fg', '#000000'),
            selectbackground=palette.get('tree_selected_bg', '#0078D7'),
            selectforeground=palette.get('tree_selected_fg', '#FFFFFF'),
            relief="solid",
            borderwidth=1
        )

def _theme_widget_recursively_global(widget, palette, theme_text_widget_func):
    if not widget.winfo_exists(): return
    if widget.winfo_class() == 'Text':
        if theme_text_widget_func: theme_text_widget_func(widget, palette)
    for child in widget.winfo_children():
        try:
            if child.winfo_exists(): _theme_widget_recursively_global(child, palette, theme_text_widget_func)
        except Exception as e: logger.debug(f"Error theming child widget {child}: {e}")
        
def _add_translatable_widget(self, widget, key: str, attr: str = "text", is_title: bool = False, is_menu: bool = False, menu_index: Optional[int] = None, is_notebook_tab: bool = False, tab_id: Optional[Any] = None):
        # This method should add to self.translatable_widgets (the generic list in ThemedToplevel)
        # Subclasses can override this or call super() and then add to their own specific list if needed.
        self.translatable_widgets.append({
            "widget": widget, "key": key, "attr": attr,
            "is_title": is_title, "is_menu": is_menu, "menu_index": menu_index,
            "is_notebook_tab": is_notebook_tab,
            "tab_id": tab_id
        })
def refresh_ui_for_language(self): # pragma: no cover
        # This method should be implemented by each Toplevel window that needs UI translation
        # Example: self.title(_("window_title_key"))
        # Generic refresh for ThemedToplevel itself (e.g., its own title if set via _add_translatable_widget)
        widgets_to_translate = []
        # Determine which list of translatable widgets to use
        # This logic helps if subclasses (like AppSettingsWindow, EmployeeProfileWindow)

  