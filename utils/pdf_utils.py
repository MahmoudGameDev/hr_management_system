# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\pdf_utils.py
import logging
import os
from typing import List, Dict, Optional, Any
from datetime import date as dt_date

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors as reportlab_colors
from reportlab.lib.units import inch

import config
from data import database as db_schema # For column constants
from data import queries as db_queries # For _find_employee_by_id, increment_app_counter

logger = logging.getLogger(__name__)
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) not installed. PDF signing features will be limited in pdf_utils.")

# --- Payslip PDF Generation ---
def generate_payslip_pdf(payslip_data: Dict, filepath: str) -> None:
    """Generates a PDF payslip from the given data and saves it to filepath."""
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Payslip", styles['h2']))
    story.append(Spacer(1, 0.1*inch))

    emp_details = db_queries._find_employee_by_id(payslip_data[db_schema.COL_PAY_EMP_ID])
    emp_name = emp_details.get(db_schema.COL_EMP_NAME, payslip_data[db_schema.COL_PAY_EMP_ID]) if emp_details else payslip_data[db_schema.COL_PAY_EMP_ID]
    emp_pos = emp_details.get(db_schema.COL_EMP_POSITION, "N/A") if emp_details else "N/A"

    info_data = [
        ["Employee Name:", emp_name, "Pay Period:", f"{payslip_data[db_schema.COL_PAY_PERIOD_START]} to {payslip_data[db_schema.COL_PAY_PERIOD_END]}"],
        ["Employee ID:", payslip_data[db_schema.COL_PAY_EMP_ID], "Generation Date:", payslip_data[db_schema.COL_PAY_GENERATION_DATE]],
        ["Position:", emp_pos, "", ""],
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2.0*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3), ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("<u>Earnings</u>", styles['h3']))
    earnings_data = [["Description", "Amount"],
        ["Monthly Reference Salary", f"{payslip_data.get('monthly_reference_salary', 0.0):,.2f}"],
        ["Basic Salary for Period", f"{payslip_data[db_schema.COL_PAY_BASIC_SALARY]:,.2f}"],]
    if payslip_data.get('overtime_pay', 0) > 0:
        earnings_data.append([f"Overtime Pay ({payslip_data.get('overtime_hours', 0):.2f} hrs)", f"{payslip_data['overtime_pay']:,.2f}"])
    for item in payslip_data.get("recurring_allowances_detail", []):
        earnings_data.append([f"{item[db_schema.COL_ALLW_TYPE]} (Recurring)", f"{item[db_schema.COL_ALLW_AMOUNT]:,.2f}"])
    for item in payslip_data.get("non_recurring_allowances_detail", []):
        earnings_data.append([f"{item[db_schema.COL_ALLW_TYPE]} (Bonus/Other)", f"{item[db_schema.COL_ALLW_AMOUNT]:,.2f}"])
    earnings_data.append(["<b>Total Allowances</b>", f"<b>{payslip_data[db_schema.COL_PAY_TOTAL_ALLOWANCES]:,.2f}</b>"])
    earnings_data.append(["<b>GROSS SALARY</b>", f"<b>{payslip_data[db_schema.COL_PAY_GROSS_SALARY]:,.2f}</b>"])
    earnings_table = Table(earnings_data, colWidths=[4.5*inch, 2.5*inch])
    earnings_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'), ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, reportlab_colors.grey),
        ('BACKGROUND', (0,0), (-1,0), reportlab_colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTNAME', (0,-2), (-1,-2), 'Helvetica-Bold'),
    ]))
    story.append(earnings_table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("<u>Deductions</u>", styles['h3']))
    deductions_data = [["Description", "Amount"],]
    for item in payslip_data.get("recurring_deductions_detail", []):
        deductions_data.append([f"{item[db_schema.COL_DED_TYPE]} (Recurring)", f"{item[db_schema.COL_DED_AMOUNT]:,.2f}"])
    for item in payslip_data.get("non_recurring_deductions_detail", []):
        deductions_data.append([f"{item[db_schema.COL_DED_TYPE]} (Penalty/Other)", f"{item[db_schema.COL_DED_AMOUNT]:,.2f}"])
    if payslip_data[db_schema.COL_PAY_ADVANCE_REPAYMENT] > 0:
        deductions_data.append(["Salary Advance Repayment", f"{payslip_data[db_schema.COL_PAY_ADVANCE_REPAYMENT]:,.2f}"])
    total_deductions_for_pdf = payslip_data[db_schema.COL_PAY_TOTAL_DEDUCTIONS] + payslip_data[db_schema.COL_PAY_ADVANCE_REPAYMENT]
    deductions_data.append(["<b>Total Deductions</b>", f"<b>{total_deductions_for_pdf:,.2f}</b>"])
    deductions_table = Table(deductions_data, colWidths=[4.5*inch, 2.5*inch])
    deductions_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'), ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, reportlab_colors.grey),
        ('BACKGROUND', (0,0), (-1,0), reportlab_colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(deductions_table)
    story.append(Spacer(1, 0.2*inch))

    net_pay_data = [["<b>NET PAY</b>", f"<b>{payslip_data[db_schema.COL_PAY_NET_PAY]:,.2f}</b>"]]
    net_pay_table = Table(net_pay_data, colWidths=[4.5*inch, 2.5*inch])
    net_pay_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'), ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), reportlab_colors.black), ('FONTSIZE', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEABOVE', (0,0), (-1,0), 1, reportlab_colors.black),
        ('LINEBELOW', (0,0), (-1,0), 2, reportlab_colors.black),
    ]))
    story.append(net_pay_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"Expected Workdays: {payslip_data.get('expected_workdays_in_period', 'N/A')}, Actual Days Logged: {payslip_data.get('actual_days_worked_in_period', 'N/A')}", styles['Normal']))
    if payslip_data.get(db_schema.COL_PAY_NOTES):
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("<u>Notes:</u>", styles['h3']))
        story.append(Paragraph(payslip_data[db_schema.COL_PAY_NOTES], styles['Normal']))
    doc.build(story)
    logger.info(f"Payslip PDF generated: {filepath}")

def generate_contract_pdf(employee_details: Dict, contract_data: Dict, filepath: str) -> None:
    """Generates a simple contract PDF using reportlab."""
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    centered_style = styles['Normal'].clone('centered_style'); centered_style.alignment = 1
    centered_h3_style = styles['h3'].clone('centered_h3_style'); centered_h3_style.alignment = 1
    story.append(Paragraph("EMPLOYMENT CONTRACT", styles['h1']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"This Employment Contract (the \"Contract\") is made and entered into on this day, <b>{dt_date.today().strftime('%d %B %Y')}</b>", styles['Normal']))
    story.append(Spacer(1, 0.1*inch)); story.append(Paragraph("BETWEEN", styles['h3'])); story.append(Spacer(1, 0.1*inch))
    # Use get_setting for robustness
    company_name = config.get_setting("CompanyDetails", "company_name_for_reports")
    reg_country = config.get_setting("CompanyDetails", "company_registration_country")
    company_address = config.get_setting("CompanyDetails", "company_address_for_reports")
    story.append(Paragraph(f"<b>{company_name}</b>, a company duly registered under the laws of {reg_country}, with its principal place of business at {company_address} (hereinafter referred to as the \"Company\"),", styles['Normal']))
    story.append(Spacer(1, 0.2*inch)); story.append(Paragraph("AND", centered_h3_style)); story.append(Spacer(1, 0.1*inch))
    emp_name = employee_details.get(db_schema.COL_EMP_NAME, "N/A"); emp_id = employee_details.get(db_schema.COL_EMP_ID, "N/A")
    story.append(Paragraph(f"<b>{emp_name}</b>, holding Employee ID <b>{emp_id}</b>, residing at [Employee Address - if available/needed] (hereinafter referred to as the \"Employee\").", styles['Normal']))
    story.append(Spacer(1, 0.3*inch)); story.append(Paragraph("<u>Terms of Employment</u>", styles['h3'])); story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"<b>Contract Type:</b> {contract_data.get('contract_type', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Position:</b> {contract_data.get('position', employee_details.get(db_schema.COL_EMP_POSITION, 'N/A'))}", styles['Normal']))
    story.append(Paragraph(f"<b>Start Date:</b> {contract_data.get('start_date', employee_details.get(db_schema.COL_EMP_START_DATE, 'N/A'))}", styles['Normal']))
    story.append(Paragraph(f"<b>End Date:</b> {contract_data.get('current_end_date', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Salary:</b> {contract_data.get('salary', f'${employee_details.get(db_schema.COL_EMP_SALARY, 0.0):,.2f}')}", styles['Normal']))
    story.append(Paragraph(f"<b>Initial Duration:</b> {contract_data.get('initial_duration_years', 'N/A')} years", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    raw_custom_terms = contract_data.get(db_schema.COL_CONTRACT_CUSTOM_TERMS); processed_custom_terms = raw_custom_terms.strip() if raw_custom_terms else ""
    if processed_custom_terms:
        story.append(Paragraph("<u>Custom Conditions</u>", styles['h3'])); story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(processed_custom_terms, styles['Normal'])); story.append(Spacer(1, 0.2*inch))
    story.append(Spacer(1, 0.5*inch)); story.append(Paragraph("_________________________<br/>Employee Signature", centered_style))
    story.append(Spacer(1, 0.5*inch)); story.append(Paragraph("_________________________<br/>Company Representative Signature", centered_style))
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        doc.build(story)
        if not os.path.exists(filepath): raise FileNotFoundError(f"PDF generation failed: File not found at {filepath} after build.")
        logger.info(f"Contract PDF generated: {filepath}")
    except Exception as e:
        logger.error(f"Error during contract PDF generation for path {filepath}: {e}", exc_info=True)
        raise db_queries.DatabaseOperationError(f"Failed to generate contract PDF: {e}")

def generate_professional_pdf_report(data_rows: List[List[Any]], headers: List[str], column_widths: Optional[List[float]],
                                     report_title: str, filepath: str, responsible_signature_text: str = "Responsible Signature:"):
    """Generates a professional-looking PDF report with a title and signature line."""
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(report_title, styles['h1']))
    story.append(Spacer(1, 0.2*inch))

    table_data = [headers]
    for row_list in data_rows: # Iterate through the list of lists
        table_data.append([str(value) for value in row_list]) # Convert each value in the inner list to string

    table = Table(table_data, colWidths=column_widths if column_widths else None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), reportlab_colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), reportlab_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), reportlab_colors.beige), ('GRID', (0, 0), (-1, -1), 1, reportlab_colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("_" * 40, styles['Normal'])) # type: ignore
    story.append(Paragraph(responsible_signature_text, styles['Normal']))
    try:
        db_schema.increment_app_counter(db_schema.COUNTER_REPORTS_GENERATED_PDF) # Corrected: Use db_schema
        doc.build(story)
        logger.info(f"Professional PDF report '{report_title}' generated at {filepath}")
    except Exception as e:
        logger.error(f"Error generating professional PDF report '{report_title}': {e}")
        raise db_schema.DatabaseOperationError(f"Failed to generate PDF report: {e}") # Corrected: Use db_schema for exception
def embed_image_in_pdf(pdf_path: str, image_path: str, page_number: int,
                       sig_width: float, sig_height: float, position: str = "bottom-right",
                       margin: float = 36): # margin in points (0.5 inch)
    """
    Embeds an image (signature) into a PDF file on a specified page and position.
    The original PDF file is overwritten.

    Args:
        pdf_path (str): Path to the PDF file to modify.
        image_path (str): Path to the signature image file.
        page_number (int): 0-indexed page number where the signature should be placed.
        sig_width (float): Desired width of the signature image on the PDF in points.
        sig_height (float): Desired height of the signature image on the PDF in points.
        position (str): "bottom-right", "bottom-left", "top-right", "top-left".
        margin (float): Margin from the page edges in points.
    """
    if not fitz:
        raise db_queries.HRException("PyMuPDF (fitz) library is not installed. Cannot sign PDF.")
    try:
        doc = fitz.open(pdf_path)
        if not (0 <= page_number < len(doc)):
            raise ValueError(f"Invalid page number: {page_number + 1}. PDF has {len(doc)} pages.")

        page = doc.load_page(page_number)
        page_rect = page.rect # Page dimensions (x0, y0, x1, y1)

        x0 = margin; y0 = margin
        if position == "bottom-right": x0 = page_rect.width - sig_width - margin; y0 = page_rect.height - sig_height - margin
        elif position == "bottom-left": y0 = page_rect.height - sig_height - margin
        elif position == "top-right": x0 = page_rect.width - sig_width - margin
        sig_rect = fitz.Rect(x0, y0, x0 + sig_width, y0 + sig_height)
        page.insert_image(sig_rect, filename=image_path)
        doc.saveIncr()
        doc.close()
        logger.info(f"Signature embedded in '{pdf_path}' on page {page_number + 1}.")
    except Exception as e:
        logger.error(f"Failed to embed signature in PDF '{pdf_path}': {e}")
        raise db_queries.DatabaseOperationError(f"Failed to sign PDF: {e}")
