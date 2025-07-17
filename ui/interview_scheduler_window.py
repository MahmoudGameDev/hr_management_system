# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\interview_scheduler_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, time as dt_time
from data import database as db_schema
from data import queries as db_queries
from utils.localization import _ # Import _ directly
from utils.gui_utils import populate_employee_combobox, extract_id_from_combobox_selection # Added extract_id_from_combobox_selection
from utils.exceptions import DatabaseOperationError, InvalidInputError, EmployeeNotFoundError # Import custom exceptions
# --- Project-specific imports ---
from .themed_toplevel import ThemedToplevel # Assuming this is ui.themed_toplevel
from .components import AutocompleteCombobox # Import from ui.components

logger = logging.getLogger(__name__)

class InterviewSchedulerWindow(ThemedToplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance) # Call super first
        self.title("Interview Scheduling") # Title can be set after super
        self.geometry("950x700")

        # --- Main Paned Window for Layout ---
        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)
        # --- Left Pane: Form for Adding/Editing Interview ---
        form_pane = ttk.Frame(main_paned_window, padding="10") # Define form_pane
        main_paned_window.add(form_pane, weight=1)             # Add it to the paned window
        # Now call the method with the defined form_pane
        
        self._create_interview_form_widgets(form_pane) # Pass form_pane here

        # --- Right Pane: List of Scheduled Interviews ---
        list_pane = ttk.Frame(main_paned_window, padding="10")
        main_paned_window.add(list_pane, weight=2)
        self._create_interview_list_widgets(list_pane)

        self._load_interviews_to_tree() # Initial load
        # Ensure all widgets within this Toplevel are processed by Tkinter
        # before the deferred theme update from ThemedToplevel's __init__ runs.
        self.update_idletasks()

    def _create_interview_form_widgets(self, parent_frame):
        
        form_lf = ttk.LabelFrame(parent_frame, text=_("interview_form_frame_title"), padding="10")
        form_lf.pack(fill="both", expand=True)
        form_lf.columnconfigure(1, weight=1)

        self.interview_form_vars = {}
        row_idx = 0

        # Candidate Name
        cand_lbl = ttk.Label(form_lf, text=_("candidate_name_label")); cand_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(cand_lbl, "candidate_name_label") # TODO: Add helper for this window
        self.interview_form_vars["candidate_name"] = tk.StringVar()
        ttk.Entry(form_lf, textvariable=self.interview_form_vars["candidate_name"], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Interviewer
        interviewer_lbl = ttk.Label(form_lf, text=_("interviewer_label")); interviewer_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(interviewer_lbl, "interviewer_label")
        self.interview_form_vars["interviewer_emp_id"] = tk.StringVar()
        interviewer_combo = AutocompleteCombobox(form_lf, textvariable=self.interview_form_vars["interviewer_emp_id"], width=28)
        populate_employee_combobox(interviewer_combo, db_queries.get_all_employees_db, include_active_only=True)
        interviewer_combo.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Date & Time
        date_lbl = ttk.Label(form_lf, text=_("date_label_format")); date_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(date_lbl, "date_label_format")
        self.interview_date_entry = DateEntry(form_lf, width=12, dateformat='%Y-%m-%d')
        self.interview_date_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        time_lbl = ttk.Label(form_lf, text=_("time_label_format")); time_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(time_lbl, "time_label_format")
        self.interview_time_var = tk.StringVar(value="09:00") # Default time
        # Simple entry for time, could be spinboxes or comboboxes for HH and MM
        ttk.Entry(form_lf, textvariable=self.interview_time_var, width=8).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Duration
        duration_lbl = ttk.Label(form_lf, text=_("duration_minutes_label")); duration_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(duration_lbl, "duration_minutes_label")
        self.interview_form_vars["duration_minutes"] = tk.StringVar(value="60")
        ttk.Spinbox(form_lf, from_=15, to=180, increment=15, textvariable=self.interview_form_vars["duration_minutes"], width=5).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx += 1

        # Location
        location_lbl = ttk.Label(form_lf, text=_("location_label")); location_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(location_lbl, "location_label")
        self.interview_form_vars["location"] = tk.StringVar()
        ttk.Entry(form_lf, textvariable=self.interview_form_vars["location"], width=30).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Status
        status_lbl = ttk.Label(form_lf, text=_("status_label")); status_lbl.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        # self._add_translatable_widget_interview(status_lbl, "status_label")
        self.interview_form_vars["status"] = tk.StringVar(value="Scheduled")
        ttk.Combobox(form_lf, textvariable=self.interview_form_vars["status"], values=db_schema.VALID_INTERVIEW_STATUSES, state="readonly", width=28).grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Notes
        notes_lbl = ttk.Label(form_lf, text=_("notes_label")); notes_lbl.grid(row=row_idx, column=0, sticky="nw", padx=5, pady=3)
        # self._add_translatable_widget_interview(notes_lbl, "notes_label")
        self.interview_notes_text = tk.Text(form_lf, height=4, width=30, relief="solid", borderwidth=1)
        self.interview_notes_text.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
        row_idx += 1

        # Action Buttons
        buttons_frame = ttk.Frame(form_lf)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=15, sticky="e") # pragma: no cover
        self.save_interview_btn = ttk.Button(buttons_frame, text=_("interview_schedule_button"), command=self._gui_save_interview, bootstyle=db_schema.BS_ADD)
   
        self.save_interview_btn.pack(side="right", padx=5)
        self.clear_interview_form_btn = ttk.Button(buttons_frame, text=_("interview_clear_form_button"), command=self._gui_clear_interview_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_interview_form_btn.pack(side="right", padx=5)

        self.current_editing_interview_id = None # To store ID when editing

    def _create_interview_list_widgets(self, parent_frame):
        
        list_lf = ttk.LabelFrame(parent_frame, text=_("interview_list_frame_title"), padding="10")
        list_lf.columnconfigure(0, weight=1)
        list_lf.pack(fill="both", expand=True)

        # TODO: Add filters for date range, interviewer, status here

        self.interview_tree_cols = (db_schema.COL_INT_ID, db_schema.COL_INT_CANDIDATE_NAME, "interviewer_name", db_schema.COL_INT_DATE, db_schema.COL_INT_TIME, db_schema.COL_INT_STATUS, db_schema.COL_INT_LOCATION)
        self.interview_tree = ttk.Treeview(list_lf, columns=self.interview_tree_cols, show="headings")
        
        self.interview_tree.heading(db_schema.COL_INT_ID, text="ID")
        self.interview_tree.heading(db_schema.COL_INT_CANDIDATE_NAME, text="Candidate")
        self.interview_tree.heading("interviewer_name", text="Interviewer")
        self.interview_tree.heading(db_schema.COL_INT_DATE, text="Date")
        self.interview_tree.heading(db_schema.COL_INT_TIME, text="Time")
        self.interview_tree.heading(db_schema.COL_INT_STATUS, text="Status")
        self.interview_tree.heading(db_schema.COL_INT_LOCATION, text="Location")

        self.interview_tree.column(db_schema.COL_INT_ID, width=40, anchor="e", stretch=tk.NO)
        self.interview_tree.column(db_schema.COL_INT_CANDIDATE_NAME, width=150)
        self.interview_tree.column("interviewer_name", width=150)
        self.interview_tree.column(db_schema.COL_INT_DATE, width=90, anchor="center")
        self.interview_tree.column(db_schema.COL_INT_TIME, width=70, anchor="center")
        self.interview_tree.column(db_schema.COL_INT_STATUS, width=100, anchor="center")
        self.interview_tree.column(db_schema.COL_INT_LOCATION, width=120, stretch=tk.YES)

        scrollbar_y = ttk.Scrollbar(list_lf, orient="vertical", command=self.interview_tree.yview)
        self.interview_tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_x = ttk.Scrollbar(list_lf, orient="horizontal", command=self.interview_tree.xview)
        self.interview_tree.configure(xscrollcommand=scrollbar_x.set)

        self.interview_tree.pack(side="top", fill="both", expand=True) # Changed from left to top
        scrollbar_y.pack(side="right", fill="y") # Removed 'before=scrollbar_x' which caused error
        scrollbar_x.pack(side="bottom", fill="x")

        self.interview_tree.bind("<<TreeviewSelect>>", self._gui_on_interview_select)
        # TODO: Add buttons for Edit Selected, Cancel Selected below the tree

    def _load_interviews_to_tree(self):
        for item in self.interview_tree.get_children():
            self.interview_tree.delete(item)
        try:
            # TODO: Use filters when implemented
            interviews = db_queries.get_interviews_db()
            for interview in interviews:
                self.interview_tree.insert("", "end", iid=interview[db_schema.COL_INT_ID], values=(
                    interview[db_schema.COL_INT_ID],
                    interview[db_schema.COL_INT_CANDIDATE_NAME],
                    interview.get("interviewer_name", "N/A"), # From JOIN
                    interview[db_schema.COL_INT_DATE],
                    interview[db_schema.COL_INT_TIME],
                    interview[db_schema.COL_INT_STATUS],
                    interview.get(db_schema.COL_INT_LOCATION, "")
                ))
        except DatabaseOperationError as e: # Corrected exception
            messagebox.showerror("Error", f"Could not load interviews: {e}", parent=self)

    def _gui_save_interview(self):
        # Collect data from form
        candidate_name = self.interview_form_vars["candidate_name"].get().strip()
        interviewer_selection = self.interview_form_vars["interviewer_emp_id"].get()
        interviewer_emp_id = extract_id_from_combobox_selection(interviewer_selection)
        interview_date_str = self.interview_date_entry.entry.get()
        interview_time_str = self.interview_time_var.get().strip()
        duration_minutes_str = self.interview_form_vars["duration_minutes"].get()
        location = self.interview_form_vars["location"].get().strip()
        status = self.interview_form_vars["status"].get()
        notes = self.interview_notes_text.get("1.0", tk.END).strip()

        if not interviewer_emp_id:
            messagebox.showerror("Input Error", "Interviewer is required.", parent=self)
            return
        try:
            duration_minutes = int(duration_minutes_str)
            # TODO: Add more validation for time format HH:MM
            
            # For now, only adding is implemented. Edit mode would use self.current_editing_interview_id
            db_queries.add_interview_db(candidate_name, interviewer_emp_id, interview_date_str, interview_time_str, # type: ignore
                             duration_minutes, location, notes, status) # type: ignore
            messagebox.showinfo(_("success_title"), _("interview_scheduled_success_message"), parent=self)
            self._load_interviews_to_tree()
            self._gui_clear_interview_form()
        except (InvalidInputError, EmployeeNotFoundError, DatabaseOperationError) as e: # Corrected exceptions
            messagebox.showerror(_("scheduling_error_title"), str(e), parent=self)
        except ValueError:
            messagebox.showerror(_("input_error_title"), _("invalid_duration_must_be_number_error"), parent=self)
        except Exception as e_generic:
            logger.error(f"Unexpected error saving interview: {e_generic}", exc_info=True)
            messagebox.showerror(_("error_title"), _("unexpected_error_occurred_message", error=e_generic), parent=self)

    def _gui_clear_interview_form(self):
        for key, var in self.interview_form_vars.items():
            var.set("")
        self.interview_date_entry.date = datetime.now().date() # Reset date
        self.interview_time_var.set("09:00")
        if "duration_minutes" in self.interview_form_vars: self.interview_form_vars["duration_minutes"].set("60")
        self.interview_form_vars["status"].set("Scheduled")
        if hasattr(self, 'interview_notes_text'): self.interview_notes_text.delete("1.0", tk.END)
        self.current_editing_interview_id = None
        if hasattr(self, 'save_interview_btn'): self.save_interview_btn.config(text=_("interview_schedule_button")) # Reset button text

    def refresh_ui_for_language(self): # pragma: no cover
        self.title(_("Interview Scheduling")) # Example key
        # Update LabelFrame titles
        if hasattr(self, 'form_lf') and self.form_lf.winfo_exists(): self.form_lf.config(text=_("interview_form_frame_title"))
        if hasattr(self, 'list_lf') and self.list_lf.winfo_exists(): self.list_lf.config(text=_("interview_list_frame_title"))
        # Update labels in form
        # This requires storing references or iterating through children, which is less robust.
        # Assuming labels were created with _() directly, they might update if parent is refreshed.
        # For explicit updates:
        # self.candidate_name_label.config(text=_("candidate_name_label"))
        # ... and so on for other labels in _create_interview_form_widgets
        # Update button texts
        if hasattr(self, 'save_interview_btn') and self.save_interview_btn.winfo_exists():
            self.save_interview_btn.config(text=_("interview_schedule_button")) # Or "Update Interview" if in edit mode
        if hasattr(self, 'clear_interview_form_btn') and self.clear_interview_form_btn.winfo_exists():
            self.clear_interview_form_btn.config(text=_("interview_clear_form_button"))
        # Update Treeview headers
        # self.interview_tree.heading(COL_INT_ID, text=_("id_header")) ...
 

    def _gui_on_interview_select(self, event=None):
        # Placeholder: Load selected interview into form for editing
        # For now, just logs selection.
        selected_item = self.interview_tree.focus()
        if selected_item:
            logger.info(f"Interview selected: {self.interview_tree.item(selected_item, 'values')}")
            # TODO: Populate form for editing, change save button text to "Update Interview"
            # self.current_editing_interview_id = int(selected_item)