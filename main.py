import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.slack_bot import create_slack_bot
from utils.logger import logger
from app.assistants.assistant_manager import AssistantManager
from app.assistants.dispatcher import Dispatcher
from app.assistants.assistant_factory import AssistantFactory
from app.google_client import initialize_google_auth  # Add this import
from app.config.assistant_config import AssistantConfig, AssistantCategory

async def update_assistants():
    logger.debug("Updating assistants...")
    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()
    assistant_factory = AssistantFactory()
    
    assistants = await assistant_manager.list_assistants()
    
    for assistant_name in AssistantConfig.get_all_assistant_names():
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
            if assistant_name == AssistantConfig.ASSISTANT_NAMES[AssistantCategory.CLASSIFIER]:
                dispatcher.classifier_assistant_id = new_assistant.id
    
    logger.debug("Assistants update completed")

async def setup():

    # Initialize Google authentication
    initialize_google_auth() 
    # Update assistants
    await update_assistants()

    # Set up and initialize Slack app
    slack_app = create_slack_bot()
    return slack_app

def main():
    # Run the setup in the asyncio event loop
    slack_app = asyncio.get_event_loop().run_until_complete(setup())

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")
    slack_app.start(port=3000)

if __name__ == "__main__":
    main()