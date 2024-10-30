import os
import sys
from pathlib import Path
import time

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

class CallbackHandler(BaseHTTPRequestHandler):
    received_code = None
    
    def do_GET(self):
        CallbackHandler.received_code = self.path
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Authorization received! You can close this window.")

def start_local_server():
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server

def test_auth_flow():
    # Update to use localhost instead of ngrok
    LOCAL_REDIRECT_URI = "http://localhost:8080"
    settings.GOOGLE_REDIRECT_URI = LOCAL_REDIRECT_URI
    
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
    
    # 1. Test initialization
    try:
        initialize_google_auth()
        logger.info("✅ Google auth initialization successful")
    except Exception as e:
        logger.error(f"❌ Google auth initialization failed: {e}")
        return

    # 2. Test auth flow creation
    try:
        flow = google_auth_manager.create_auth_flow()
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        logger.info("✅ Auth flow creation successful")
        logger.info(f"Auth URL: {auth_url}")
        
        # Optional: automatically open the auth URL
        webbrowser.open(auth_url)
    except Exception as e:
        logger.error(f"❌ Auth flow creation failed: {e}")
        return

    # 3. Test credentials storage (improved auth code handling)
    print("\nInstructions:")
    print("1. Copy the FULL callback URL after authentication")
    print("2. The code should be in the URL as '?code=<auth_code>'\n")
    
    server = start_local_server()
    try:
        # Wait for the auth code
        while not CallbackHandler.received_code:
            time.sleep(1)
        callback_url = f"{LOCAL_REDIRECT_URI}{CallbackHandler.received_code}"
        
        # Extract code from callback URL with better URL parsing
        if "?" in callback_url:
            # Parse the URL and extract the code parameter
            parsed_url = urlparse(callback_url)
            params = parse_qs(parsed_url.query)
            
            if 'code' not in params:
                logger.error("No code parameter found in URL")
                return
                
            auth_code = params['code'][0]  # get first code value
        else:
            auth_code = callback_url.strip()
            
        logger.info(f"Extracted auth code: {auth_code[:10]}...")
        
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Test saving credentials
        test_user_id = "test_user_123"
        success = google_auth_manager.save_credentials(test_user_id, credentials)
        if success:
            logger.info(f"✅ Credentials saved successfully for user {test_user_id}")
        else:
            logger.error("❌ Failed to save credentials")
            return

        # Test retrieving credentials
        retrieved_creds = google_auth_manager.get_credentials(test_user_id)
        if retrieved_creds and retrieved_creds.valid:
            logger.info("✅ Credentials retrieved and valid")
        else:
            if retrieved_creds is None:
                logger.error("❌ No credentials found")
            else:
                logger.error("❌ Retrieved credentials are invalid")
            return

        # Test Google API access
        calendar_service = google_auth_manager.get_service(
            test_user_id, 
            "calendar", 
            "v3"
        )
        events = calendar_service.events().list(
            calendarId='primary',
            maxResults=1
        ).execute()
        
        logger.info("✅ Successfully accessed Google Calendar API")
        logger.info(f"Found {len(events.get('items', []))} events")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        server.shutdown()

def setup_test_credentials():
    """Helper function to ensure test credentials exist and return test user ID"""
    test_user_id = "test_user_123"
    
    try:
        # Check if credentials already exist
        existing_creds = google_auth_manager.get_credentials(test_user_id)
        if existing_creds and existing_creds.valid:
            logger.info("✅ Using existing test credentials")
            return test_user_id
            
        # If no valid credentials exist, run the auth flow
        logger.info("No valid credentials found. Running auth flow...")
        test_auth_flow()
        
        # Verify credentials were created successfully
        if google_auth_manager.get_credentials(test_user_id):
            return test_user_id
        else:
            logger.error("Failed to create test credentials")
            return None
            
    except Exception as e:
        logger.error(f"Error setting up test credentials: {e}")
        return None

if __name__ == "__main__":
    test_auth_flow()