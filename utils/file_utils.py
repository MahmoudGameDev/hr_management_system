# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\file_utils.py
import csv
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3

# Project-specific imports
import config # For DATABASE_NAME, BACKUP_DIR

try:
    import pandas as pd
except ImportError:
    pd = None

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors as reportlab_colors
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

def export_to_excel(data: List[Dict[str, Any]], filepath: str, sheet_name: str = "Sheet1"):
    """
    Exports a list of dictionaries to an Excel file.
    Can also be used for CSV-like structures if pandas is available.
    """
    if pd:
        try:
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, sheet_name=sheet_name)
            logger.info(f"Data successfully exported to Excel: {filepath}")
        except Exception as e:
            logger.error(f"Error exporting data to Excel file {filepath}: {e}")
            raise IOError(f"Failed to export to Excel: {e}")
    else:
        # Fallback to basic CSV if pandas is not installed,
        # assuming the structure is simple enough for csv.DictWriter.
        logger.warning("Pandas library not found. Attempting to export as CSV.")
        if not data:
            logger.warning("No data to export to CSV.")
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(data[0].keys()) # Use keys from the first dict as headers
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"Data successfully exported as CSV (pandas fallback): {filepath}")
        except Exception as e:
            logger.error(f"Error exporting data to CSV (pandas fallback) {filepath}: {e}")
            raise IOError(f"Failed to export to CSV: {e}")

def export_to_pdf(data: List[Dict[str, Any]], headers: List[str], column_widths: Optional[List[float]],
                  report_title: str, filepath: str):
    """
    Placeholder for exporting data to a PDF file using ReportLab.
    This function should be similar to pdf_utils.generate_professional_pdf_report
    or call it. For now, it's a basic placeholder.
    """
    # This is a simplified placeholder. You'd typically use pdf_utils.generate_professional_pdf_report
    # or implement similar logic here.
    logger.info(f"Placeholder: PDF export called for '{report_title}' to '{filepath}'. Actual implementation needed.")
    # Example: pdf_utils.generate_professional_pdf_report(data, headers, column_widths, report_title, filepath)
    pass

def secure_delete_file(filepath: str):
    """
    Securely deletes a file. (Placeholder - actual secure deletion is complex)
    For now, just performs a standard os.remove.
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"File '{filepath}' deleted.")
        else:
            logger.warning(f"Attempted to delete non-existent file: {filepath}")
    except Exception as e:
        logger.error(f"Error deleting file '{filepath}': {e}")
        # Do not re-raise if the goal is just to attempt deletion.
        # If deletion is critical, an exception should be raised.

def create_backup_db(backup_directory: Optional[str] = None, custom_filename: Optional[str] = None) -> Optional[str]:
    """
    Creates a backup of the current SQLite database file.
    The backup is named with a timestamp or a custom name.

    Args:
        backup_directory (Optional[str]): The directory where the backup file will be stored.
                                         Defaults to config.BACKUP_DIR if None.
        custom_filename (Optional[str]): If provided, this name is used for the backup file.
                                         Otherwise, a timestamped name is generated.

    Returns:
        Optional[str]: The path to the created backup file, or None if failed.
    """
    if backup_directory is None:
        backup_directory = config.BACKUP_DIR
    if not os.path.exists(config.DATABASE_NAME):
        print(f"Database file '{config.DATABASE_NAME}' not found. Cannot create backup.") # Or log this
        return None

    try:
        if not os.path.exists(backup_directory):
            os.makedirs(backup_directory, exist_ok=True) # Use exist_ok=True
            print(f"Backup directory '{backup_directory}' created.") # Or log this

        if custom_filename:
            backup_filename = custom_filename if custom_filename.endswith(".db") else f"{custom_filename}.db"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{os.path.splitext(config.DATABASE_NAME)[0]}_backup_{timestamp}.db"
        
        backup_filepath = os.path.join(backup_directory, backup_filename)

        shutil.copy2(config.DATABASE_NAME, backup_filepath) # copy2 preserves metadata
        print(f"Database backup created successfully: {backup_filepath}") # Or log this
        return backup_filepath
    except Exception as e:
        print(f"Failed to create database backup: {e}") # Or log this
        return None

def restore_database_from_backup(backup_filepath: str, destination_db_name: Optional[str] = None) -> bool:
    """
    Restores the database from a given backup file to the specified destination.
    If destination_db_name is None, it defaults to config.DATABASE_NAME.
    """
    if destination_db_name is None:
        destination_db_name = config.DATABASE_NAME

    if not os.path.exists(backup_filepath):
        print(f"Backup file '{backup_filepath}' not found. Cannot restore.") # Or log this
        return False
    shutil.copy2(backup_filepath, destination_db_name)
    print(f"Database restored successfully from '{backup_filepath}' to '{destination_db_name}'.") # Or log this
    return True