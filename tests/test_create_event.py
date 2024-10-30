import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.assistants.update_assistants import update_assistants
from dotenv import load_dotenv
import asyncio
import pytest
import time
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

from app.slack_bot import process_message_event
from app.assistants.dispatcher import Dispatcher
from app.config.config_manager import ConfigManager
from utils.logger import logger
from app.google_client import initialize_google_auth
from app.services.calendar.calendar_manager import CalendarManager

class MockSlackSay:
    """
    A mock class to simulate Slack's say function for testing purposes.
    """
    async def __call__(self, *args, **kwargs):
        # Extract the text from args or kwargs and log it
        text = kwargs.get('text', args[0] if args else '')
        logger.info(f"Assistant: {text}")

@pytest.mark.asyncio
async def test_create_event():
    """
    Main function to run calendar integration tests.
    """
    logger.info("Starting create event test")
    start_time = time.time()

    # Initialize necessary components for testing
    initialize_google_auth()
    
    calendar_manager = CalendarManager()
    config_manager = ConfigManager()
    dispatcher = Dispatcher()
    slack_say = MockSlackSay()
    await update_assistants(config_manager)

    # Define test cases
    test_cases = [

        {
            "name": "Create Event",
            "text": "create an event with the title 'Test Event' on 2024-11-01 at 3pm for 1 hour with a description 'This is a test event'"
        },


        # Add more test cases here if needed
    ]

    # Run each test case
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"Processing test case {i}: {test_case['name']}")
        event = {
            "text": test_case['text'],
            "user": "U123456",
            "channel": "C789012"
        }
        try:
            # Process the message event using the Slack bot's function
            await process_message_event(event, slack_say, dispatcher)
        except Exception as e:
            logger.error(f"Error processing test case {i}: {str(e)}", exc_info=True)

    # Log the total time taken for the tests
    logger.info(f"Create event tests completed in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_create_event())