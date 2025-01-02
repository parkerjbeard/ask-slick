from app.google_client import google_auth_manager
from app.user_setup import UserSetup
from utils.logger import logger
from typing import Dict, Any
from app.config.settings import settings
import os
from slack_sdk.web.async_client import AsyncWebClient

class OAuthHandler:
    def __init__(self):
        self.user_setup = UserSetup()
    
    async def handle_oauth_callback(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query_params = event.get('queryStringParameters', {})
            code = query_params.get('code')
            state = query_params.get('state')

            verified_user_id = await google_auth_manager.verify_state_token(state)
            if not verified_user_id:
                return create_error_response("Invalid or expired state token")

            credentials = await google_auth_manager.exchange_code(code, state)
            logger.info("Successfully exchanged code for credentials")

            save_result = google_auth_manager.save_credentials(verified_user_id, credentials)
            if not save_result:
                return create_error_response("Failed to save credentials")

            # Mark the user as setup-complete since they've authenticated
            try:
                self.user_setup._save_user_preferences(
                    verified_user_id,
                    {"setup_completed": True}  # This ensures next time they won't be treated as new
                )
                logger.info(f"User {verified_user_id} setup marked complete in DynamoDB after successful auth")
            except Exception as e:
                logger.error(f"Failed to finalize user setup: {e}")

            # Attempt to send the success message to Slack:
            # We must open a DM channel first and then post the message.
            try:
                client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
                
                # Remove any prefix like "slack_"
                slack_user_id = verified_user_id.replace("slack_", "")
                
                im_response = await client.conversations_open(users=slack_user_id)
                channel_id = im_response["channel"]["id"]
                
                await client.chat_postMessage(
                    channel=channel_id,
                    text=":white_check_mark: Google authentication successful! You can now continue using the assistant."
                )
            except Exception as e:
                logger.error(f"Failed to send Slack success message: {e}")

            return create_success_response()

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return create_error_response(str(e))

def create_success_response() -> Dict[str, Any]:
    """Create success HTML response"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Successful</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f8f9fa;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
            }
            h1 { color: #2ea44f; }
            p { color: #444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authentication Successful!</h1>
            <p>You've successfully connected your Google account.</p>
            <p>You can now return to Slack and continue using Slick.</p>
            <script>setTimeout(() => window.close(), 5000);</script>
        </div>
    </body>
    </html>
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-store'
        },
        'body': html
    }

def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create error HTML response"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Error</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f8f9fa;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{ color: #dc3545; }}
            p {{ color: #444; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authentication Error</h1>
            <p>{error_message}</p>
            <p>Please try again or contact support if the problem persists.</p>
        </div>
    </body>
    </html>
    """
    return {
        'statusCode': 500,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }
