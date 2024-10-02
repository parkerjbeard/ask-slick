import os
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from utils.logger import logger
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

class GoogleAuthManager:
    def __init__(self):
        self.credentials_file = '/Users/parkerbeard/BeardoGPT/credentials.json'
        self.token_file = '/Users/parkerbeard/BeardoGPT/token.json'
        self.scopes: List[str] = []
        self.credentials: Credentials = None
        self.services: Dict[str, any] = {}

    def add_scope(self, scope: str):
        if scope not in self.scopes:
            self.scopes.append(scope)

    def authenticate(self):
        try:
            self.credentials = self._get_credentials()
            if not self.credentials:
                raise Exception("Failed to authenticate with Google API")
        except RefreshError as e:
            logger.error(f"Error refreshing credentials: {e}")
            # Delete the token file and try to authenticate again
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            self.credentials = self._get_credentials()
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise

    def _get_credentials(self) -> Credentials:
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)

            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        return creds

    def get_service(self, api_name: str, api_version: str):
        if not self.credentials:
            raise Exception("No credentials available. Please authenticate first.")
        service_key = f"{api_name}_{api_version}"
        if service_key not in self.services:
            try:
                self.services[service_key] = build(api_name, api_version, credentials=self.credentials)
            except HttpError as error:
                logger.error(f"Error building {api_name} service: {error}")
                raise
        return self.services[service_key]

# Create a global instance of GoogleAuthManager
google_auth_manager = GoogleAuthManager()

def initialize_google_auth():
    # Add all required scopes here
    google_auth_manager.add_scope('https://www.googleapis.com/auth/calendar')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.compose')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.modify')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.send')
    
    # Add more scopes as needed for other Google services

    # Authenticate
    google_auth_manager.authenticate()

    logger.info("Google authentication initialized successfully")

def get_google_service(api_name: str, api_version: str):
    return google_auth_manager.get_service(api_name, api_version)