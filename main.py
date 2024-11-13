from dotenv import load_dotenv
load_dotenv()

from app.assistants.update_assistants import update_assistants
from app.google_client import initialize_google_auth
from app.config.config_manager import ConfigManager
from app.google_client import google_auth_manager
from app.slack_bot import create_slack_bot, AsyncSlackRequestHandler
from app.config.settings import settings
from app.user_setup import UserSetup
from utils.logger import logger
import asyncio
import json

# Global variable for the Slack app
slack_app = None

async def setup():
    logger.info("Starting system setup...")
    
    # Basic system setup
    global slack_app
    if slack_app is None:
        config_manager = ConfigManager()
        slack_app = create_slack_bot(config_manager)
    
    return slack_app

# Lambda handler function
def lambda_handler(event, context):
    try:
        logger.info("Lambda handler started")
        logger.debug(f"Event: {event}")

        # Check if this is a retry attempt
        headers = event.get('headers', {})
        if 'x-slack-retry-num' in headers:
            logger.info("Skipping retry attempt")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Retry request ignored'}),
                'headers': {'Content-Type': 'application/json'}
            }

        body = event.get('body')
        if body:
            if isinstance(body, str):
                logger.debug("Parsing string body to JSON")
                body = json.loads(body)
                logger.debug(f"Parsed body: {body}")
            
            if body.get('type') == 'url_verification':
                logger.info("Processing URL verification challenge")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'challenge': body.get('challenge')}),
                    'headers': {'Content-Type': 'application/json'}
                }
        
        logger.info("Setting up async event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            logger.info("Initializing Slack app...")
            slack_app = loop.run_until_complete(setup())
            logger.info("Creating AsyncSlackRequestHandler and processing event...")
            handler = AsyncSlackRequestHandler(slack_app)
            response = loop.run_until_complete(handler.handle(event, context))
            logger.info("Event processed successfully")
            return response
        finally:
            logger.debug("Closing event loop")
            loop.close()
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }