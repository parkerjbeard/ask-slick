from openai import OpenAI
from app.assistants.assistant_manager import AssistantManager
from app.openai_helper import OpenAIClient
from app.services.travel.travel_planner import TravelPlanner
from app.assistants.assistant_factory import AssistantFactory
from app.assistants.classifier import Classifier
import os
import json
import asyncio
from utils.logger import logger
from typing import List

class Dispatcher:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.openai_client = OpenAIClient()
        self.travel_planner = TravelPlanner()
        self.classifier = Classifier(self.assistant_manager)
        self.thread_id = None

    async def dispatch(self, user_input: str) -> dict:
        try:
            logger.info(f"Starting dispatch for user input: {user_input}")
            
            category = await self.classifier.classify_message(user_input)
            
            assistant_name = AssistantFactory.get_assistant_name(category)
            logger.info(f"Selected assistant: {assistant_name}")
            
            chat_history = await self.get_chat_history()
            
            assistant_id = await self.assistant_manager.create_or_get_assistant(assistant_name)
            
            if not self.thread_id:
                thread = await self.assistant_manager.create_thread()
                self.thread_id = thread.id
            
            await self.assistant_manager.create_message(self.thread_id, "user", user_input)

            run = await self.assistant_manager.create_run(assistant_id=assistant_id, thread_id=self.thread_id)
            
            # Wait for the assistant's response or function call
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
                    # Handle function calls
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    function_outputs = await self.handle_tool_calls(tool_calls, user_input, chat_history)
                    
                    # Submit tool outputs and continue the run
                    run = await self.assistant_manager.submit_tool_outputs(self.thread_id, run.id, function_outputs)
                else:
                    logger.error(f"Unexpected run status: {run.status}")
                    return {
                        'thread_id': self.thread_id,
                        'run_id': run.id,
                        'error': f"Unexpected run status: {run.status}"
                    }

        except Exception as e:
            logger.error(f"Error in dispatch: {str(e)}", exc_info=True)
            return {'thread_id': self.thread_id, 'run_id': None, 'error': str(e)}

    async def handle_tool_calls(self, tool_calls, user_input: str, chat_history: List[str]):
        function_outputs = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name in ["search_flights", "search_hotels"]:
                # Parse travel request only when needed
                travel_structured_data = self.travel_planner.parse_travel_request(user_input, chat_history)
                result = await self.call_function(function_name, travel_structured_data)
            else:
                result = await self.call_function(function_name, function_args)
            
            function_outputs.append({
                "tool_call_id": tool_call.id,
                "output": result
            })
        return function_outputs

    async def call_function(self, function_name: str, function_params: dict) -> str:
        logger.debug(f"Executing function: {function_name} with parameters: {function_params}")
        result = ""
        if function_name == "search_flights":
            if all(key in function_params for key in ["origin", "destination", "departure_date"]):
                result = await self.travel_planner._search_flights(function_params)
            else:
                result = "Missing required parameters for flight search"
        elif function_name == "search_hotels":
            if all(key in function_params for key in ["location", "check_in_date", "check_out_date"]):
                result = await self.travel_planner._search_hotels(function_params)
            else:
                result = "Missing required parameters for hotel search"
        else:
            result = f"Unknown function: {function_name}"
        return result

    async def get_chat_history(self) -> List[str]:
        if not self.thread_id:
            return []
        messages = await self.assistant_manager.list_messages(self.thread_id, limit=10, order="desc")
        return [f"{msg.role}: {msg.content[0].text.value}" for msg in reversed(messages.data)]

    async def call_functions(self, travel_structured_data: dict) -> list:
        tools = AssistantFactory.get_tools_for_assistant("TravelAssistant")[0]
        messages = [{"role": "user", "content": json.dumps(travel_structured_data)}]
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
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