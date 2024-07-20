from openai import OpenAI
from app.assistant_manager import AssistantManager
from app.openai_helper import OpenAIClient
from app.services.travel.travel_planner import TravelPlanner
import os

class Dispatcher:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.openai_client = OpenAIClient()
        self.travel_planner = TravelPlanner()
        self.thread_id = None
        self.classifier_assistant_id = None

    async def initialize(self):
        assistants = await self.assistant_manager.list_assistants()
        self.classifier_assistant_id = assistants.get("ClassifierAssistant")
        if not self.classifier_assistant_id:
            raise ValueError("ClassifierAssistant not found. Please run update_assistants() first.")

    async def classify_message(self, user_input):

        if not self.classifier_assistant_id:
            await self.initialize()

        if not self.thread_id:
            thread = await self.assistant_manager.create_thread()
            self.thread_id = thread.id

        # Add user message to the thread
        await self.assistant_manager.create_message(self.thread_id, "user", user_input)

        # Get the last few messages for context
        messages = await self.assistant_manager.list_messages(self.thread_id, order="desc", limit=5)
        context = "\n".join([f"{msg.role}: {msg.content[0].text.value}" for msg in reversed(messages.data)])

        instructions = f"""Classify the last user message into one of these categories: schedule, family, travel, todo, document.
        Consider the context of the conversation:
        
        {context}
        
        Your response should be a single word (the category)."""

        run = await self.assistant_manager.create_run(
            thread_id=self.thread_id,
            assistant_id=self.classifier_assistant_id,
            instructions=instructions
        )

        # Wait for the run to complete
        run = self.assistant_manager.wait_on_run(self.thread_id, run.id)
        # Get the assistant's response (classification)
        classification = await self.assistant_manager.get_assistant_response(self.thread_id, run.id)

        return classification.strip().lower()

    async def dispatch(self, user_input):
        category = await self.classify_message(user_input)

        assistant_name = self.get_assistant_name(category)
        
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
        
        # Add user message to the thread
        await self.assistant_manager.create_message(self.thread_id, "user", user_input)

        run = await self.assistant_manager.create_run(assistant_id=assistant_id, thread_id=self.thread_id)
        
        function_output = None
        if assistant_name == "TravelAssistant" and "error" not in travel_structured_data:
            function_output = await self.call_function("search_flights", travel_structured_data)

        return {
            'thread_id': self.thread_id, 
            'run_id': run.id, 
            'function_output': function_output
        }

    def get_assistant_name(self, category):
        return {
            "travel": "TravelAssistant",
            "schedule": "ScheduleAssistant",
            "family": "FamilyAssistant",
            "todo": "TodoAssistant",
            "document": "DocumentAssistant"
        }.get(category, "GeneralAssistant")

    async def create_assistant(self, name):
        tools, model = self.get_tools_for_assistant(name)
        assistant = await self.assistant_manager.create_assistant(
            name=name,
            instructions=f"You are a {name}.",
            tools=tools,
            model=model
        )
        return assistant.id

    def get_tools_for_assistant(self, name):
        if name == "TravelAssistant":
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_flights",
                        "description": "Search for flights using the SerpAPI Google Flights API with advanced options.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "origin": {"type": "string", "description": "The 3-letter airport code for the departure location"},
                                "destination": {"type": "string", "description": "The 3-letter airport code for the arrival location"},
                                "departure_date": {"type": "string", "description": "The date of departure in YYYY-MM-DD format"},
                                "return_date": {"type": "string", "description": "The date of return in YYYY-MM-DD format (optional for one-way trips)"},
                                "currency": {"type": "string", "description": "Currency code (e.g., USD, EUR)"},
                                "travel_class": {"type": "string", "description": "Travel class (e.g., '1' for Economy, '2' for Premium Economy, '3' for Business, '4' for First Class)"},
                                "adults": {"type": "string", "description": "Number of adult passengers"},
                                "children": {"type": "string", "description": "Number of child passengers"},
                                "infants_in_seat": {"type": "string", "description": "Number of infants in seat"},
                                "infants_on_lap": {"type": "string", "description": "Number of infants on lap"},
                                "stops": {"type": "string", "description": "Number of stops (e.g., '0' for non-stop, '1' for one stop)"},
                                "max_price": {"type": "string", "description": "Maximum price for flights"}
                            },
                            "required": ["origin", "destination", "departure_date"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_hotels",
                        "description": "Search for hotels using the SerpAPI Google Hotels API with advanced options.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "The location to search for hotels"},
                                "check_in_date": {"type": "string", "description": "The check-in date in YYYY-MM-DD format"},
                                "check_out_date": {"type": "string", "description": "The check-out date in YYYY-MM-DD format"},
                                "currency": {"type": "string", "description": "Currency code (e.g., USD, EUR)"},
                                "adults": {"type": "string", "description": "Number of adult guests"},
                                "children": {"type": "string", "description": "Number of child guests"},
                                "rating": {"type": "string", "description": "Minimum hotel rating (e.g., '8' for 4-star and above)"},
                                "min_price": {"type": "string", "description": "Minimum price for hotels"},
                                "max_price": {"type": "string", "description": "Maximum price for hotels"},
                                "amenities": {"type": "string", "description": "Comma-separated list of desired amenities"},
                                "property_types": {"type": "string", "description": "Comma-separated list of desired property types"}
                            },
                            "required": ["location", "check_in_date", "check_out_date"]
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
            model = "gpt-4o-mini"
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
                                "to": {"type": "string", "description": "Recipient email address"},
                                "subject": {"type": "string", "description": "Email subject"},
                                "body": {"type": "string", "description": "Email body"}
                            },
                            "required": ["to", "subject", "body"]
                        }
                    }
                }
            ]
            model = "gpt-4o-mini"
        else:
            tools = []
            model = "gpt-4o-mini"

        return tools, model

    async def call_function(self, function_name, function_params):
        if function_name == "plan_trip":
            return await self.travel_planner.plan_trip(function_params["travel_request"])
        elif function_name == "search_flights":
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