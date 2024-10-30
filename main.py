from dotenv import load_dotenv
load_dotenv()

from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from app.config.assistant_config import AssistantCategory
from app.google_client import initialize_google_auth
from app.config.config_manager import ConfigManager
from app.assistants.dispatcher import Dispatcher
from app.slack_bot import create_slack_bot
from app.config.settings import settings
from utils.logger import logger
import asyncio

async def update_assistants(config_manager):
    logger.debug("Updating assistants...")
    assistant_manager = AssistantManager(config_manager)
    dispatcher = Dispatcher()
    assistant_factory = AssistantFactory()
    
    assistants = await assistant_manager.list_assistants()
    
    for assistant_name in config_manager.get_assistant_names().values():
        assistant_id = assistants.get(assistant_name)
        tools, model = assistant_factory.get_tools_for_assistant(assistant_name)
        instructions = assistant_factory.get_assistant_instructions(assistant_name)
        
        
        if assistant_id:
            await assistant_manager.update_assistant(
                assistant_id=assistant_id,
                instructions=instructions,
                tools=tools
            )
            logger.debug(f"Updated {assistant_name} with new tools and instructions")
        else:
            logger.debug(f"{assistant_name} not found, creating a new one")
            new_assistant = await assistant_manager.create_assistant(
                name=assistant_name,
                instructions=instructions,
                tools=tools,
                model=model
            )
            if assistant_name == config_manager.get_assistant_names()[AssistantCategory.CLASSIFIER]:
                dispatcher.classifier_assistant_id = new_assistant.id
        
        logger.debug("Assistants update completed")

async def setup():
    # Initialize Google authentication
    initialize_google_auth()

    # Verify KMS key is available
    if not settings.KMS_KEY_ID:
        raise ValueError("KMS_KEY_ID setting is required")

    config_manager = ConfigManager()
    await update_assistants(config_manager)

    # Set up and initialize Slack app
    app = create_slack_bot(config_manager)
    logger.debug(f"Slack app created, type: {type(app)}")
    return app

# Lambda handler function
def lambda_handler(event, context):
    try:
        logger.debug("Lambda handler started")
        
        # Initialize Google auth and config manager
        initialize_google_auth()
        config_manager = ConfigManager()
        
        # Create single event loop for all async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create Slack app with all initialization in one go
        slack_app = loop.run_until_complete(setup())
        
        # Create handler and process event
        handler = SlackRequestHandler(slack_app)
        return handler.handle(event, context)
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        loop.close()