# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\ai\analytics_engine.py
import sqlite3
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Optional, List, Any

# Machine Learning imports
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
# from sklearn.metrics import classification_report, confusion_matrix # Optional for more detailed logging

# Resume parsing
try:
    from pyresparser import ResumeParser
except ImportError:
    ResumeParser = None
    print("Warning: pyresparser library not found. Resume parsing features will be disabled. Install with: pip install pyresparser")
except LookupError as e_lookup: # Catch NLTK resource errors
    print(f"NLTK resource missing for pyresparser: {e_lookup}. Resume parsing disabled. Try: import nltk; nltk.download('stopwords'); nltk.download('punkt')")
    ResumeParser = None

# Project-specific imports
import config # Assuming config.py is in the project root
from data import database as db_schema
from data.queries import _find_employee_by_id # Assuming this helper is in data/queries.py

logger = logging.getLogger(__name__)

class PredictiveAnalytics:
    def __init__(self, db_name=config.DATABASE_NAME):
        self.db_name = db_name
        self.attrition_model = None
        self.attrition_scaler = None
        self.attrition_label_encoders: Dict[str, LabelEncoder] = {}
        self.attrition_feature_columns: List[str] = []
        # Placeholders for future models
        self.salary_increase_model = None
        self.salary_increase_scaler = None
        self.salary_increase_label_encoders: Dict[str, LabelEncoder] = {}
        self.salary_increase_feature_columns: List[str] = []

    def _get_historical_data_for_attrition(self) -> pd.DataFrame:
        """Fetches and preprocesses historical data for training the attrition model."""
        conn = sqlite3.connect(self.db_name)
        # Note: Constants like COL_EMP_ID are from db_schema
        query = f"""
            SELECT
                e.{db_schema.COL_EMP_ID}, e.{db_schema.COL_EMP_SALARY}, e.{db_schema.COL_EMP_VACATION_DAYS},
                e.{db_schema.COL_EMP_START_DATE}, e.{db_schema.COL_EMP_TERMINATION_DATE},
                e.{db_schema.COL_EMP_POSITION}, d.{db_schema.COL_DEPT_NAME} as {db_schema.COL_EMP_DEPARTMENT},
                (SELECT AVG(ev.{db_schema.COL_EVAL_TOTAL_SCORE})
                 FROM {db_schema.TABLE_EMPLOYEE_EVALUATIONS} ev
                 WHERE ev.{db_schema.COL_EVAL_EMP_ID} = e.{db_schema.COL_EMP_ID}
                ) as avg_performance_score,
                (SELECT ev.{db_schema.COL_EVAL_TOTAL_SCORE}
                 FROM {db_schema.TABLE_EMPLOYEE_EVALUATIONS} ev
                 WHERE ev.{db_schema.COL_EVAL_EMP_ID} = e.{db_schema.COL_EMP_ID}
                 ORDER BY ev.{db_schema.COL_EVAL_DATE} DESC LIMIT 1
                ) as last_performance_score,
                (SELECT COUNT(*) FROM {db_schema.TABLE_LEAVE_REQUESTS} lr
                 WHERE lr.{db_schema.COL_LR_EMP_ID} = e.{db_schema.COL_EMP_ID} AND
                 lr.{db_schema.COL_LR_STATUS} = 'Approved' AND lr.{db_schema.COL_LR_LEAVE_TYPE} = 'Unpaid Leave'
                ) as unpaid_leave_count
            FROM {db_schema.TABLE_EMPLOYEES} e
            LEFT JOIN {db_schema.TABLE_DEPARTMENTS} d ON e.{db_schema.COL_EMP_DEPARTMENT_ID} = d.{db_schema.COL_DEPT_ID}
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return pd.DataFrame()

        # Imputation for performance scores and unpaid leave
        median_avg_score = df['avg_performance_score'].median()
        df['avg_performance_score'] = df['avg_performance_score'].fillna(median_avg_score if pd.notna(median_avg_score) else 0)
        median_last_score = df['last_performance_score'].median()
        df['last_performance_score'] = df['last_performance_score'].fillna(median_last_score if pd.notna(median_last_score) else 0)
        df['unpaid_leave_count'] = df['unpaid_leave_count'].fillna(0)

        # Feature Engineering
        df['start_date_dt'] = pd.to_datetime(df[db_schema.COL_EMP_START_DATE], errors='coerce')
        df['termination_date_dt'] = pd.to_datetime(df[db_schema.COL_EMP_TERMINATION_DATE], errors='coerce')
        now_dt = pd.to_datetime(datetime.now())
        df['tenure_days'] = (df['termination_date_dt'].fillna(now_dt) - df['start_date_dt']).dt.days

        # Target variable
        df['left_company'] = df[db_schema.COL_EMP_TERMINATION_DATE].notna().astype(int)

        # Handle categorical features
        categorical_cols = [db_schema.COL_EMP_POSITION, db_schema.COL_EMP_DEPARTMENT]
        self.attrition_label_encoders = {} # Reset for fresh training
        for col in categorical_cols:
            df[col] = df[col].fillna('Unknown') # Fill NaN before encoding
            le = LabelEncoder()
            df[col + '_encoded'] = le.fit_transform(df[col])
            self.attrition_label_encoders[col] = le

        self.attrition_feature_columns = [
            db_schema.COL_EMP_SALARY, db_schema.COL_EMP_VACATION_DAYS, 'tenure_days',
            'avg_performance_score', 'last_performance_score', 'unpaid_leave_count'
        ] + [col + '_encoded' for col in categorical_cols]

        df_model = df[self.attrition_feature_columns + ['left_company', db_schema.COL_EMP_ID]].copy()
        df_model = df_model.fillna(0) # General fillna for any other NaNs in feature columns
        return df_model

    def train_attrition_model(self):
        df_model = self._get_historical_data_for_attrition()

        if df_model.empty or 'left_company' not in df_model.columns or len(df_model['left_company'].unique()) < 2:
            logger.warning("Attrition Model: Not enough data or classes to train. Min 2 classes needed for target.")
            self.attrition_model = None
            return

        X = df_model[self.attrition_feature_columns].copy()
        y = df_model['left_company']

        # Stratify only if there are at least 2 samples for each class
        stratify_param = y if y.nunique() > 1 and all(y.value_counts() >= 2) else None
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=stratify_param)

        self.attrition_scaler = StandardScaler()
        X_train_scaled = self.attrition_scaler.fit_transform(X_train)
        X_test_scaled = self.attrition_scaler.transform(X_test)

        self.attrition_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        self.attrition_model.fit(X_train_scaled, y_train)

        y_pred_test = self.attrition_model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred_test)
        logger.info(f"Attrition model trained. Test accuracy: {accuracy:.2f}")
        # Consider logging: classification_report(y_test, y_pred_test)

    def predict_employee_attrition(self, live_employee_df: pd.DataFrame) -> Optional[List[float]]:
        if not self.attrition_model or not self.attrition_scaler or not self.attrition_feature_columns:
            logger.warning("Attrition model/scaler/features not ready. Cannot predict.")
            return None

        try:
            X_live_processed = live_employee_df.copy()

            # Apply label encoding using stored encoders
            for col, le in self.attrition_label_encoders.items():
                if col in X_live_processed.columns:
                    # Handle unseen labels by replacing them with a placeholder or a specific encoded value
                    # For simplicity, map unseen to a new category like 'Unknown_Live' then encode, or use -1
                    X_live_processed[col + '_encoded'] = X_live_processed[col].apply(
                        lambda x: le.transform([x])[0] if x in le.classes_ else -1 # -1 or handle as new category
                    )
                else: # pragma: no cover
                    logger.warning(f"Column {col} not found in live data for label encoding. Filling with -1.")
                    X_live_processed[col + '_encoded'] = -1

            # Ensure all feature columns are present and in correct order
            for feature_col in self.attrition_feature_columns:
                if feature_col not in X_live_processed.columns:
                    X_live_processed[feature_col] = 0 # Or a more appropriate fill value (e.g., median from training)

            X_live_aligned = X_live_processed[self.attrition_feature_columns].fillna(0)

            X_live_scaled = self.attrition_scaler.transform(X_live_aligned)
            predictions_proba = self.attrition_model.predict_proba(X_live_scaled)[:, 1] # Probability of class 1 (leaving)
            return predictions_proba.tolist()
        except Exception as e:
            logger.error(f"Error during attrition prediction: {e}", exc_info=True)
            return None

    def extract_resume_data(self, resume_filepath: str) -> Optional[Dict]:
        if ResumeParser is None:
            logger.error("ResumeParser (pyresparser) is not available. Cannot extract resume data.")
            return None
        try:
            logger.info(f"Attempting to parse resume: {resume_filepath}")
            parser = ResumeParser(resume_filepath)
            data = parser.get_extracted_data()
            logger.info(f"Successfully parsed resume. Extracted keys: {list(data.keys()) if data else 'None'}")
            return data
        except Exception as e:
            logger.error(f"Error parsing resume {resume_filepath}: {e}", exc_info=True)
            return None

    def suggest_profile_updates_from_resume(self, employee_id: str, resume_data: Dict) -> Dict[str, Dict[str, Any]]:
        """
        Compares extracted resume data with existing employee profile and suggests updates.
        Note: This method's direct call to _find_employee_by_id is a design consideration.
        Ideally, employee_details would be passed in, or this logic moved to a service layer.
        """
        suggestions: Dict[str, Dict[str, Any]] = {"updates": {}, "new_info": {}}
        employee_details = _find_employee_by_id(employee_id) # Assumes _find_employee_by_id is imported

        if not employee_details:
            logger.warning(f"Cannot suggest updates, employee {employee_id} not found.")
            return suggestions

        if resume_data.get('email') and not employee_details.get(db_schema.COL_EMP_EMAIL):
            suggestions["updates"][db_schema.COL_EMP_EMAIL] = resume_data['email']
        if resume_data.get('mobile_number') and not employee_details.get(db_schema.COL_EMP_PHONE):
            suggestions["updates"][db_schema.COL_EMP_PHONE] = resume_data['mobile_number']

        extracted_education_parts = []
        if resume_data.get('degree'): # pyresparser might use 'degree'
            extracted_education_parts.extend(resume_data['degree'])
        if resume_data.get('college_name'): # pyresparser might use 'college_name'
             extracted_education_parts.extend(resume_data['college_name'])

        if extracted_education_parts:
            extracted_education_str = ", ".join(filter(None, extracted_education_parts))
            # Suggest update only if current education is empty
            if extracted_education_str and not employee_details.get(db_schema.COL_EMP_EDUCATION):
                 suggestions["updates"][db_schema.COL_EMP_EDUCATION] = extracted_education_str
            # Always provide as new_info if found
            elif extracted_education_str:
                 suggestions["new_info"]["education_from_cv"] = extracted_education_str

        if resume_data.get('skills'):
            suggestions["new_info"]["extracted_skills"] = resume_data['skills']

        if resume_data.get('experience'):
            suggestions["new_info"]["extracted_experience"] = resume_data['experience']
        if resume_data.get('total_experience') is not None: # Can be 0
             suggestions["new_info"]["total_experience_years"] = resume_data['total_experience']

        logger.info(f"Resume update suggestions for {employee_id}: {suggestions}")
        return suggestions

    def basic_suitability_assessment(self, resume_skills: List[str],
                                     job_description_text: str, # Not used in current basic version
                                     required_skills_keywords: List[str]) -> Dict[str, Any]:
        assessment: Dict[str, Any] = {"keyword_match_score": 0.0, "matched_keywords": [], "similarity_score": 0.0}

        # Keyword Matching
        if resume_skills and required_skills_keywords:
            matched_count = 0
            normalized_resume_skills = [str(s).lower() for s in resume_skills]
            for req_skill in required_skills_keywords:
                if str(req_skill).lower() in normalized_resume_skills:
                    matched_count += 1
                    assessment["matched_keywords"].append(req_skill)
            assessment["keyword_match_score"] = (matched_count / len(required_skills_keywords)) * 100 if required_skills_keywords else 0.0

        # Cosine similarity part was commented out in monolithic, keeping it so.
        # If implemented, ensure TfidfVectorizer and cosine_similarity are imported.

        logger.info(f"Basic suitability assessment: {assessment}")
        return assessment