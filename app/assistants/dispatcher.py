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

class Dispatcher:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.classifier = Classifier(self.assistant_manager)
        self.thread_id = None
        self.current_category = None
        self.openai_helper = OpenAIClient()
        self.search_flight = FlightSearch()
        self.calendar_manager = CalendarManager()

    async def dispatch(self, user_input: str) -> dict:
        try:
            logger.info(f"Starting dispatch for user input: {user_input}")
            
            self.current_category = await self.classifier.classify_message(user_input)
            assistant_name = AssistantFactory.get_assistant_name(self.current_category)
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
            
            if function_name in ["search_flights", "search_hotels"]:
                travel_structured_data = await self.get_structured_travel_request(user_input, chat_history, function_name)
                processed_request = self.search_flight._process_travel_request(travel_structured_data)
                result = await self.call_function(function_name, processed_request)
            elif function_name in ["check_available_slots", "create_event", "update_event", "delete_event"]:
                calendar_structured_data = await self.get_structured_calendar_request(user_input, chat_history, function_name)
                result = await self.call_function(function_name, calendar_structured_data)
            elif function_name in ["send_email", "create_draft"]:
                email_structured_data = await self.get_structured_email_request(user_input, chat_history, function_name)
                result = await self.call_function(function_name, email_structured_data)
            else:
                function_args = json.loads(tool_call.function.arguments)
                result = await self.call_function(function_name, function_args)
            
            function_outputs.append({
                "tool_call_id": tool_call.id,
                "output": result
            })
        return function_outputs

    async def get_structured_travel_request(self, user_input: str, chat_history: List[str], function_name: str) -> dict:
        # Prepare the chat history context
        history_context = "\n".join(chat_history[-10:])  # Use the last 10 messages for context
        
        messages = [
            {"role": "system", "content": """You are a travel assistant parsing travel requests. 
            When extracting information, follow these rules:
            1. For origin and destination, always use 3-letter IATA airport codes.
            2. If a specific airport is not mentioned, use the main airport code for the given city, state, or country.
               For example:
               - New York -> JFK (John F. Kennedy International Airport)
               - California -> LAX (Los Angeles International Airport)
               - Japan -> NRT (Narita International Airport)
            3. If the origin is not specified at all, use 'NULL' as the value.
            4. For all other fields, if the information is not provided, leave the field empty.
            5. Always include all fields in the output, even if they are empty.
            6. Use the chat history as context to infer any missing information.
            7. If you're unsure about the correct airport code, use your best judgment to provide the most likely code for the main airport in that location."""},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following travel request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]
        return await self.assistant_manager.create_structured_completion(messages, "TravelAssistant", function_name)

    async def get_structured_calendar_request(self, user_input: str, chat_history: List[str], function_name: str) -> dict:
        history_context = "\n".join(chat_history[-10:])  # Use the last 10 messages for context
        
        messages = [
            {"role": "system", "content": """You are a calendar assistant parsing calendar requests. 
            When extracting information, follow these rules:
            1. For dates and times, use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
            2. If a specific time is not mentioned, use 00:00:00 as the default time.
            3. If the information is not provided, leave the field empty.
            4. Always include all fields in the output, even if they are empty.
            5. Use the chat history as context to infer any missing information.
            6. For event IDs, if not explicitly mentioned, use 'NULL' as the value."""},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following calendar request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]
        return await self.assistant_manager.create_structured_completion(messages, "CalendarAssistant", function_name)

    async def get_structured_email_request(self, user_input: str, chat_history: List[str], function_name: str) -> dict:
        history_context = "\n".join(chat_history[-10:])  # Use the last 10 messages for context
        
        messages = [
            {"role": "system", "content": """You are an email assistant parsing email requests. 
            When extracting information, follow these rules:
            1. Always extract the recipient's email address. If not provided, use 'example@example.com'.
            2. Always generate a suitable subject line based on the content.
            3. Always compose an appropriate email body based on the user's request.
            4. If any information is missing or unclear, use your best judgment to fill in the gaps.
            5. Always include 'to', 'subject', and 'body' fields in the output."""},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following email request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]
        return await self.assistant_manager.create_structured_completion(messages, "GmailAssistant", function_name)

    async def call_function(self, function_name: str, function_params: dict) -> str:
        logger.debug(f"Executing function: {function_name} with parameters: {function_params}")
        
        assistant_name = AssistantFactory.get_assistant_name(self.current_category)
        integration = AssistantFactory.get_api_integration(assistant_name)
        
        if integration:
            return await integration.execute(function_name, function_params)
        else:
            return f"Unknown function: {function_name}"

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