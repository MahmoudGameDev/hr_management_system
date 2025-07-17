# c:\Users\mahmo\OneDrive\Documents\ai\HR\version\utils\cloud_sync.py
from typing import Optional
import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file'] # Scope for creating/uploading files
TOKEN_PATH = 'token.json'  # Stores the user's access and refresh tokens.
CREDENTIALS_PATH = 'credentials.json'  # Your Google Cloud project OAuth 2.0 client ID file.
                                      # THIS FILE MUST BE OBTAINED FROM GOOGLE CLOUD CONSOLE.
                                      # AND SHOULD BE KEPT SECRET.

class GoogleDriveSync:
    def __init__(self):
        self.creds = None
        self._load_or_refresh_credentials()

    def _load_or_refresh_credentials(self):
        """Loads existing credentials or initiates the OAuth flow."""
        if os.path.exists(TOKEN_PATH):
            self.creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.info("Google Drive token refreshed successfully.")
                except Exception as e:
                    logger.warning(f"Failed to refresh Google Drive token: {e}. Re-authentication may be needed.")
                    self.creds = None # Force re-auth if refresh fails
            # If still no valid creds, authentication is needed.
            # The actual authentication flow will be triggered by authenticate()

    def is_authenticated(self) -> bool:
        self._load_or_refresh_credentials() # Ensure creds are up-to-date
        return bool(self.creds and self.creds.valid)

    def authenticate(self, force_reauth: bool = False) -> bool:
        """Initiates the OAuth2 authentication flow if needed or forced."""
        if force_reauth and os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
            self.creds = None
            logger.info("Forced re-authentication: token.json removed.")

        self._load_or_refresh_credentials() # Attempt to load/refresh first

        if not self.creds or not self.creds.valid: # If still not valid, run the flow
            if not os.path.exists(CREDENTIALS_PATH):
                logger.error(f"Google API Credentials file ('{CREDENTIALS_PATH}') not found. Cannot authenticate.")
                # In a GUI app, you'd show a message to the user here.
                raise FileNotFoundError(f"Google API Credentials file ('{CREDENTIALS_PATH}') is required for authentication.")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # run_local_server will attempt to open a browser and start a local server for the redirect.
            try:
                self.creds = flow.run_local_server(port=0) # port=0 finds an available port
                logger.info("Google Drive authentication successful.")
            except Exception as e:
                logger.error(f"Error during Google Drive authentication flow: {e}")
                self.creds = None
                raise ConnectionError(f"Google Drive authentication failed: {e}")

            if self.creds: # Save the credentials for the next run
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(self.creds.to_json())
                logger.info(f"Google Drive token saved to {TOKEN_PATH}")
        return self.is_authenticated()

    def upload_file(self, local_filepath: str, drive_folder_name: str = "HRAppBackups") -> Optional[str]:
        """Uploads a file to a specific folder in Google Drive."""
        if not self.is_authenticated():
            logger.error("Not authenticated with Google Drive. Please authenticate first.")
            # In a GUI, you might trigger the auth flow here or prompt the user.
            return None

        try:
            service = build('drive', 'v3', credentials=self.creds)
            
            # Find or create the folder
            folder_id = None
            query = f"mimeType='application/vnd.google-apps.folder' and name='{drive_folder_name}' and trashed=false"
            response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            if response.get('files'):
                folder_id = response.get('files')[0].get('id')
            else:
                file_metadata = {'name': drive_folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
            
            file_metadata = {'name': os.path.basename(local_filepath), 'parents': [folder_id]}
            media = MediaFileUpload(local_filepath, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            logger.info(f"File '{os.path.basename(local_filepath)}' uploaded to Google Drive folder '{drive_folder_name}'. File ID: {file.get('id')}")
            return file.get('webViewLink') # Return the web view link
        except HttpError as error:
            logger.error(f"An HTTP error occurred during Google Drive upload: {error.resp.status} - {error._get_reason()}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Google Drive upload: {e}", exc_info=True)
        return None