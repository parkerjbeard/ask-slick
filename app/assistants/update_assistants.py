from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from app.config.assistant_config import AssistantCategory
from app.assistants.dispatcher import Dispatcher
from utils.logger import logger

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