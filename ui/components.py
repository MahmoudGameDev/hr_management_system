# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\components.py
import tkinter as tk
from tkinter import ttk

class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master=None, completevalues=None, **kwargs):
        super().__init__(master, **kwargs)
        self._completevalues = sorted(list(set(completevalues))) if completevalues else []
        self._hits = []
        self._hit_idx = 0
        self.position = 0
        self.bind("<KeyRelease>", self.handle_keyrelease)
        self['values'] = self._completevalues

    def set_completion_list(self, completion_list):
        """Use this to change the completion list (e.g. after data changes)."""
        self._completevalues = sorted(list(set(completion_list))) if completion_list else []
        self['values'] = self._completevalues # Update the displayed list
        self.set('') # Clear current text

    def autocomplete(self, delta=0):
        """Autocomplete the Combobox."""
        if delta: # E.g., up/down arrow
            self.set(self._hits[self._hit_idx])
            self._hit_idx += delta
            if self._hit_idx < 0:
                self._hit_idx = 0
            elif self._hit_idx >= len(self._hits):
                self._hit_idx = len(self._hits) -1
        else: # Match typed input
            self.position = self.icursor() # Get current cursor position
            current_input = self.get().lower()
            _hits = [item for item in self._completevalues if str(item).lower().startswith(current_input)]
            
            if _hits != self._hits: 
                self._hit_idx = 0 # Reset hit index when hits change
                self._hits = _hits
            
            if self._hits and current_input: # Only show filtered list if there's input and hits
                self['values'] = self._hits 
            else:
                self['values'] = [] if current_input else self._completevalues

    def handle_keyrelease(self, event):
        """Event handler for the keyrelease event."""
        if event.keysym in ["BackSpace", "Delete", "Right", "Left", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Up", "Down", "Tab", "Return", "KP_Enter"]:
            # Let default TCombobox behavior handle navigation and selection from dropdown.
            # For BackSpace/Delete, or when input becomes empty, reset to full list or filter.
            pass # Or specific logic if needed beyond default
        self.autocomplete()