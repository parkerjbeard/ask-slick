from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from app.config.settings import settings
from typing import List, Dict, Optional
from utils.user_id import UserIDManager
from utils.logger import logger
from dotenv import load_dotenv
from datetime import datetime
import boto3
import json
import os



load_dotenv()

class GoogleAuthManager:
    def __init__(self):
        self.kms_client = boto3.client('kms')
        self.kms_key_id = settings.KMS_KEY_ID
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('user_manifests')
        self.scopes: List[str] = []
        self.services: Dict[str, Dict[str, any]] = {}  # nested dict for user-specific services

    def add_scope(self, scope: str):
        if scope not in self.scopes:
            self.scopes.append(scope)

    def create_auth_flow(self) -> Flow:
        """Create OAuth flow for initial authentication"""
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
            }
        }
        flow = Flow.from_client_config(client_config, scopes=self.scopes)
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        return flow

    def save_credentials(self, user_id: str, credentials: Credentials) -> bool:
        """Save user credentials to DynamoDB with encryption"""
        try:
            normalized_user_id = UserIDManager.normalize_user_id(user_id)
            manifest = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            encrypted_data = self.kms_client.encrypt(
                KeyId=self.kms_key_id,
                Plaintext=json.dumps(manifest).encode()
            )['CiphertextBlob']
            
            item = {
                'user_id': normalized_user_id,
                'manifest_data': encrypted_data,
                'updated_at': datetime.utcnow().isoformat()
            }
            self.table.put_item(Item=item)
            logger.info(f"Saved encrypted credentials for user {normalized_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False

    def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get user credentials from DynamoDB with decryption"""
        try:
            normalized_user_id = UserIDManager.normalize_user_id(user_id)
            response = self.table.get_item(Key={'user_id': normalized_user_id})
            if 'Item' not in response:
                logger.info(f"No credentials found for user {normalized_user_id}")
                return None

            decrypted_data = self.kms_client.decrypt(
                CiphertextBlob=bytes(response['Item']['manifest_data']),
                KeyId=self.kms_key_id
            )['Plaintext']
            
            if isinstance(decrypted_data, bytes):
                decrypted_data = decrypted_data.decode('utf-8')
                
            manifest = json.loads(decrypted_data)
            credentials = Credentials(
                token=manifest['token'],
                refresh_token=manifest['refresh_token'],
                token_uri=manifest['token_uri'],
                client_id=manifest['client_id'],
                client_secret=manifest['client_secret'],
                scopes=manifest['scopes']
            )

            # Refresh if needed
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    self.save_credentials(normalized_user_id, credentials)
                else:
                    return None

            return credentials
        except Exception as e:
            logger.error(f"Error getting credentials: {str(e)}")
            return None

    def get_service(self, user_id: str, api_name: str, api_version: str):
        """Get a Google service client for a specific user"""
        service_key = f"{api_name}_{api_version}"
        user_services = self.services.get(user_id, {})

        if service_key not in user_services:
            credentials = self.get_credentials(user_id)
            if not credentials:
                raise Exception(f"No valid credentials for user {user_id}")

            try:
                service = build(api_name, api_version, credentials=credentials)
                if user_id not in self.services:
                    self.services[user_id] = {}
                self.services[user_id][service_key] = service
            except HttpError as error:
                logger.error(f"Error building {api_name} service: {error}")
                raise

        return self.services[user_id][service_key]

    def get_auth_url(self) -> str:
        """Get the authorization URL for Google OAuth"""
        flow = self.create_auth_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

# Create a global instance
google_auth_manager = GoogleAuthManager()

def initialize_google_auth():
    """Initialize scopes for Google authentication"""
    google_auth_manager.add_scope('https://www.googleapis.com/auth/calendar')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.compose')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.modify')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/gmail.send')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/userinfo.email')
    google_auth_manager.add_scope('https://www.googleapis.com/auth/userinfo.profile')
    logger.info("Google authentication scopes initialized")

def get_google_service(user_id: str, api_name: str, api_version: str = None):
    """Helper function to get a Google service for a specific user"""
    if api_version is None:
        api_version = settings.GOOGLE_API_VERSION
    return google_auth_manager.get_service(user_id, api_name, api_version)