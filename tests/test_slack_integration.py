import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.slack_bot import create_slack_bot, process_message_event
from app.config.config_manager import ConfigManager
from utils.logger import logger
from app.assistants.dispatcher import Dispatcher

async def test_slack_integration():
    try:
        # Test Slack bot creation
        config_manager = ConfigManager()
        app = create_slack_bot(config_manager)
        logger.info("✅ Slack bot created successfully")

        # Test message handling with a mock event
        mock_event = {
            "type": "message",
            "text": "Hello, test message",
            "user": "test_user_123",
            "channel": "test_channel"
        }
        
        # Create a mock say function
        async def mock_say(**kwargs):
            logger.info(f"Would send message: {kwargs}")
        
        # Test the process_message_event function directly
        dispatcher = Dispatcher()
        await process_message_event(mock_event, mock_say, dispatcher)
        logger.info("✅ Message processing test completed")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_slack_integration()) 