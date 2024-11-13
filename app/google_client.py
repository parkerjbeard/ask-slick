from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from app.config.settings import settings
from typing import List, Optional, Dict
from utils.user_id import UserIDManager
from datetime import datetime, timezone
from utils.logger import logger
import boto3
import json
import os
import secrets
import base64

class GoogleAuthManager:
    def __init__(self):
        self.kms_client = boto3.client('kms')
        self.kms_key_id = settings.KMS_KEY_ID
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('user_manifests')
        self.scopes: List[str] = []
        self.credentials_store: Dict[str, Dict[str, object]] = {}

    def add_scope(self, scope: str):
        if scope not in self.scopes:
            self.scopes.append(scope)

    def initialize_default_scopes(self):
        """Initialize default scopes if none are set"""
        unique_scopes = {
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.modify'
        }
        self.scopes = list(unique_scopes)

    def create_auth_flow(self) -> Flow:
        """Create OAuth2 flow for Google authentication"""
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
            }
        }

        if not self.scopes:
            self.initialize_default_scopes()

        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return flow

    async def exchange_code(self, code: str) -> Credentials:
        """Exchange authorization code for credentials"""
        try:
            flow = self.create_auth_flow()

            if 'openid' not in self.scopes:
                self.add_scope('openid')

            flow.fetch_token(
                code=code,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )

            return flow.credentials

        except Exception as e:
            logger.error(f"Error exchanging code: {repr(e)}")
            if hasattr(e, 'token'):
                scopes = e.token.get('scope', '').split()
                return Credentials(
                    token=e.token['access_token'],
                    refresh_token=e.token.get('refresh_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                    scopes=scopes or self.scopes
                )
            raise

    def _generate_state_token(self) -> str:
        """Generate a secure state token for OAuth flow"""
        return secrets.token_urlsafe(32)

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

            plaintext = json.dumps(manifest).encode('utf-8')
            encrypted_data = self.kms_client.encrypt(
                KeyId=self.kms_key_id,
                Plaintext=plaintext
            )['CiphertextBlob']

            # Store the binary data directly
            item = {
                'user_id': normalized_user_id,
                'manifest_data': encrypted_data,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            self.table.put_item(Item=item)
            logger.info(f"Saved encrypted credentials for user {normalized_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {type(e).__name__}({str(e)})")
            return False

    async def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get credentials for a specific user"""
        try:
            normalized_user_id = UserIDManager.normalize_user_id(user_id)
            response = self.table.get_item(Key={'user_id': normalized_user_id})
            if 'Item' not in response:
                logger.info(f"No credentials found for user {normalized_user_id}")
                return None

            encrypted_data_b64 = response['Item']['manifest_data']
            decrypted_data = self._decrypt_data(encrypted_data_b64)

            manifest = json.loads(decrypted_data)
            credentials = Credentials(
                token=manifest['token'],
                refresh_token=manifest.get('refresh_token'),
                token_uri=manifest['token_uri'],
                client_id=manifest['client_id'],
                client_secret=manifest['client_secret'],
                scopes=manifest['scopes']
            )

            if not credentials.valid and credentials.refresh_token:
                credentials.refresh(Request())
                self.save_credentials(normalized_user_id, credentials)

            return credentials
        except Exception as e:
            logger.error(f"Error getting credentials: {repr(e)}")
            return None

    def _decrypt_data(self, encrypted_data_b64: str) -> str:
        """Decrypt base64-encoded encrypted data"""
        try:
            # Convert from DynamoDB Binary type if necessary
            if hasattr(encrypted_data_b64, 'value'):
                encrypted_data = encrypted_data_b64.value
            else:
                encrypted_data = base64.b64decode(encrypted_data_b64)
                
            decrypted_response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_data
            )
            decrypted_data = decrypted_response['Plaintext'].decode('utf-8')
            return decrypted_data
        except Exception as e:
            logger.error(f"Error decrypting data: {type(e).__name__}({str(e)})")
            raise

    def get_service(self, user_id: str, api_name: str, api_version: str):
        """Get a Google service client for a specific user"""
        service_key = f"{api_name}_{api_version}"
        user_services = self.credentials_store.setdefault(user_id, {})

        if service_key not in user_services:
            credentials = self.get_credentials(user_id)
            if not credentials:
                raise Exception(f"No valid credentials for user {user_id}")

            service = build(api_name, api_version, credentials=credentials)
            user_services[service_key] = service

        return user_services[service_key]

    def get_auth_url(self) -> str:
        """Get the authorization URL for Google OAuth"""
        flow = self.create_auth_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

    def get_scopes(self) -> List[str]:
        """Get the currently configured scopes"""
        return self.scopes.copy()

# Create a global instance
google_auth_manager = GoogleAuthManager()

def initialize_google_auth():
    """Initialize scopes for Google authentication"""
    google_auth_manager.scopes = []
    default_scopes = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/calendar'
    ]
    for scope in default_scopes:
        google_auth_manager.add_scope(scope)

def get_google_service(user_id: str, api_name: str, api_version: str = None):
    """Helper function to get a Google service for a specific user"""
    api_version = api_version or settings.GOOGLE_API_VERSION
    return google_auth_manager.get_service(user_id, api_name, api_version)