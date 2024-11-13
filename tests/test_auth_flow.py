import os
import sys
from pathlib import Path
import time
import asyncio

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.google_client import google_auth_manager, initialize_google_auth
from app.config.settings import settings
import webbrowser
from utils.logger import logger
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from utils.user_id import UserIDManager

class CallbackHandler(BaseHTTPRequestHandler):
    received_code = None
    
    def do_GET(self):
        CallbackHandler.received_code = self.path
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Authorization received! You can close this window.")

async def test_auth_flow():
    # Update the redirect URI to match exactly what's configured in Google Cloud Console
    LOCAL_REDIRECT_URI = "https://cuy5utj6me.execute-api.us-east-2.amazonaws.com/ask-slick/oauth/callback"
    settings.GOOGLE_REDIRECT_URI = LOCAL_REDIRECT_URI
    
    logger.info("\n=== OAuth Flow Test Started ===")
    logger.info(f"Using API Gateway endpoint: {LOCAL_REDIRECT_URI}")
    
    # Verify settings first
    required_settings = {
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID,
        'GOOGLE_CLIENT_SECRET': settings.GOOGLE_CLIENT_SECRET,
        'GOOGLE_REDIRECT_URI': settings.GOOGLE_REDIRECT_URI,
        'KMS_KEY_ID': settings.KMS_KEY_ID
    }
    
    missing_settings = [
        setting for setting, value in required_settings.items() 
        if not value
    ]
    
    if missing_settings:
        logger.error(f"❌ Missing required settings: {', '.join(missing_settings)}")
        return
        
    logger.info("✅ All required settings present")
    
    # Initialize Google Auth
    try:
        initialize_google_auth()
        logger.info("✅ Google auth initialization successful")
    except Exception as e:
        logger.error(f"❌ Google auth initialization failed: {e}")
        return

    # Test auth flow creation and URL generation
    try:
        flow = google_auth_manager.create_auth_flow()
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logger.info("=== Auth URL Details ===")
        logger.info(f"State token: {state}")
        logger.info(f"Complete authorization URL: {auth_url}\n")
        
        webbrowser.open(auth_url)
    except Exception as e:
        logger.error(f"❌ Auth flow creation failed: {e}")
        return

    # Update the callback handling instructions
    print("\nImportant Instructions:")
    print("1. After authenticating, you will be redirected to the API Gateway endpoint")
    print("2. The endpoint might show 'Not Found' - this is expected!")
    print("3. Copy the FULL URL from your browser's address bar")
    print("4. Paste it here and press Enter:\n")
    
    callback_url = input("Paste the full callback URL: ").strip()
    
    try:
        # Parse the callback URL
        parsed_url = urlparse(callback_url)
        params = parse_qs(parsed_url.query)
        
        if 'code' not in params:
            logger.error("❌ No authorization code found in the callback URL")
            logger.error(f"Received URL: {callback_url}")
            return
            
        auth_code = params['code'][0]
        received_state = params.get('state', [None])[0]
        
        # Verify state parameter
        if received_state != state:
            logger.error("❌ State parameter mismatch - possible CSRF attack")
            return
            
        logger.info("✅ State parameter verified")
        logger.info(f"✅ Successfully extracted auth code: {auth_code[:10]}...")

        # Test code exchange - now properly awaited
        try:
            credentials = await google_auth_manager.exchange_code(auth_code)
            logger.info("✅ Successfully exchanged code for credentials")
            
            # Test saving credentials
            test_user_id = UserIDManager.normalize_user_id("test_user", "test")
            if google_auth_manager.save_credentials(test_user_id, credentials):
                logger.info("✅ Successfully saved credentials")
            else:
                logger.error("❌ Failed to save credentials")
                return
                
        except Exception as e:
            logger.error(f"❌ Failed to exchange code: {e}")
            return

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

async def setup_test_credentials():
    """Helper function to ensure test credentials exist and return test user ID"""
    test_user_id = UserIDManager.normalize_user_id("test_user", "test")
    
    try:
        # Check if credentials already exist using normalized ID
        existing_creds = google_auth_manager.get_credentials(test_user_id)
        if existing_creds and existing_creds.valid:
            logger.info(f"✅ Using existing test credentials for {test_user_id}")
            return test_user_id
            
        # If no valid credentials exist, run the auth flow
        logger.info("No valid credentials found. Running auth flow...")
        await test_auth_flow()
        
        # Verify credentials were created successfully
        if google_auth_manager.get_credentials(test_user_id):
            logger.info("✅ Test credentials created successfully")
            return test_user_id
        else:
            logger.error("❌ Failed to create test credentials")
            return None
            
    except Exception as e:
        logger.error(f"Error setting up test credentials: {e}")
        return None

# Runner function to execute the async test
def run_test():
    asyncio.run(test_auth_flow())

if __name__ == "__main__":
    run_test()