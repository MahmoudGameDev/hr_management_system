# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\api\server.py
from flask import Flask, jsonify, request
import sys
import os
import logging

# Add the project root to sys.path to allow importing 'data' and 'config'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data import queries as db_queries
from data import database as db_schema # For constants if needed
import config as app_config # For API key or other settings

logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Authentication Decorator ---
def require_api_key(f):
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        # Use the API key from app_config
        if not app_config.API_SECRET_KEY:
            logger.error("API: API_SECRET_KEY is not configured. Denying all API requests.")
            return jsonify({"error": "API Misconfiguration"}), 500
        if provided_key == app_config.API_SECRET_KEY:
            return f(*args, **kwargs)
        else:
            logger.warning(f"API: Unauthorized access attempt. Provided key: {provided_key}")
            return jsonify({"error": "Unauthorized"}), 401
    decorated_function.__name__ = f.__name__ # Preserve original function name for Flask
    return decorated_function

# --- API Endpoints ---

@app.route('/api/status', methods=['GET'])
def api_status():
    """Basic status endpoint to check if the API is running."""
    logger.info("API: Status endpoint accessed.")
    return jsonify({"status": "HR Management System API is running"}), 200

@app.route('/api/employees', methods=['GET'])
@require_api_key
def get_all_employees():
    """Retrieves a list of all employees."""
    try:
        include_archived_str = request.args.get('include_archived', 'false').lower()
        include_archived = include_archived_str == 'true'
        
        employees = db_queries.get_all_employees_db(include_archived=include_archived)
        logger.info(f"API: Retrieved {len(employees)} employees. Include archived: {include_archived}")
        return jsonify(employees), 200
    except Exception as e:
        logger.error(f"API: Error fetching all employees: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve employees", "details": str(e)}), 500

@app.route('/api/employees/<string:employee_id>', methods=['GET'])
@require_api_key
def get_employee_by_id(employee_id: str):
    """Retrieves details for a specific employee by their ID."""
    try:
        employee = db_queries.get_employee_by_id_db(employee_id)
        if employee:
            logger.info(f"API: Retrieved employee details for ID: {employee_id}")
            return jsonify(employee), 200
        else:
            logger.warning(f"API: Employee not found with ID: {employee_id}")
            return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        logger.error(f"API: Error fetching employee {employee_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve employee details", "details": str(e)}), 500

@app.route('/api/departments', methods=['GET'])
@require_api_key
def get_all_departments():
    """Retrieves a list of all departments."""
    try:
        departments = db_queries.list_departments_db()
        logger.info(f"API: Retrieved {len(departments)} departments.")
        return jsonify(departments), 200
    except Exception as e:
        logger.error(f"API: Error fetching departments: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve departments", "details": str(e)}), 500

# --- Main ---
if __name__ == '__main__':
    # Basic logging setup for the API server if run directly
    if not logger.handlers: # Avoid adding multiple handlers if already configured
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - API - %(message)s')
    
    # Ensure database is initialized if API is run standalone
    # (though typically db init is handled by the main app's startup)
    try:
        db_schema.init_db()
    except Exception as e_db_init:
        logger.critical(f"API: Failed to initialize database on standalone run: {e_db_init}")
        # Decide if to exit or continue with potential errors

    logger.info("API server starting on http://127.0.0.1:5001")
    app.run(debug=app_config.DEBUG_MODE, port=5001) # Run on a different port than default 5000