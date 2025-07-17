# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ui\employee_evaluation_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry # Assuming DateEntry is used
import logging
from datetime import datetime, date as dt_date

# --- Project-specific imports ---
from data import database as db_schema # For COL_EVAL_... constants
from data import queries as db_queries # For evaluation DB functions
from utils import localization # For _()
from utils.gui_utils import populate_employee_combobox # If used for evaluator selection
from utils.theming_utils import get_theme_palette_global, _theme_text_widget_global # For theming tk.Text
from .themed_toplevel import ThemedToplevel

logger = logging.getLogger(__name__)

class EmployeeEvaluationWindow(ThemedToplevel):
    def __init__(self, parent, app_instance, employee_id: str):
        super().__init__(parent, app_instance)
        self.employee_id = employee_id
        self.employee_details = db_queries.view_employee_details(employee_id) # Fetch employee details
        
        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id) if self.employee_details else self.employee_id
        self.title(localization._("employee_evaluation_window_title", employee_name=emp_name_display)) # Add key
        self.geometry("800x700") # Adjust as needed
        self.translatable_widgets_eval = []
        self.current_selected_evaluation_id = None
        self.criteria_widgets = {} # To store score entries for each criterion

        # --- Main Paned Window ---
        main_paned_window = ttkb.PanedWindow(self, orient=tk.VERTICAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Top Pane: Evaluation Form ---
        form_pane = ttkb.Frame(main_paned_window, padding="10")
        main_paned_window.add(form_pane, weight=2) # More weight to form
        self._create_evaluation_form_widgets(form_pane)

        # --- Bottom Pane: Evaluation History List ---
        history_pane = ttkb.Frame(main_paned_window, padding="10")
        main_paned_window.add(history_pane, weight=1)
        self._create_evaluation_history_widgets(history_pane)

        self._load_evaluation_history_to_tree() # Initial load

    def _add_translatable_widget_eval(self, widget, key, attr="text"):
        self.translatable_widgets_eval.append({"widget": widget, "key": key, "attr": attr})

    def refresh_ui_for_language(self): # pragma: no cover
        emp_name_display = self.employee_details.get(db_schema.COL_EMP_NAME, self.employee_id) if self.employee_details else self.employee_id
        self.title(localization._("employee_evaluation_window_title", employee_name=emp_name_display))
        
        # Update LabelFrame titles
        if hasattr(self, 'form_lf') and self.form_lf.winfo_exists(): self.form_lf.config(text=localization._("eval_form_frame_title"))
        if hasattr(self, 'history_lf') and self.history_lf.winfo_exists(): self.history_lf.config(text=localization._("eval_history_frame_title"))
        
        # Update static labels in the form
        if hasattr(self, 'eval_period_label') and self.eval_period_label.winfo_exists(): self.eval_period_label.config(text=localization._("eval_period_label"))
        if hasattr(self, 'eval_date_label') and self.eval_date_label.winfo_exists(): self.eval_date_label.config(text=localization._("eval_date_label"))
        if hasattr(self, 'eval_evaluator_label') and self.eval_evaluator_label.winfo_exists(): self.eval_evaluator_label.config(text=localization._("eval_evaluator_label"))
        if hasattr(self, 'eval_comments_label') and self.eval_comments_label.winfo_exists(): self.eval_comments_label.config(text=localization._("eval_comments_label"))
        if hasattr(self, 'eval_overall_score_label') and self.eval_overall_score_label.winfo_exists(): self.eval_overall_score_label.config(text=localization._("eval_overall_score_label_prefix"))

        # Update button texts
        if hasattr(self, 'save_eval_btn') and self.save_eval_btn.winfo_exists(): self.save_eval_btn.config(text=localization._("eval_save_button"))
        if hasattr(self, 'clear_eval_btn') and self.clear_eval_btn.winfo_exists(): self.clear_eval_btn.config(text=localization._("eval_clear_button"))
        
        # Update Treeview headers
        if hasattr(self, 'history_tree') and self.history_tree.winfo_exists():
            self.history_tree.heading(db_schema.COL_EVAL_ID, text=localization._("eval_history_header_id"))
            self.history_tree.heading(db_schema.COL_EVAL_PERIOD, text=localization._("eval_history_header_period"))
            self.history_tree.heading(db_schema.COL_EVAL_DATE, text=localization._("eval_history_header_date"))
            self.history_tree.heading(db_schema.COL_EVAL_TOTAL_SCORE, text=localization._("eval_history_header_total_score"))
            self.history_tree.heading("evaluator_name", text=localization._("eval_history_header_evaluator"))
        
        # Reload criteria to update their labels if they are translatable
        if hasattr(self, 'criteria_frame') and self.criteria_frame.winfo_exists():
            self._populate_criteria_fields(self.criteria_frame)


    def _create_evaluation_form_widgets(self, parent_frame):
        self.form_lf = ttkb.LabelFrame(parent_frame, text=localization._("eval_form_frame_title"), padding="10")
        self.form_lf.pack(fill="both", expand=True)
        self._add_translatable_widget_eval(self.form_lf, "eval_form_frame_title", attr="title")

        # Evaluation Period
        self.eval_period_label = ttk.Label(self.form_lf, text=localization._("eval_period_label"))
        self.eval_period_label.grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_eval(self.eval_period_label, "eval_period_label")
        self.eval_period_var = tk.StringVar()
        self.eval_period_entry = ttkb.Entry(self.form_lf, textvariable=self.eval_period_var, width=30)
        self.eval_period_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Evaluation Date
        self.eval_date_label = ttk.Label(self.form_lf, text=localization._("eval_date_label"))
        self.eval_date_label.grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_eval(self.eval_date_label, "eval_date_label")
        self.eval_date_entry = DateEntry(self.form_lf, width=12, dateformat='%Y-%m-%d')
        self.eval_date_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        self.eval_date_entry.date = dt_date.today()

        # Evaluator (Current User or Selectable)
        self.eval_evaluator_label = ttk.Label(self.form_lf, text=localization._("eval_evaluator_label"))
        self.eval_evaluator_label.grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self._add_translatable_widget_eval(self.eval_evaluator_label, "eval_evaluator_label")
        self.evaluator_var = tk.StringVar()
        # If admin/manager can evaluate on behalf of others, use a combobox
        # For now, assume current user is evaluator
        current_user_id = self.parent_app.get_current_user_id()
        current_username = self.parent_app.get_current_username()
        self.evaluator_id = current_user_id
        self.evaluator_var.set(current_username if current_username else localization._("unknown_user"))
        self.evaluator_display = ttk.Label(self.form_lf, textvariable=self.evaluator_var)
        self.evaluator_display.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        # Criteria Section (Dynamically populated)
        self.criteria_frame = ttkb.LabelFrame(self.form_lf, text=localization._("eval_criteria_section_title"), padding="10")
        self.criteria_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        self._add_translatable_widget_eval(self.criteria_frame, "eval_criteria_section_title", attr="title")
        self._populate_criteria_fields(self.criteria_frame)

        # Overall Score (Calculated)
        self.eval_overall_score_label = ttk.Label(self.form_lf, text=localization._("eval_overall_score_label_prefix"))
        self.eval_overall_score_label.grid(row=4, column=0, sticky="e", padx=5, pady=3)
        self._add_translatable_widget_eval(self.eval_overall_score_label, "eval_overall_score_label_prefix")
        self.overall_score_var = tk.StringVar(value="0")
        self.overall_score_display = ttk.Label(self.form_lf, textvariable=self.overall_score_var, font=("Helvetica", 12, "bold"))
        self.overall_score_display.grid(row=4, column=1, sticky="w", padx=5, pady=3)

        # Comments
        self.eval_comments_label = ttk.Label(self.form_lf, text=localization._("eval_comments_label"))
        self.eval_comments_label.grid(row=5, column=0, sticky="nw", padx=5, pady=3)
        self._add_translatable_widget_eval(self.eval_comments_label, "eval_comments_label")
        self.comments_text = tk.Text(self.form_lf, height=4, width=40, relief="solid", borderwidth=1)
        self.comments_text.grid(row=5, column=1, sticky="ew", padx=5, pady=3)
        palette = get_theme_palette_global(self.parent_app.get_current_theme())
        _theme_text_widget_global(self.comments_text, palette)

        # Action Buttons
        buttons_frame = ttkb.Frame(self.form_lf)
        buttons_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="e")
        
        self.save_eval_btn = ttkb.Button(buttons_frame, text=localization._("eval_save_button"), command=self._gui_save_evaluation, bootstyle=db_schema.BS_ADD)
        self.save_eval_btn.pack(side="left", padx=5)
        self._add_translatable_widget_eval(self.save_eval_btn, "eval_save_button")

        # Add "Record Reward" button, initially disabled
        reward_btn_key = "eval_record_reward_button" # New key
        self.record_reward_btn = ttkb.Button(buttons_frame, text=localization._(reward_btn_key), command=self._gui_record_reward, state="disabled", bootstyle="info")
        self.record_reward_btn.pack(side="left", padx=5)
        self._add_translatable_widget_eval(self.record_reward_btn, reward_btn_key)

        self.clear_eval_btn = ttkb.Button(buttons_frame, text=localization._("eval_clear_button"), command=self._gui_clear_evaluation_form, bootstyle=db_schema.BS_LIGHT)
        self.clear_eval_btn.pack(side="left", padx=5)
        self._add_translatable_widget_eval(self.clear_eval_btn, "eval_clear_button")

    def _populate_criteria_fields(self, parent_frame):
        # Clear existing criteria widgets if any (for language refresh)
        for widget in parent_frame.winfo_children():
            widget.destroy()
        self.criteria_widgets.clear()

        try:
            criteria_list = db_queries.get_all_evaluation_criteria_db()
            if not criteria_list:
                no_criteria_label = ttk.Label(parent_frame, text=localization._("eval_no_criteria_defined_message"))
                no_criteria_label.pack(pady=10)
                self._add_translatable_widget_eval(no_criteria_label, "eval_no_criteria_defined_message")
                return

            row_num = 0
            for criterion in criteria_list:
                crit_id = criterion[db_schema.COL_CRITERIA_ID]
                crit_name = criterion[db_schema.COL_CRITERIA_NAME]
                max_points = criterion[db_schema.COL_CRITERIA_MAX_POINTS]

                label = ttk.Label(parent_frame, text=f"{crit_name} ({localization._('eval_max_points_suffix', points=max_points)}):")
                label.grid(row=row_num, column=0, sticky="w", padx=5, pady=2)
                # No need to add label to translatable_widgets_eval if crit_name is from DB and not a key

                score_var = tk.IntVar(value=0)
                score_spin = ttkb.Spinbox(parent_frame, from_=0, to=max_points, textvariable=score_var, width=5, command=self._calculate_total_score)
                score_spin.grid(row=row_num, column=1, sticky="w", padx=5, pady=2)
                
                self.criteria_widgets[crit_id] = {"var": score_var, "spinbox": score_spin, "max_points": max_points}
                row_num += 1
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("eval_error_loading_criteria", error=e), parent=self)

    def _calculate_total_score(self):
        total_score = 0
        for crit_id, data in self.criteria_widgets.items():
            try:
                total_score += data["var"].get()
            except tk.TclError: # Handle case where var might not be fully initialized or spinbox is empty
                pass
        self.overall_score_var.set(str(total_score))


    def _create_evaluation_history_widgets(self, parent_frame):
        self.history_lf = ttkb.LabelFrame(parent_frame, text=localization._("eval_history_frame_title"), padding="10")
        self.history_lf.pack(fill="both", expand=True)
        self._add_translatable_widget_eval(self.history_lf, "eval_history_frame_title", attr="title")

        cols = (db_schema.COL_EVAL_ID, db_schema.COL_EVAL_PERIOD, db_schema.COL_EVAL_DATE, db_schema.COL_EVAL_TOTAL_SCORE, "evaluator_name")
        self.history_tree = ttkb.Treeview(self.history_lf, columns=cols, show="headings")
        
        self.history_tree.heading(db_schema.COL_EVAL_ID, text=localization._("eval_history_header_id"))
        self.history_tree.heading(db_schema.COL_EVAL_PERIOD, text=localization._("eval_history_header_period"))
        self.history_tree.heading(db_schema.COL_EVAL_DATE, text=localization._("eval_history_header_date"))
        self.history_tree.heading(db_schema.COL_EVAL_TOTAL_SCORE, text=localization._("eval_history_header_total_score"))
        self.history_tree.heading("evaluator_name", text=localization._("eval_history_header_evaluator"))

        self.history_tree.column(db_schema.COL_EVAL_ID, width=50, anchor="e", stretch=tk.NO)
        self.history_tree.column(db_schema.COL_EVAL_PERIOD, width=150)
        self.history_tree.column(db_schema.COL_EVAL_DATE, width=100, anchor="center")
        self.history_tree.column(db_schema.COL_EVAL_TOTAL_SCORE, width=100, anchor="e")
        self.history_tree.column("evaluator_name", width=150, stretch=tk.YES)

        scrollbar = ttkb.Scrollbar(self.history_lf, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.history_tree.bind("<<TreeviewSelect>>", self._on_evaluation_select)


    def _load_evaluation_history_to_tree(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            evaluations = db_queries.get_employee_evaluations_db(self.employee_id)
            for eval_data in evaluations:
                evaluator_name = eval_data.get('evaluator_username', localization._("unknown_user"))
                self.history_tree.insert("", "end", iid=eval_data[db_schema.COL_EVAL_ID], values=(
                    eval_data[db_schema.COL_EVAL_ID],
                    eval_data[db_schema.COL_EVAL_PERIOD],
                    eval_data[db_schema.COL_EVAL_DATE],
                    eval_data[db_schema.COL_EVAL_TOTAL_SCORE],
                    evaluator_name
                ))
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("eval_error_loading_history", error=e), parent=self)
        self._gui_clear_evaluation_form() # Clear form after loading history


    def _on_evaluation_select(self, event=None):
        selected_item_iid = self.history_tree.focus()
        if not selected_item_iid:
            self.current_selected_evaluation_id = None
            self._gui_clear_evaluation_form()
            return

        self.current_selected_evaluation_id = int(selected_item_iid)
        try:
            eval_data = db_queries.get_evaluation_details_db(self.current_selected_evaluation_id)
            if not eval_data:
                messagebox.showerror(localization._("error_title"), localization._("eval_not_found_error"), parent=self)
                return

            self.eval_period_var.set(eval_data[db_schema.COL_EVAL_PERIOD])
            self.eval_date_entry.entry.delete(0, tk.END)
            self.eval_date_entry.entry.insert(0, eval_data[db_schema.COL_EVAL_DATE])
            self.evaluator_var.set(eval_data.get('evaluator_username', localization._("unknown_user")))
            self.comments_text.delete("1.0", tk.END)
            self.comments_text.insert("1.0", eval_data.get(db_schema.COL_EVAL_COMMENTS, ""))
            
            # Populate criteria scores
            for crit_id, data in self.criteria_widgets.items():
                score_detail = next((item for item in eval_data.get("details", []) if item[db_schema.COL_EVAL_DETAIL_CRITERIA_ID] == crit_id), None)
                data["var"].set(score_detail[db_schema.COL_EVAL_DETAIL_SCORE] if score_detail else 0)
            
            self._calculate_total_score()
            self.save_eval_btn.config(text=localization._("eval_update_button")) # Change button text to Update
            self.record_reward_btn.config(state="normal") # Enable reward button when viewing existing
            self._add_translatable_widget_eval(self.save_eval_btn, "eval_update_button")


        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("eval_error_loading_details", error=e), parent=self)
            self.current_selected_evaluation_id = None
            self._gui_clear_evaluation_form()


    def _gui_save_evaluation(self):
        period = self.eval_period_var.get().strip()
        eval_date = self.eval_date_entry.entry.get()
        comments = self.comments_text.get("1.0", tk.END).strip()
        total_score = float(self.overall_score_var.get()) # Already calculated, ensure float
        evaluator_user_id = self.evaluator_id # Assuming this is set correctly

        if not period or not eval_date:
            messagebox.showwarning(localization._("input_error_title"), localization._("eval_missing_period_or_date_error"), parent=self) # Parent should be self
            return

        scores_details = []
        for crit_id, data in self.criteria_widgets.items():
            scores_details.append({
                "criteria_id": crit_id,
                "score": data["var"].get(),
                "comment": "" # Placeholder, add a comment field per criterion if needed
            })

        try:
            if self.current_selected_evaluation_id: # Update existing
                db_queries.update_employee_evaluation_db(
                    self.current_selected_evaluation_id, period, eval_date, total_score, comments, scores_details, evaluator_user_id
                )
                messagebox.showinfo(localization._("success_title"), localization._("eval_updated_success_message"), parent=self)
                self.record_reward_btn.config(state="normal") # Enable after update
            else: # Add new
                new_eval_id = db_queries.add_employee_evaluation_db(
                    self.employee_id, period, eval_date, total_score, comments, scores_details, evaluator_user_id
                )
                messagebox.showinfo(localization._("success_title"), localization._("eval_added_success_message"), parent=self)
                self.current_selected_evaluation_id = new_eval_id # Store new ID
                self.record_reward_btn.config(state="normal") # Enable after add
            
            self._load_evaluation_history_to_tree() # Parent should be self
            # Don't clear form immediately after save, user might want to record reward
        except db_queries.DatabaseOperationError as e:
            messagebox.showerror(localization._("error_title"), localization._("eval_error_saving", error=str(e)), parent=self)
        except Exception as e_save: # General catch for unexpected issues
            logger.error(f"Unexpected error saving evaluation: {e_save}", exc_info=True)
            messagebox.showerror(localization._("error_title"), localization._("eval_error_saving_unexpected", error=e_save), parent=self)


    def _gui_clear_evaluation_form(self):
        self.current_selected_evaluation_id = None
        self.eval_period_var.set("")
        self.eval_date_entry.entry.delete(0, tk.END)
        self.eval_date_entry.entry.insert(0, dt_date.today().strftime('%Y-%m-%d'))
        # self.evaluator_var.set(self.parent_app.get_current_username() or localization._("unknown_user")) # Reset to current user
        self.comments_text.delete("1.0", tk.END)
        for crit_id, data in self.criteria_widgets.items():
            data["var"].set(0)
        self._calculate_total_score()
        self.save_eval_btn.config(text=localization._("eval_save_button"))
        self._add_translatable_widget_eval(self.save_eval_btn, "eval_save_button")
        self.record_reward_btn.config(state="disabled") # Disable reward button on clear
        self.eval_period_entry.focus_set()

    def _gui_record_reward(self):
        if not self.current_selected_evaluation_id:
            messagebox.showwarning(localization._("warning_title"), localization._("eval_select_for_reward_warning"), parent=self) # Add key
            return

        # Option A: Simple dialog to add a non-recurring allowance
        reward_amount_str = simpledialog.askstring(localization._("eval_reward_amount_title"), # Add key
                                                   localization._("eval_reward_amount_prompt"), parent=self) # Add key
        if reward_amount_str:
            try:
                reward_amount = float(reward_amount_str)
                if reward_amount <= 0:
                    raise ValueError("Amount must be positive.")
                
                reward_desc = f"Performance Bonus based on Evaluation ID {self.current_selected_evaluation_id} (Period: {self.eval_period_var.get()})"
                eff_date = self.eval_date_entry.entry.get() # Use evaluation date as effective date
                db_queries.add_employee_reward_db(self.employee_id, reward_desc, reward_amount, eff_date)
                messagebox.showinfo(localization._("success_title"), localization._("eval_reward_recorded_success", amount=reward_amount), parent=self) # Add key
            except ValueError:
                messagebox.showerror(localization._("input_error_title"), localization._("eval_reward_invalid_amount_error"), parent=self) # Add key
            except Exception as e:
                messagebox.showerror(localization._("error_title"), localization._("eval_reward_record_error", error=str(e)), parent=self) # Add key
