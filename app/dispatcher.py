from openai import OpenAI
from app.assistant_manager import AssistantManager
from app.openai_client import OpenAIClient
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger
import os


class Dispatcher:
    def __init__(self):
        logger.info("Initializing Dispatcher")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.openai_client = OpenAIClient()
        self.travel_planner = TravelPlanner()
        logger.info("Dispatcher initialized successfully")

    async def dispatch(self, user_input):
        logger.info(f"Dispatching user input: {user_input}")
        # Classify the user input to determine which assistant to use
        categories = ["schedule", "family", "travel", "todo", "document"]
        category = self.openai_client.classify_text(user_input, categories)
        logger.info(f"Classified input as: {category}")

        if category == "travel":
            assistant_name = "TravelAssistant"
        elif category == "schedule":
            assistant_name = "ScheduleAssistant"
        elif category == "family":
            assistant_name = "FamilyAssistant"
        elif category == "todo":
            assistant_name = "TodoAssistant"
        elif category == "document":
            assistant_name = "DocumentAssistant"
        else:
            assistant_name = "GeneralAssistant"
        
        logger.info(f"Selected assistant: {assistant_name}")

        # Get or create the assistant
        assistants = await self.assistant_manager.list_assistants()
        if assistant_name in assistants:
            assistant_id = assistants[assistant_name]
            logger.info(f"Using existing assistant: {assistant_name} (ID: {assistant_id})")
        else:
            assistant_id = await self.create_assistant(assistant_name)
            logger.info(f"Created new assistant: {assistant_name} (ID: {assistant_id})")

        thread = self.assistant_manager.create_thread()
        logger.info(f"Created new thread: {thread.id}")

        # Create a run with the selected assistant
        run = await self.assistant_manager.create_run(  # Ensure this is awaited
            assistant_id=assistant_id,
            thread_id=thread.id
        )
        logger.info(f"Created new run: {run.id}")

        # Example of calling a function and handling its output
        if assistant_name == "TravelAssistant":
            function_name = "parse_travel_request"
            function_params = {
                "prompt": user_input
            }
            logger.info(f"Calling function: {function_name}")
            function_output = await self.call_function(function_name, function_params)
            logger.info(f"Function Output: {function_output}")

        return run, thread

    async def create_assistant(self, name):
        logger.info(f"Creating new assistant: {name}")
        tools, model = self.get_tools_for_assistant(name)
        assistant = await self.assistant_manager.create_assistant(
            name=name,
            instructions=f"You are a {name}.",
            tools=tools,
            model=model
        )
        logger.info(f"Assistant created: {name} (ID: {assistant.id})")
        return assistant.id

    def get_tools_for_assistant(self, name):
        logger.info(f"Getting tools for assistant: {name}")
        if name == "TravelAssistant":
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "parse_travel_request",
                        "description": "Parse a travel request into structured data.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "origin": {
                                    "type": "string",
                                    "description": "The 3-letter airport code for the departure location"
                                },
                                "destination": {
                                    "type": "string",
                                    "description": "The 3-letter airport code for the arrival location"
                                },
                                "departure_date": {
                                    "type": "string",
                                    "description": "The date of departure in YYYY-MM-DD format"
                                },
                                "return_date": {
                                    "type": "string",
                                    "description": "The date of return in YYYY-MM-DD format"
                                },
                                "check_in": {
                                    "type": "string",
                                    "description": "The check-in date for accommodation in YYYY-MM-DD format"
                                },
                                "check_out": {
                                    "type": "string",
                                    "description": "The check-out date for accommodation in YYYY-MM-DD format"
                                }
                            },
                            "required": ["origin", "destination", "departure_date"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "plan_trip",
                        "description": "Plan a trip based on the parsed travel request.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "travel_request": {
                                    "type": "object",
                                    "description": "The parsed travel request",
                                    "properties": {
                                        "origin": {"type": "string"},
                                        "destination": {"type": "string"},
                                        "departure_date": {"type": "string"},
                                        "return_date": {"type": "string"},
                                        "check_in": {"type": "string"},
                                        "check_out": {"type": "string"}
                                    },
                                    "required": ["origin", "destination", "departure_date"]
                                }
                            },
                            "required": ["travel_request"]
                        }
                    }
                }
            ]
            model = "gpt-3.5-turbo-0125"
        elif name == "EmailAssistant":
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "send_email",
                        "description": "Send an email",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "string",
                                    "description": "Recipient email address"
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject"
                                },
                                "body": {
                                    "type": "string",
                                    "description": "Email body"
                                }
                            },
                            "required": ["to", "subject", "body"]
                        }
                    }
                }
            ]
            model = "gpt-3.5-turbo-0301"
        # Add other assistants and their tools here
        else:
            tools = []
            model = "gpt-3.5-turbo-0125"  # Default model

        logger.info(f"Tools and model selected for {name}: {len(tools)} tools, model {model}")
        return tools, model

    async def call_function(self, function_name, function_params):
        logger.info(f"Calling function: {function_name} with params: {function_params}")
        # This method should call the function and return the result
        if function_name == "parse_travel_request":
            result = self.travel_planner.parse_travel_request(function_params["prompt"])
        elif function_name == "plan_trip":
            result = self.travel_planner.plan_trip(function_params["travel_request"])
        # Add other function calls here
        else:
            logger.warning(f"Unknown function call: {function_name}")
            result = {}
        
        logger.info(f"Function {function_name} returned: {result}")
        return result