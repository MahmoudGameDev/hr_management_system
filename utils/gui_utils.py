# c:\Users\mahmo\OneDrive\Documents\ai\HR\version\utils\gui_utils.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any, Callable, Union, TYPE_CHECKING

# Project-specific imports
from data import queries as db_queries # Assuming queries.py is in data directory
from data import database as db_schema # For constants
from utils.localization import _ # For CustomDialog button text
from ui.themed_toplevel import ThemedToplevel # Import ThemedToplevel at module level

# Assuming AutocompleteCombobox is in ui.components
# This try-except block handles potential circular imports during type checking
# or if AutocompleteCombobox is not yet defined when this module is first imported.
if TYPE_CHECKING:
    from ui.components import AutocompleteCombobox # type: ignore

try:
    from ui.components import AutocompleteCombobox # type: ignore
except ImportError:
    # Define a dummy class or handle gracefully if ui.components is not ready
    # This allows the module to be imported even if AutocompleteCombobox isn't fully available yet,
    # especially during initial setup or if there are complex import orders.
    class AutocompleteCombobox(ttk.Combobox): # type: ignore
        def set_completion_list(self, completion_list: List[str]): # pragma: no cover
            self['values'] = completion_list
        pass

def extract_id_from_combobox_selection(selection_string: Optional[str]) -> Optional[str]:
    """
    Extracts an ID from a string formatted as 'Name (ID)'.
    Returns the ID string or None if extraction fails.
    """
    if selection_string and "(" in selection_string and ")" in selection_string:
        try:
            # Extract the content within the last parentheses
            return selection_string.rsplit('(', 1)[-1].rsplit(')', 1)[0]
        except IndexError: # pragma: no cover
            return None
    return None

def populate_employee_combobox(
    combobox_widget: Union[ttk.Combobox, 'AutocompleteCombobox'],
    employee_list_func: Callable[[], List[Dict]],
    include_active_only: bool = True,
    default_to_first: bool = False,
    empty_option_text: Optional[str] = None,
    combo_width: Optional[int] = None
):
    """
    Populates a ttk.Combobox with employee names and IDs.

    Args:
        combobox_widget: The ttk.Combobox or AutocompleteCombobox widget to populate.
        employee_list_func: A callable that returns a list of employee dictionaries.
        include_active_only: If True, only active employees are listed.
        default_to_first: If True and list is not empty, selects the first actual employee.
        empty_option_text: If provided, adds this as the first (selectable) empty option.
        combo_width: Optional width to set for the combobox.
    """
    try:
        all_employees = employee_list_func()
        employees_to_list = all_employees
        if include_active_only:
            employees_to_list = [emp for emp in all_employees if emp.get(db_schema.COL_EMP_STATUS) == db_schema.STATUS_ACTIVE]

        display_list = []
        if empty_option_text is not None: # Check for None explicitly
            display_list.append(empty_option_text)

        display_list.extend([f"{emp.get(db_schema.COL_EMP_NAME, 'N/A')} ({emp.get(db_schema.COL_EMP_ID, 'N/A')})" for emp in employees_to_list])

        if isinstance(combobox_widget, AutocompleteCombobox):
            combobox_widget.set_completion_list(display_list)
        else:
            combobox_widget['values'] = display_list

        if display_list:
            if default_to_first and empty_option_text is None and employees_to_list:
                combobox_widget.current(0)
            elif default_to_first and empty_option_text is not None and len(display_list) > 1 and employees_to_list:
                combobox_widget.current(1) # Index 1 if empty option is at 0
            elif empty_option_text is not None:
                combobox_widget.current(0) # Default to the empty option
            else: # No default selection, no empty option
                combobox_widget.set('')
        else: # No employees to list
            if isinstance(combobox_widget, AutocompleteCombobox):
                combobox_widget.set_completion_list([])
            else:
                combobox_widget['values'] = []
            combobox_widget.set('')

        if combo_width is not None:
            combobox_widget.config(width=combo_width)

    except Exception as e: # pragma: no cover
        messagebox.showerror("Error", f"Could not load employee list for combobox: {e}", parent=combobox_widget.master if combobox_widget.master else None)
        if isinstance(combobox_widget, AutocompleteCombobox):
            combobox_widget.set_completion_list([])
        else:
            combobox_widget['values'] = []
        combobox_widget.set("Error loading employees")
        combobox_widget.config(state="disabled")


def populate_user_combobox(
    combo_widget: Union[ttk.Combobox, 'AutocompleteCombobox'],
    user_list_getter: Callable[[], List[Dict]], # Function that returns the list of user dicts
    empty_option_text: Optional[str] = None,
    combo_width: Optional[int] = None # Optional width parameter
):
    """
    Populates a combobox with user usernames and IDs in 'Username (ID)' format.
    Args:
        combo_widget: The ttk.Combobox or AutocompleteCombobox widget to populate.
        user_list_getter: A function (or lambda) that returns a list of user dictionaries.
        empty_option_text: Optional text for the first item (e.g., "Select User", "None").
        combo_width: Optional width to set for the combobox.
    """
    try:
        users = user_list_getter()
        user_display_list = [f"{user.get(db_schema.COL_USER_USERNAME, 'N/A')} (ID: {user.get(db_schema.COL_USER_ID, 'N/A')})" for user in users]

        if empty_option_text is not None:
            user_display_list.insert(0, empty_option_text)

        if isinstance(combo_widget, AutocompleteCombobox):
            combo_widget.set_completion_list(user_display_list)
        else:
            combo_widget['values'] = user_display_list

        if empty_option_text is not None:
            combo_widget.set(empty_option_text) # Set default to the empty option
        elif user_display_list:
             combo_widget.set(user_display_list[0]) # Set default to the first user
        else:
            combo_widget.set('')


        if combo_width is not None:
            combo_widget.config(width=combo_width)
    except Exception as e: # pragma: no cover
        messagebox.showerror("Error", f"Could not load user list for combobox: {e}", parent=combo_widget.master if combo_widget.master else None)
        if isinstance(combo_widget, AutocompleteCombobox):
            combo_widget.set_completion_list([])
        else:
            combo_widget['values'] = []
        combo_widget.set("Error loading users")
        combo_widget.config(state="disabled")

def center_toplevel_on_parent(toplevel_window: tk.Toplevel, parent_window: tk.Widget):
    """
    Centers a Toplevel window on its parent window.

    Args:
        toplevel_window (tk.Toplevel): The Toplevel window to center.
        parent_window (tk.Widget): The parent window (usually root or another Toplevel).
    """
    toplevel_window.update_idletasks() # Ensure window size is calculated

    # Get parent window geometry
    parent_x = parent_window.winfo_x()
    parent_y = parent_window.winfo_y()
    parent_width = parent_window.winfo_width()
    parent_height = parent_window.winfo_height()

    # Get Toplevel window size
    window_width = toplevel_window.winfo_width()
    window_height = toplevel_window.winfo_height()

    # Calculate position
    position_x = parent_x + (parent_width // 2) - (window_width // 2)
    position_y = parent_y + (parent_height // 2) - (window_height // 2)

    toplevel_window.geometry(f"+{position_x}+{position_y}")

def populate_department_combobox(
    combobox_widget: Union[ttk.Combobox, 'AutocompleteCombobox'],
    include_empty: bool = True,
    default_to_first: bool = False,
    empty_option_text: Optional[str] = None
):
    """Populates a combobox with department names."""
    try:
        departments = db_queries.list_departments_db()
        dept_names = [dept[db_schema.COL_DEPT_NAME] for dept in departments]

        options = []
        if include_empty:
            options.append(empty_option_text if empty_option_text is not None else "")
        options.extend(dept_names)

        if isinstance(combobox_widget, AutocompleteCombobox):
            combobox_widget.set_completion_list(options)
        else:
            combobox_widget['values'] = options

        if default_to_first and dept_names:
            combobox_widget.set(dept_names[0])
        elif include_empty:
            combobox_widget.set(empty_option_text if empty_option_text is not None else "")
        else:
            combobox_widget.set('')
    except Exception as e: # pragma: no cover
        messagebox.showerror("Error", f"Could not load departments: {e}", parent=combobox_widget.master if combobox_widget.master else None)
        if isinstance(combobox_widget, AutocompleteCombobox): combobox_widget.set_completion_list([])
        else: combobox_widget['values'] = []
        combobox_widget.set("Error loading")
        
def setup_treeview_columns(treeview: ttk.Treeview, column_config: Dict[str, Dict[str, Any]]):
    """
    Configures the Treeview columns based on a dictionary configuration.

    Args:
        treeview (ttk.Treeview): The Treeview widget to configure.
        column_config (Dict[str, Dict[str, Any]]): Config for columns.
            Example: {"col_id": {"header_key": "translation_key_for_header", "width": 100, "anchor": "e", "stretch": tk.YES}}
                     If "header_key" is missing, col_id.replace("_", " ").title() is used.
    """
    treeview["columns"] = list(column_config.keys())
    for col_id, conf in column_config.items():
        header_text_key = conf.get("header_key")
        header_text = _(header_text_key) if header_text_key else col_id.replace("_", " ").title()
        
        treeview.heading(col_id, text=header_text, anchor=conf.get("anchor", "w"))
        treeview.column(col_id, width=conf.get("width", 100), 
                        stretch=conf.get("stretch", tk.NO), 
                        minwidth=conf.get("minwidth", 40), # Added minwidth
                        anchor=conf.get("anchor", "w"))
        
def clear_treeview(treeview: ttk.Treeview):
    """Clears all items from the given ttk.Treeview."""
    if treeview.winfo_exists(): # Check if widget still exists
        for item in treeview.get_children():
            treeview.delete(item)
            
class CustomDialog(ThemedToplevel): # type: ignore # Inherits from ThemedToplevel
    def __init__(self, parent, app_instance, title, message, buttons_config=None):
        super().__init__(parent, app_instance)
        self.title(title)
        self.result = None

        if buttons_config is None:
            buttons_config = [(_("ok_button_text", default="OK"), "ok")] # Use translation key

        ttk.Label(self, text=message, wraplength=300, justify="center").pack(padx=20, pady=20)
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        for btn_text, btn_val in buttons_config:
            btn = ttk.Button(button_frame, text=btn_text, command=lambda val=btn_val: self._set_result_and_close(val),
                             bootstyle=db_schema.BS_PRIMARY_ACTION if btn_val in ["ok", "yes"] else db_schema.BS_LIGHT)
            btn.pack(side="left", padx=10)
        self.transient(parent); self.grab_set(); self.wait_window()

    def _set_result_and_close(self, result_value):
        self.result = result_value
        self.destroy()

class BusyContext:
    """Context manager to show a busy cursor during long operations."""
    def __init__(self, widget):
        self.widget = widget

    def __enter__(self):
        self.widget.config(cursor="watch")
        self.widget.update_idletasks() # Ensure cursor changes immediately

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure widget still exists before trying to change cursor
        # This is important if the widget might be destroyed during the 'with' block
        if self.widget.winfo_exists():
            self.widget.config(cursor="")
        # Do not suppress exceptions, let them propagate
