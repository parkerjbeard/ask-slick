from openai import OpenAI
from app.assistants.assistant_manager import AssistantManager
from app.assistants.assistant_factory import AssistantFactory
from app.assistants.classifier import Classifier
import os
import json
import asyncio
from utils.logger import logger
from typing import List
from app.openai_helper import OpenAIClient
from app.services.travel.search_flight import FlightSearch
from app.services.calendar.calendar_manager import CalendarManager
from app.config.config_manager import ConfigManager
from app.config.assistant_config import AssistantCategory, AssistantConfig

class Dispatcher:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.assistant_manager = AssistantManager(self.config_manager)
        self.classifier = Classifier(self.assistant_manager, self.config_manager)
        self.current_category = None
        self.thread_id = None 

    async def dispatch(self, user_input: str) -> dict:
        try:
            logger.info(f"Starting dispatch for user input: {user_input}")
            
            self.current_category = await self.classifier.classify_message(user_input)
            
            assistant_name = AssistantConfig.get_assistant_name(self.current_category)
            logger.info(f"Selected assistant: {assistant_name}")
            
            chat_history = await self.get_chat_history()
            assistant_id = await self.assistant_manager.create_or_get_assistant(assistant_name)
            
            if not self.thread_id:
                thread = await self.assistant_manager.create_thread()
                self.thread_id = thread.id
            
            await self.assistant_manager.create_message(self.thread_id, "user", user_input)
            run = await self.assistant_manager.create_run(assistant_id=assistant_id, thread_id=self.thread_id)
            
            return await self.process_run(run, user_input, chat_history)

        except Exception as e:
            logger.error(f"Error in dispatch: {str(e)}", exc_info=True)
            return {'thread_id': self.thread_id, 'run_id': None, 'error': str(e)}

    async def process_run(self, run, user_input: str, chat_history: List[str]) -> dict:
        while True:
            run = self.assistant_manager.wait_on_run(self.thread_id, run.id)
            
            if run.status == "completed":
                assistant_response = await self.assistant_manager.get_assistant_response(self.thread_id, run.id)
                return {
                    'thread_id': self.thread_id,
                    'run_id': run.id,
                    'assistant_response': assistant_response
                }
            elif run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                function_outputs = await self.handle_tool_calls(tool_calls, user_input, chat_history)
                run = await self.assistant_manager.submit_tool_outputs(self.thread_id, run.id, function_outputs)
            else:
                logger.error(f"Unexpected run status: {run.status}")
                return {
                    'thread_id': self.thread_id,
                    'run_id': run.id,
                    'error': f"Unexpected run status: {run.status}"
                }

    async def handle_tool_calls(self, tool_calls, user_input: str, chat_history: List[str]):
        function_outputs = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            category = AssistantCategory(self.current_category)
            
            structured_data = await self.get_structured_request(category, user_input, chat_history, function_name)
            result = await self.call_function(function_name, structured_data)
            
            function_outputs.append({
                "tool_call_id": tool_call.id,
                "output": result
            })
        return function_outputs

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

    async def get_structured_request(self, category: AssistantCategory, user_input: str, chat_history: List[str], function_name: str) -> dict:
        config = self.config_manager.get_config(category)
        if not config:
            raise ValueError(f"No configuration found for category: {category}")

        history_context = "\n".join(chat_history[-10:])
        messages = config.get_messages(history_context, user_input, function_name)
        return await self.assistant_manager.create_structured_completion(messages, category.value, function_name)

    async def call_function(self, function_name: str, function_params: dict) -> str:
        logger.debug(f"Executing function: {function_name} with parameters: {function_params}")
        
        integration = AssistantFactory.get_api_integration(AssistantConfig.get_assistant_name(self.current_category))
        
        if integration:
            return await integration.execute(function_name, function_params)
        else:
            return f"Unknown function: {function_name}"

    async def get_chat_history(self) -> List[str]:
        if not self.thread_id:
            return []
        messages = await self.assistant_manager.list_messages(self.thread_id, limit=10, order="desc")
        return [f"{msg.role}: {msg.content[0].text.value}" for msg in reversed(messages.data)]

    async def call_functions(self, structured_data: dict) -> list:
        category = self.current_category
        assistant_name = AssistantConfig.get_assistant_name(category.value)
        tools = AssistantFactory.get_tools_for_assistant(assistant_name)[0]
        messages = [{"role": "user", "content": json.dumps(structured_data)}]
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            logger.error("No tool calls found in the response")
            return response_message

        function_outputs = []
        tasks = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            logger.debug(f"Calling function: {function_name} with arguments: {function_args}")
            task = asyncio.create_task(self.call_function(function_name, function_args))
            tasks.append((tool_call.id, task))

        for tool_call_id, task in tasks:
            result = await task
            function_outputs.append({
                "tool_call_id": tool_call_id,
                "name": function_name,
                "output": result
            })

        return function_outputs

    async def create_assistant(self, name: str) -> str:
        tools, model = AssistantFactory.get_tools_for_assistant(name)
        assistant = await self.assistant_manager.create_assistant(
            name=name,
            instructions=f"You are a {name}.",
            tools=tools,
            model=model
        )
        return assistant.id