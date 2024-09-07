import sys
import os
import time
import logging
import asyncio
from dotenv import load_dotenv

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

from app.slack_bot import process_message_event
from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from app.config.assistant_config import AssistantConfig, AssistantCategory
from app.assistants.dispatcher import Dispatcher
from app.config.config_manager import ConfigManager
from utils.logger import logger
from app.google_client import initialize_google_auth
from task_decomposition.task_manager import TaskManager
# Set console handler to DEBUG level
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setLevel(logging.DEBUG)

class MockSlackSay:
    async def __call__(self, *args, **kwargs):
        logger.debug(f"MockSlackSay called with args: {args}, kwargs: {kwargs}")
        if args:
            text = args[0]
        else:
            text = kwargs.get('text', '')
        channel = kwargs.get('channel', 'test_channel')
        print(f"Assistant: {text}")

class MockUserInput:
    async def __call__(self, *args, **kwargs):
        user_input = input("User: ")
        return user_input

async def update_assistants():
    logger.debug("Updating assistants...")
    config_manager = ConfigManager()
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

async def complex_task_test():
    logger.debug("Starting complex_task_test")
    start_time = time.time()

    logger.debug("Initializing Google authentication...")
    initialize_google_auth()

    logger.debug("Updating assistants...")
    await update_assistants()

    logger.debug("Initializing components...")
    config_manager = ConfigManager()
    dispatcher = Dispatcher()
    slack_say = MockSlackSay()
    task_manager = TaskManager()
    logger.debug(f"Components initialized in {time.time() - start_time:.2f} seconds")

    print("\nStarting complex task test...")

    # Test cases
    test_cases = [
        {
            "name": "Schedule a Meeting",
            "text": "Schedule a meeting with John and Sarah for next week to discuss the project proposal. Send them an email with the meeting details and add it to my calendar."
        }
    ]

    # Process the test cases
    for i, test_case in enumerate(test_cases, 1):
        logger.debug(f"\nProcessing test case {i}: {test_case['name']}...")
        event = {
            "text": test_case['text'],
            "user": "U123456",
            "channel": "C789012"
        }
        process_start_time = time.time()
        try:
            # Create a mock user input function
            mock_user_input = MockUserInput()
            
            # Create a new task using the TaskManager
            task_result = await task_manager.create_new_task(test_case['text'])
            logger.debug(f"Task created: {task_result}")

            # Process the task using the existing message event handler
            result = await process_message_event(event, slack_say, dispatcher, mock_user_input)
            
            logger.debug(f"Test case {i} processed in {time.time() - process_start_time:.2f} seconds")
            logger.debug(f"Result: {result}")

            # Simulate task execution and status updates
            for subtask in task_result['subtasks']:
                logger.debug(f"Executing subtask: {subtask['subtask']['subtask']}")
                # Simulate subtask execution time
                await asyncio.sleep(1)
                # Update task state
                task_manager.state_manager.set_state(task_result['task_id'], f"In Progress: {subtask['subtask']['subtask']}")

            # Set final task state
            task_manager.state_manager.set_state(task_result['task_id'], "Completed")
            logger.debug(f"Task {task_result['task_id']} completed")

        except Exception as e:
            logger.error(f"Error processing test case {i}: {str(e)}", exc_info=True)

    logger.debug(f"\nComplex task tests completed in {time.time() - start_time:.2f} seconds")

async def main():
    logger.debug("Starting main function")
    await complex_task_test()
    logger.debug("Main function completed")

if __name__ == "__main__":
    logger.debug("Script started")
    asyncio.run(main())
    logger.debug("Script completed")