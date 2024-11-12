from app.config.assistant_config import AssistantCategory, AssistantConfig
from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from app.config.config_manager import ConfigManager
from app.assistants.classifier import Classifier
from utils.user_id import UserIDManager
from utils.logger import logger
from typing import List
import json
from datetime import datetime, timezone
from utils.thread_store import ThreadStore


class Dispatcher:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.assistant_manager = AssistantManager(self.config_manager)
        self.classifier = Classifier(self.assistant_manager, self.config_manager)
        self.current_category = None
        self.thread_store = ThreadStore()
        self.user_id = None
        
    def set_user_context(self, user_id: str):
        """Set the user context for the dispatcher"""
        self.user_id = UserIDManager.normalize_user_id(user_id)

    async def dispatch(self, user_input: str, user_id: str = None) -> dict:
        try:
            logger.info(f"Starting dispatch for user input: {user_input} with user_id: {user_id}")
            if not user_id:
                raise ValueError("user_id is required for message dispatch")
            
            normalized_user_id = UserIDManager.normalize_user_id(user_id)
            self.user_id = normalized_user_id
            
            # Get thread from DynamoDB
            thread_id = await self.thread_store.get_thread(normalized_user_id)
            
            self.current_category = await self.classifier.classify_message(user_input)
            
            assistant_name = AssistantConfig.get_assistant_name(self.current_category)
            logger.info(f"Selected assistant: {assistant_name}")
            
            chat_history = await self.get_chat_history(thread_id)
            assistant_id = await self.assistant_manager.create_or_get_assistant(assistant_name)
            
            if not thread_id:
                thread = await self.assistant_manager.create_thread()
                thread_id = thread.id
                await self.thread_store.store_thread(normalized_user_id, thread_id)
            else:
                # Update last_used timestamp
                await self.thread_store.update_last_used(normalized_user_id)
            
            await self.assistant_manager.create_message(thread_id, "user", user_input)
            run = await self.assistant_manager.create_run(assistant_id=assistant_id, thread_id=thread_id)
            
            return await self.process_run(run, user_input, chat_history, thread_id)
        except Exception as e:
            logger.error(f"Error in dispatch: {str(e)}", exc_info=True)
            return {'thread_id': thread_id if 'thread_id' in locals() else None, 
                   'run_id': None, 
                   'error': str(e)}

    async def process_run(self, run, user_input: str, chat_history: List[str], thread_id: str) -> dict:
        while True:
            run = self.assistant_manager.wait_on_run(thread_id, run.id)
            
            if run.status == "completed":
                logger.debug(f"Run completed: {run.status}")
                assistant_response = await self.assistant_manager.get_assistant_response(thread_id, run.id)
                return {
                    'thread_id': thread_id,
                    'run_id': run.id,
                    'assistant_response': assistant_response
                }
            elif run.status == "requires_action":
                if run.required_action.submit_tool_outputs:
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = await self.handle_tool_calls(tool_calls, user_input)
                    if tool_outputs:
                        try:
                            run = await self.assistant_manager.submit_tool_outputs(thread_id, run.id, tool_outputs)
                        except Exception as e:
                            logger.error(f"Error submitting tool outputs: {e}")
                        else:
                            logger.debug("No tool outputs to submit.")
            else:
                logger.error(f"Unexpected run status: {run.status}")
                return {
                    'thread_id': thread_id,
                    'run_id': run.id,
                    'error': f"Unexpected run status: {run.status}"
                }

    async def handle_tool_calls(self, tool_calls, user_input: str):
        tool_outputs = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            result = await self.call_function(function_name, function_args)

            tool_output = {
                "tool_call_id": tool_call.id,
                "output": result
            }
            tool_outputs.append(tool_output)

        return tool_outputs

    def get_integration_type(self, function_name: str) -> str:
        for category, functions in AssistantConfig.CATEGORY_FUNCTIONS.items():
            if function_name in functions:
                return category.value
        return AssistantCategory.GENERAL.value

    def get_category_from_assistant_name(self, assistant_name: str) -> AssistantCategory:
        for category, config in AssistantConfig.CONFIGS.items():
            if config.ASSISTANT_NAME == assistant_name:
                return category
        return AssistantCategory.GENERAL

    async def call_function(self, function_name: str, function_params: dict) -> str:
        if self.user_id:
            function_params['user_id'] = self.user_id
        else:
            logger.warning("No user_id available in dispatcher")
        
        integration = AssistantFactory.get_api_integration(
            AssistantConfig.get_assistant_name(self.current_category),
            self.user_id
        )
        
        if integration:
            return await integration.execute(function_name, function_params)
        else:
            logger.error(f"No integration found for assistant: {AssistantConfig.get_assistant_name(self.current_category)}")
            return f"Unknown function: {function_name}"
    async def get_chat_history(self, thread_id: str) -> List[str]:
        if not thread_id:
            return []
        messages = await self.assistant_manager.list_messages(thread_id, limit=10, order="desc")
        return [f"{msg.role}: {msg.content[0].text.value}" for msg in reversed(messages.data)]

    async def create_assistant(self, name: str) -> str:
        tools, model = AssistantFactory.get_tools_for_assistant(name)
        assistant = await self.assistant_manager.create_assistant(
            name=name,
            instructions=f"You are a {name}.",
            tools=tools,
            model=model
        )
        return assistant.id

    async def cleanup_old_threads(self, max_age_hours: int = 24):
        """
        Clean up threads older than max_age_hours
        Note: This should be run periodically via a separate Lambda function
        """
        try:
            # Scan DynamoDB for old threads
            scan_response = self.thread_store.table.scan()
            current_time = datetime.now(timezone.utc)
            
            for item in scan_response.get('Items', []):
                last_used = datetime.fromisoformat(item['last_used'])
                age = current_time - last_used
                
                if age.total_seconds() > (max_age_hours * 3600):
                    user_id = item['user_id']
                    thread_id = item['thread_id']
                    
                    # Delete from OpenAI
                    await self.assistant_manager.delete_thread(thread_id)
                    # Delete from DynamoDB
                    await self.thread_store.delete_thread(user_id)
                    
                    logger.debug(f"Cleaned up old thread for user {user_id}")
                    
        except Exception as e:
            logger.error(f"Error during thread cleanup: {e}")