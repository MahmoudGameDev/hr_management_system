# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\chatbot_window.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
import logging
from typing import TYPE_CHECKING
from utils import localization
from ai.chatbot_engine import ChatbotAssistant # Import from new location
from data import database as db_schema # For BS_PRIMARY_ACTION

from ai.chatbot_engine import ChatbotAssistant # Import from its new location
from .themed_toplevel import ThemedToplevel
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global

if TYPE_CHECKING:
    from .application_controller import ApplicationController

logger = logging.getLogger(__name__)

class ChatbotWindow(ThemedToplevel):
    def __init__(self, parent, app_instance: 'ApplicationController'):
        super().__init__(parent, app_instance)
        self.title(localization._("chatbot_window_title"))
        self.geometry("500x700")
        self.assistant = ChatbotAssistant(app_instance)

        # Conversation display area
        self.conversation_text = tk.Text(self, wrap="word", state="disabled", height=20, relief="solid", borderwidth=1)
        self.conversation_text.pack(padx=10, pady=10, fill="both", expand=True)
        # Apply theme to Text widget
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.conversation_text, palette)

        # Input frame
        input_frame = ttk.Frame(self, padding=(10,0,10,10))
        input_frame.pack(fill="x")

        self.user_input_var = tk.StringVar()
        self.user_input_entry = ttk.Entry(input_frame, textvariable=self.user_input_var, width=50)
        self.user_input_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.user_input_entry.bind("<Return>", self._send_message)
        
        self.send_btn = ttk.Button(input_frame, text=localization._("chatbot_send_btn"), command=self._send_message, bootstyle=db_schema.BS_PRIMARY_ACTION)
        self.send_btn.pack(side="left")

        self._add_message_to_conversation("Assistant", localization._("chatbot_greeting"))
        self.user_input_entry.focus_set()

    def _add_message_to_conversation(self, sender: str, message: str):
        self.conversation_text.config(state="normal")
        self.conversation_text.insert(tk.END, f"{sender}: {message}\n\n")
        self.conversation_text.config(state="disabled")
        self.conversation_text.see(tk.END) # Scroll to the bottom

    def _send_message(self, event=None):
        user_message = self.user_input_var.get().strip()
        if not user_message:
            return

        self._add_message_to_conversation("You", user_message)
        self.user_input_var.set("") # Clear input field

        # Process input and get assistant's response
        assistant_response = self.assistant.process_input(user_message)
        self._add_message_to_conversation("Assistant", assistant_response)

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(localization._("chatbot_window_title"))
        self.send_btn.config(text=localization._("chatbot_send_btn"))
        # Potentially update initial greeting if window is kept open during language change
        # For simplicity, we assume it's re-opened or initial greeting is fine.