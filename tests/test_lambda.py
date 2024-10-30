import sys
import os
import json
import time
from unittest.mock import AsyncMock

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.slack_bot import process_message_event
from app.assistants.dispatcher import Dispatcher
from app.config.config_manager import ConfigManager
from utils.logger import logger
import pytest
from test_auth_flow import setup_test_credentials

class MockSlackSay:
    async def __call__(self, *args, **kwargs):
        text = kwargs.get('text', args[0] if args else '')
        logger.info(f"Assistant: {text}")

@pytest.mark.asyncio
async def test_lambda():
    # Initialize components
    config_manager = ConfigManager()
    dispatcher = Dispatcher()
    slack_say = MockSlackSay()

    # Set up test credentials and ensure we get a valid user ID
    test_user_id = setup_test_credentials()
    if not test_user_id:
        logger.error("Failed to set up test credentials")
        return
    
    logger.info(f"Test initialized with user_id: {test_user_id}")

    # Modified test message with user ID
    event = {
        "text": "send an email to test@test.com with the subject 'Test Email' and the body 'This is a test email'",
        "user": test_user_id,
        "channel": "C789012",
        "team_id": "T123456"
    }

    try:
        # Set user context before processing
        logger.debug(f"Setting dispatcher user context to: {test_user_id}")
        dispatcher.set_user_context(test_user_id)
        
        # Process the message event
        logger.debug("Processing message event")
        await process_message_event(event, slack_say, dispatcher)
        logger.info("✅ Lambda handler test completed successfully")
    except Exception as e:
        logger.error(f"❌ Lambda handler test failed: {e}")
        logger.error(f"Event data: {event}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_lambda())