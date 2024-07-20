from openai import OpenAI
from app.assistants.assistant_manager import AssistantManager
from app.openai_helper import OpenAIClient
from app.services.travel.travel_planner import TravelPlanner
from app.assistants.assistant_factory import AssistantFactory
from app.assistants.classifier import Classifier
import os
import json
import asyncio

class Dispatcher:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.openai_client = OpenAIClient()
        self.travel_planner = TravelPlanner()
        self.classifier = Classifier(self.assistant_manager)
        self.thread_id = None

    async def dispatch(self, user_input: str) -> dict:
        category = await self.classifier.classify_message(user_input)
        assistant_name = AssistantFactory.get_assistant_name(category)
        
        travel_structured_data = None
        if assistant_name == "TravelAssistant":
            travel_structured_data = self.travel_planner.parse_travel_request(user_input)
            if "error" in travel_structured_data:
                return {'thread_id': None, 'run_id': None}

        assistants = await self.assistant_manager.list_assistants()
        assistant_id = assistants.get(assistant_name) or await self.create_assistant(assistant_name)

        if not self.thread_id:
            thread = await self.assistant_manager.create_thread()
            self.thread_id = thread.id
        
        await self.assistant_manager.create_message(self.thread_id, "user", user_input)

        run = await self.assistant_manager.create_run(assistant_id=assistant_id, thread_id=self.thread_id)
        
        function_outputs = None
        if assistant_name == "TravelAssistant" and "error" not in travel_structured_data:
            function_outputs = await self.call_functions(travel_structured_data)

        return {
            'thread_id': self.thread_id, 
            'run_id': run.id, 
            'function_outputs': function_outputs
        }

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
            return response_message

        function_outputs = []
        tasks = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
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

    async def call_function(self, function_name: str, function_params: dict) -> str:
        # if function_name == "plan_trip":
        #     return await self.travel_planner.plan_trip(function_params["travel_request"])
        if function_name == "search_flights":
            if all(key in function_params for key in ["origin", "destination", "departure_date"]):
                return await self.travel_planner._search_flights(function_params)
            else:
                return "Missing required parameters for flight search"
        elif function_name == "search_hotels":
            if all(key in function_params for key in ["location", "check_in_date", "check_out_date"]):
                return await self.travel_planner._search_hotels(function_params)
            else:
                return "Missing required parameters for hotel search"
        else:
            return f"Unknown function: {function_name}"

    async def create_assistant(self, name: str) -> str:
        tools, model = AssistantFactory.get_tools_for_assistant(name)
        assistant = await self.assistant_manager.create_assistant(
            name=name,
            instructions=f"You are a {name}.",
            tools=tools,
            model=model
        )
        return assistant.id