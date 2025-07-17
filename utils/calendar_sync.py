# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\calendar_sync.py
import os.path
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.localization import _ # For potential error messages

logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_PATH = 'config/token.json'  # Store token in a 'config' subdirectory
CREDENTIALS_PATH = 'config/credentials.json' # Path to your OAuth client secrets file

class GoogleCalendarSync:
    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.service: Optional[Any] = None
        self._load_credentials()

    def _load_credentials(self):
        """Loads existing credentials or initiates authentication if needed."""
        if os.path.exists(TOKEN_PATH):
            try:
                self.creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception as e:
                logger.error(f"Error loading token from {TOKEN_PATH}: {e}")
                self.creds = None # Ensure creds is None if loading fails

        if self.creds and self.creds.valid:
            try:
                self.service = build('calendar', 'v3', credentials=self.creds)
                logger.info("Google Calendar service built with existing valid credentials.")
            except Exception as e:
                logger.error(f"Error building Google Calendar service with existing credentials: {e}")
                self.service = None
        # If there are no (valid) credentials available, let the user log in.
        # The actual login flow will be triggered by authenticate()

    def authenticate(self) -> bool:
        """Initiates the OAuth 2.0 authentication flow."""
        flow = None
        try:
            if not os.path.exists(CREDENTIALS_PATH):
                logger.error(f"Credentials file not found at {CREDENTIALS_PATH}. Cannot authenticate.")
                # In a GUI, you'd show a message to the user.
                raise FileNotFoundError(_("gdrive_credentials_not_found_error", path=CREDENTIALS_PATH))

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # Note: For desktop apps, redirect_uri is often 'urn:ietf:wg:oauth:2.0:oob' or a local server.
            # The port for run_local_server can be 0 to pick an available port.
            self.creds = flow.run_local_server(port=0)
        except FileNotFoundError as fnf_err:
            logger.error(f"Credentials file error: {fnf_err}")
            raise # Re-raise to be caught by the caller
        except Exception as e:
            logger.error(f"Error during Google Calendar authentication flow: {e}", exc_info=True)
            self.creds = None # Ensure creds is None on failure
            return False

        if self.creds:
            # Save the credentials for the next run
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            with open(TOKEN_PATH, 'w') as token_file:
                token_file.write(self.creds.to_json())
            try:
                self.service = build('calendar', 'v3', credentials=self.creds)
                logger.info("Google Calendar service built successfully after authentication.")
                return True
            except Exception as e:
                logger.error(f"Error building Google Calendar service after authentication: {e}")
                self.service = None
        return False

    def is_authenticated(self) -> bool:
        """Checks if current credentials are valid."""
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                # Re-save the refreshed token
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(self.creds.to_json())
                self.service = build('calendar', 'v3', credentials=self.creds) # Rebuild service
                logger.info("Google Calendar credentials refreshed.")
            except Exception as e:
                logger.error(f"Failed to refresh Google Calendar credentials: {e}")
                self.creds = None
                self.service = None
                return False
        return bool(self.creds and self.creds.valid and self.service)

    def get_user_email(self) -> Optional[str]:
        """Gets the email of the authenticated user."""
        if not self.is_authenticated() or not self.service:
            return None
        try:
            calendar_list_entry = self.service.calendarList().get(calendarId='primary').execute()
            return calendar_list_entry.get('id') # The 'id' field is usually the email for the primary calendar
        except HttpError as e:
            logger.error(f"Error fetching user's primary calendar (for email): {e}")
            return None

    def create_event(self, summary: str, start_datetime_iso: str, end_datetime_iso: str,
                     description: Optional[str] = None, attendees_emails: Optional[List[str]] = None,
                     timezone: str = 'UTC') -> Optional[str]:
        """
        Creates an event on the user's primary Google Calendar.
        Args:
            summary (str): Title of the event.
            start_datetime_iso (str): Start datetime in ISO format (e.g., "2023-12-25T09:00:00").
            end_datetime_iso (str): End datetime in ISO format (e.g., "2023-12-25T10:00:00").
            description (Optional[str]): Description of the event.
            attendees_emails (Optional[List[str]]): List of attendee email addresses.
            timezone (str): Timezone for the event, e.g., 'America/New_York', 'Europe/London', or 'UTC'.
                            It's best to get this from user settings or system.
        Returns:
            Optional[str]: The ID of the created event, or None if failed.
        """
        if not self.is_authenticated() or not self.service:
            logger.error("Cannot create event: Not authenticated with Google Calendar.")
            return None

        event_body: Dict[str, Any] = {
            'summary': summary,
            'location': '', # Optional: Add location if available
            'description': description or '',
            'start': {
                'dateTime': start_datetime_iso,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime_iso,
                'timeZone': timezone,
            },
            'reminders': { # Default reminders
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60}, # 1 day before
                    {'method': 'popup', 'minutes': 30},      # 30 mins before
                ],
            },
        }
        if attendees_emails:
            event_body['attendees'] = [{'email': email} for email in attendees_emails]

        try:
            created_event = self.service.events().insert(calendarId='primary', body=event_body).execute()
            logger.info(f"Google Calendar event created: {created_event.get('htmlLink')}")
            return created_event.get('id')
        except HttpError as error:
            logger.error(f"An API error occurred creating Google Calendar event: {error.resp.status} - {error._get_reason()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Google Calendar event: {e}", exc_info=True)
            return None

    def disconnect(self):
        """Removes the stored token, effectively disconnecting the user."""
        if os.path.exists(TOKEN_PATH):
            try:
                os.remove(TOKEN_PATH)
                logger.info(f"Token file {TOKEN_PATH} removed. User disconnected.")
            except OSError as e:
                logger.error(f"Error removing token file {TOKEN_PATH}: {e}")
        self.creds = None
        self.service = None