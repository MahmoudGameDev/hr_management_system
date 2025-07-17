# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\analytics\predictor.py
import sqlite3
import pandas as pd
from data import database as db_schema # Added import
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root to sys.path to allow importing 'config' and 'data'
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data import database as db_schema # For column constants
# from data import queries as db_queries # Not directly used by this class methods, but _get_historical_data_for_attrition uses SQL

logger = logging.getLogger(__name__)

# Resume Parsing Imports (optional, handle gracefully if not installed)
try:
    from pyresparser import ResumeParser
except ImportError:
    logger.warning("pyresparser library not found. Resume parsing features will be disabled.")
    ResumeParser = None
except LookupError as e_lookup:
    logger.error(f"NLTK resource missing for pyresparser: {e_lookup}. Resume parsing disabled.")
    ResumeParser = None


class PredictiveAnalytics:
    def __init__(self, db_name=config.DATABASE_NAME):
        self.db_name = db_name
        self.attrition_model = None
        self.attrition_scaler = None
        self.attrition_label_encoders = {} # To store label encoders for categorical features
        self.attrition_feature_columns = [] # To store column order after encoding
        self.salary_increase_model = None
        self.salary_increase_scaler = None
        self.salary_increase_label_encoders = {}
        self.salary_increase_feature_columns = []

    def _get_historical_data_for_attrition(self) -> pd.DataFrame:
        """Fetches and preprocesses historical data for training the attrition model."""
        conn = sqlite3.connect(self.db_name)
        query = f"""
            SELECT 
                e.{COL_EMP_ID}, e.{COL_EMP_SALARY}, e.{COL_EMP_VACATION_DAYS}, e.{COL_EMP_START_DATE}, 
                e.{COL_EMP_TERMINATION_DATE}, e.{COL_EMP_POSITION}, d.{COL_DEPT_NAME} as {COL_EMP_DEPARTMENT},
                (SELECT AVG(ev.{COL_EVAL_TOTAL_SCORE}) 
                 FROM {TABLE_EMPLOYEE_EVALUATIONS} ev 
                 WHERE ev.{COL_EVAL_EMP_ID} = e.{COL_EMP_ID}
                ) as avg_performance_score,
                (SELECT ev.{COL_EVAL_TOTAL_SCORE} 
                 FROM {TABLE_EMPLOYEE_EVALUATIONS} ev 
                 WHERE ev.{COL_EVAL_EMP_ID} = e.{COL_EMP_ID}
                 ORDER BY ev.{COL_EVAL_DATE} DESC LIMIT 1
                ) as last_performance_score,
                (SELECT COUNT(*) FROM {TABLE_LEAVE_REQUESTS} lr 
                 WHERE lr.{COL_LR_EMP_ID} = e.{COL_EMP_ID} AND lr.{COL_LR_STATUS} = 'Approved' AND lr.{COL_LR_LEAVE_TYPE} = 'Unpaid Leave') as unpaid_leave_count
            FROM {TABLE_EMPLOYEES} e
            LEFT JOIN {TABLE_DEPARTMENTS} d ON e.{COL_EMP_DEPARTMENT_ID} = d.{COL_DEPT_ID}
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return pd.DataFrame()

        # --- Absence Calculation (Simplified: count days with no attendance log on expected workdays in last 6 months) ---
        # This is computationally intensive if done per employee here. 
        # A more optimized approach might involve pre-aggregating attendance data or more complex SQL.
        # For this example, we'll use 'unpaid_leave_count' as a proxy from the query above.
        # A true absence count would require iterating through expected workdays and checking attendance_log.
        # df['absence_count_last_6m'] = 0 # Placeholder for more complex calculation

        # --- Imputation for performance scores ---
        # Fill NaN for avg_performance_score and last_performance_score with median (or mean)
        # Calculate median only on non-NaN values. If all are NaN, median will be NaN.
        if 'avg_performance_score' in df.columns:
            median_avg_score = df['avg_performance_score'].dropna().median()
            # Fill NaN values in the original column. If median_avg_score is NaN, fill with 0.
            df['avg_performance_score'] = df['avg_performance_score'].fillna(median_avg_score if pd.notna(median_avg_score) else 0.0)
        else:
            df['avg_performance_score'] = 0.0 # Default if column doesn't exist

        if 'last_performance_score' in df.columns:
            median_last_score = df['last_performance_score'].dropna().median()
            df['last_performance_score'] = df['last_performance_score'].fillna(median_last_score if pd.notna(median_last_score) else 0.0)
        else:
            df['last_performance_score'] = 0.0

        if 'unpaid_leave_count' in df.columns:
            df['unpaid_leave_count'] = df['unpaid_leave_count'].fillna(0)
        else:
            df['unpaid_leave_count'] = 0

        # --- Feature Engineering ---
        # Tenure
        df['start_date_dt'] = pd.to_datetime(df[COL_EMP_START_DATE], errors='coerce')
        df['termination_date_dt'] = pd.to_datetime(df[COL_EMP_TERMINATION_DATE], errors='coerce')
        now = pd.to_datetime(datetime.now())
        df['tenure_days'] = (df['termination_date_dt'].fillna(now) - df['start_date_dt']).dt.days.fillna(0).astype(int)

        # Target variable
        df['left_company'] = df[COL_EMP_TERMINATION_DATE].notna().astype(int)

        # Handle categorical features (Position, Department)
        categorical_cols = [COL_EMP_POSITION, COL_EMP_DEPARTMENT]
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown') # Fill NaN before encoding
                le = LabelEncoder()
                df[col + '_encoded'] = le.fit_transform(df[col])
                self.attrition_label_encoders[col] = le
            else:
                logger.warning(f"Categorical column '{col}' not found in DataFrame for attrition model.")

        # Select features for the model
        # Keep original COL_EMP_ID for now if needed for mapping predictions later, but drop before training
        self.attrition_feature_columns = [
            COL_EMP_SALARY, COL_EMP_VACATION_DAYS, 'tenure_days', 
            'avg_performance_score', 'last_performance_score', 'unpaid_leave_count'
        ]
        # Add encoded categorical columns only if they were created
        for col in categorical_cols:
            if col + '_encoded' in df.columns:
                self.attrition_feature_columns.append(col + '_encoded')

        # Ensure all selected feature columns actually exist in the DataFrame
        self.attrition_feature_columns = [col for col in self.attrition_feature_columns if col in df.columns]

        required_cols_for_df_model = self.attrition_feature_columns + ['left_company', db_schema.COL_EMP_ID]
        # Ensure all these columns exist in df before trying to select them
        df_model_cols = [col for col in required_cols_for_df_model if col in df.columns]
        df_model = df[df_model_cols].copy()

        # Handle missing values (e.g., avg_performance_score if no evaluations)
        # Fill any remaining NaNs in feature columns with 0 after specific imputation.
        df_model = df_model.fillna(0) # General fillna for any other NaNs, review this

        return df_model

    def train_attrition_model(self):
        df_model = self._get_historical_data_for_attrition()

        if df_model.empty or 'left_company' not in df_model.columns or len(df_model['left_company'].unique()) < 2:
            logger.warning("Attrition Model: Not enough data or classes to train. Min 2 classes needed for target.")
            self.attrition_model = None
            return

        X = df_model[self.attrition_feature_columns].copy() # Ensure it's a copy
        y = df_model['left_company']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

        self.attrition_scaler = StandardScaler()
        X_train_scaled = self.attrition_scaler.fit_transform(X_train)
        X_test_scaled = self.attrition_scaler.transform(X_test)

        self.attrition_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        self.attrition_model.fit(X_train_scaled, y_train)

        y_pred_test = self.attrition_model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred_test)
        logger.info(f"Attrition model trained. Test accuracy: {accuracy:.2f}")
        # TODO: Log more metrics (precision, recall, F1, confusion matrix)

    def predict_employee_attrition(self, live_employee_features: pd.DataFrame) -> Optional[list]:
        if not self.attrition_model or not self.attrition_scaler or not self.attrition_feature_columns:
            logger.warning("Attrition model/scaler/features not ready. Cannot predict.")
            return None
        
        # Ensure live_employee_features has the same columns in the same order as training data
        # And apply the same preprocessing (fillna, label encoding, scaling)
        # This is a complex step, for now, assume live_employee_features is preprocessed correctly.
        # Example:
        # X_live_processed = live_employee_features[self.attrition_feature_columns].copy()
        # for col, le in self.attrition_label_encoders.items():
        #     X_live_processed[col + '_encoded'] = le.transform(X_live_processed[col].fillna('Unknown'))
        # X_live_processed = X_live_processed.fillna(0) # Or more sophisticated imputation
        # X_live_scaled = self.attrition_scaler.transform(X_live_processed[self.attrition_feature_columns])
        # predictions = self.attrition_model.predict_proba(X_live_scaled)[:, 1] # Probability of leaving

        # Simplified for now, assuming live_employee_features is already scaled and matches columns
        try:
            predictions = self.attrition_model.predict_proba(live_employee_features)[:, 1]
            return predictions.tolist()
        except Exception as e:
            logger.error(f"Error during attrition prediction: {e}")
            return None


    def extract_resume_data(self, resume_filepath: str) -> Optional[Dict]:
        """
        Extracts data from a resume file using pyresparser.
        Ensure pyresparser and its dependencies (spaCy model, NLTK data) are installed.
        """
        if ResumeParser is None:
            logger.error("ResumeParser (pyresparser) is not available. Cannot extract resume data.")
            return None
        try:
            logger.info(f"Attempting to parse resume: {resume_filepath}")
            # Ensure NLTK and spaCy models are downloaded.
            # This might be better handled at application startup or first use.
            # import nltk
            # try:
            #     nltk.data.find('corpora/wordnet.zip')
            # except nltk.downloader.DownloadError:
            #     nltk.download('wordnet')
            # try:
            #     nltk.data.find('corpora/stopwords.zip')
            # except nltk.downloader.DownloadError:
            #     nltk.download('stopwords')
            # import spacy
            # try:
            #     spacy.load('en_core_web_sm')
            # except OSError:
            #     logger.warning("spaCy en_core_web_sm model not found. Downloading...")
            #     spacy.cli.download('en_core_web_sm')
                
            parser = ResumeParser(resume_filepath)
            data = parser.get_extracted_data()
            logger.info(f"Successfully parsed resume. Extracted keys: {list(data.keys()) if data else 'None'}")
            return data
        except Exception as e:
            logger.error(f"Error parsing resume {resume_filepath}: {e}")
            return None

    def suggest_profile_updates_from_resume(self, employee_id: str, resume_data: Dict) -> Dict:
        """
        Compares extracted resume data with existing employee profile and suggests updates.
        """
        suggestions = {"updates": {}, "new_info": {}}
        employee_details = _find_employee_by_id(employee_id)
        if not employee_details:
            logger.warning(f"Cannot suggest updates, employee {employee_id} not found.")
            return suggestions

        if resume_data.get('email') and not employee_details.get(COL_EMP_EMAIL):
            suggestions["updates"][COL_EMP_EMAIL] = resume_data['email']
        if resume_data.get('mobile_number') and not employee_details.get(COL_EMP_PHONE):
            suggestions["updates"][COL_EMP_PHONE] = resume_data['mobile_number']
        
        extracted_education_parts = []
        if resume_data.get('degree'):
            extracted_education_parts.extend(resume_data['degree'])
        if resume_data.get('college_name'): # pyresparser might use 'college_name' or similar
             extracted_education_parts.extend(resume_data['college_name'])
        
        if extracted_education_parts:
            extracted_education_str = ", ".join(filter(None, extracted_education_parts))
            if extracted_education_str and not employee_details.get(COL_EMP_EDUCATION):
                 suggestions["updates"][COL_EMP_EDUCATION] = extracted_education_str
            elif extracted_education_str:
                 suggestions["new_info"]["education_from_cv"] = extracted_education_str

        if resume_data.get('skills'):
            suggestions["new_info"]["extracted_skills"] = resume_data['skills']
        
        if resume_data.get('experience'):
            # For now, just list experience. Integrating into COL_EMP_EMPLOYMENT_HISTORY needs careful formatting.
            suggestions["new_info"]["extracted_experience"] = resume_data['experience']
        if resume_data.get('total_experience') is not None:
             suggestions["new_info"]["total_experience_years"] = resume_data['total_experience']

        logger.info(f"Resume update suggestions for {employee_id}: {suggestions}")
        return suggestions

    def basic_suitability_assessment(self, resume_skills: List[str], job_description_text: str, required_skills_keywords: List[str]) -> Dict:
        """
        Performs a very basic suitability assessment.
        1. Keyword matching for required skills.
        2. Cosine similarity between resume skills (joined) and job description.
        """
        assessment = {"keyword_match_score": 0.0, "matched_keywords": [], "similarity_score": 0.0}
        
        # Keyword Matching
        if resume_skills and required_skills_keywords:
            matched_count = 0
            for skill in required_skills_keywords:
                if skill.lower() in [s.lower() for s in resume_skills]:
                    matched_count += 1
                    assessment["matched_keywords"].append(skill)
            assessment["keyword_match_score"] = (matched_count / len(required_skills_keywords)) * 100 if required_skills_keywords else 0

        # Basic TF-IDF Cosine Similarity (conceptual, needs more robust implementation)
        # This is a very simplified example. Real-world usage would involve better text preprocessing.
        # if resume_skills and job_description_text:
        #     try:
        #         vectorizer = TfidfVectorizer()
        #         resume_text_for_similarity = " ".join(resume_skills)
        #         tfidf_matrix = vectorizer.fit_transform([resume_text_for_similarity, job_description_text])
        #         assessment["similarity_score"] = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
        #     except Exception as e:
        #         logger.error(f"Error calculating TF-IDF similarity: {e}")
        #         assessment["similarity_score"] = -1 # Indicate error

        logger.info(f"Basic suitability assessment: {assessment}")
        return assessment
# --- Payslip PDF Generation ---
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
