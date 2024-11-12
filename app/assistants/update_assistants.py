from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from app.config.assistant_config import AssistantCategory
from app.config.config_manager import ConfigManager
from app.assistants.dispatcher import Dispatcher
from utils.logger import logger
import asyncio

async def update_assistants(config_manager):
    logger.info("Starting assistant update process...")
    assistant_manager = AssistantManager(config_manager)
    dispatcher = Dispatcher()
    assistant_factory = AssistantFactory()
    
    logger.info("Fetching existing assistants...")
    assistants = await assistant_manager.list_assistants()
    logger.info(f"Found {len(assistants)} existing assistants")
    
    update_tasks = [
        update_single_assistant(
            assistant_manager,
            assistant_factory,
            config_manager,
            dispatcher,
            assistant_name,
            assistants.get(assistant_name)
        )
        for assistant_name in config_manager.get_assistant_names().values()
    ]
    
    await asyncio.gather(*update_tasks)
    logger.info("Assistant update process completed successfully")

async def update_single_assistant(
    assistant_manager, 
    assistant_factory, 
    config_manager, 
    dispatcher, 
    assistant_name, 
    assistant_id
):
    logger.info(f"Processing assistant: {assistant_name}")
    
    tools, model = assistant_factory.get_tools_for_assistant(assistant_name, "system")
    instructions = assistant_factory.get_assistant_instructions(assistant_name, "system")
    
    if assistant_id:
        await assistant_manager.update_assistant(
            assistant_id=assistant_id,
            instructions=instructions,
            tools=tools
        )
    else:
        logger.info(f"Creating new assistant: {assistant_name}")
        new_assistant = await assistant_manager.create_assistant(
            name=assistant_name,
            instructions=instructions,
            tools=tools,
            model=model
        )
        logger.info(f"Successfully created {assistant_name} with ID: {new_assistant.id}")
        if assistant_name == config_manager.get_assistant_names()[AssistantCategory.CLASSIFIER]:
            logger.info(f"Setting classifier assistant ID to: {new_assistant.id}")
            dispatcher.classifier_assistant_id = new_assistant.id