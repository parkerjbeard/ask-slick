from dotenv import load_dotenv
load_dotenv()

from app.assistants.update_assistants import update_assistants
from app.google_client import initialize_google_auth
from app.config.config_manager import ConfigManager
from app.google_client import google_auth_manager
from app.slack_bot import create_slack_bot, AsyncSlackRequestHandler
from app.config.settings import settings
from app.user_setup import UserSetup
from app.oauth_handler import OAuthHandler
from utils.logger import logger
import asyncio
import json
import traceback

# Global variable for the Slack app
slack_app = None

async def setup():
    logger.info("Starting system setup...")
    
    global slack_app
    if slack_app is None:
        config_manager = ConfigManager()
        slack_app = create_slack_bot(config_manager)
    
    return slack_app

def lambda_handler(event, context):
    """Synchronous wrapper for async handler"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_async_handler(event, context))

async def _async_handler(event, context):
    try:
        # Check if this is an OAuth callback
        if event.get('requestContext', {}).get('http', {}).get('method') == 'GET' and \
           event.get('rawPath', '').endswith('/oauth/callback'):
            oauth_handler = OAuthHandler()
            return await oauth_handler.handle_oauth_callback(event)

        # Check if this is a retry attempt
        headers = event.get('headers', {})
        if 'x-slack-retry-num' in headers:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Retry request ignored'}),
                'headers': {'Content-Type': 'application/json'}
            }

        body = event.get('body')
        if body:
            try:
                if isinstance(body, str):
                    body = json.loads(body)
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse request body: {str(je)}")
                raise
            
            if body.get('type') == 'url_verification':
                return {
                    'statusCode': 200,
                    'body': json.dumps({'challenge': body.get('challenge')}),
                    'headers': {'Content-Type': 'application/json'}
                }
        
        slack_app = await setup()
        handler = AsyncSlackRequestHandler(slack_app)
        return await handler.handle(event, context)
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }