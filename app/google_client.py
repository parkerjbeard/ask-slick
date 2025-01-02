from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from app.config.settings import settings
from typing import List, Optional, Dict
from utils.user_id import UserIDManager
from datetime import datetime, timezone, timedelta
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
        self.state_table = self.dynamodb.Table('oauth_states')
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

        )

        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return flow

    async def exchange_code(self, code: str, state: str) -> Credentials:
        """Exchange authorization code for credentials"""
        try:
            flow = self.create_auth_flow()
            flow.state = state

            # Add debug logging for OAuth parameters
            logger.debug(f"OAuth Exchange Parameters:")
            logger.debug(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
            logger.debug(f"State Token: {state}")
            logger.debug(f"Scopes: {self.scopes}")

            if 'openid' not in self.scopes:
                self.add_scope('openid')

            flow.fetch_token(code=code)
            return flow.credentials

        except Exception as e:
            logger.error(f"Error exchanging code: {repr(e)}")
            # Add error context logging
            logger.error(f"Failed OAuth parameters - Redirect URI: {settings.GOOGLE_REDIRECT_URI}, State: {state}, Scopes: {self.scopes}")
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

    def get_auth_url(self, user_id: str) -> str:
        """Get the authorization URL for Google OAuth with user tracking"""
        flow = self.create_auth_flow()
        state_token = self._generate_state_token()
        
        # Store state token with user ID
        self.state_table.put_item(Item={
            'state_token': state_token,
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        })
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state_token  # Include state token in URL
        )
        return auth_url

    async def verify_state_token(self, state_token: str) -> Optional[str]:
        """Verify state token and return associated user_id"""
        try:
            response = self.state_table.get_item(Key={'state_token': state_token})
            if 'Item' not in response:
                logger.error(f"No state token found: {state_token}")
                return None
                
            item = response['Item']
            expires_at = datetime.fromisoformat(item['expires_at'])
            
            if datetime.now(timezone.utc) > expires_at:
                logger.error(f"State token expired: {state_token}")
                return None
                
            # Clean up used token
            self.state_table.delete_item(Key={'state_token': state_token})
            return item['user_id']
            
        except Exception as e:
            logger.error(f"Error verifying state token: {repr(e)}")
            return None

    def get_scopes(self) -> List[str]:
        """Get the currently configured scopes"""
        return self.scopes.copy()

    async def process_oauth_callback(self, auth_code: str, user_id: str, state: str) -> bool:
        """Process OAuth callback and save credentials"""
        try:
            credentials = await self.exchange_code(auth_code, state)
            return self.save_credentials(user_id, credentials)
        except Exception as e:
            logger.error(f"Error processing OAuth callback: {repr(e)}")
            return False

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