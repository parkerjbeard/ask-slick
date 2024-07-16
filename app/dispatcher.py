from openai import OpenAI
from app.assistant_manager import AssistantManager
from app.openai_client import OpenAIClient
import os


class Dispatcher:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_manager = AssistantManager()
        self.openai_client = OpenAIClient()

    async def dispatch(self, user_input):
        # Classify the user input to determine which assistant to use
        categories = ["schedule", "family", "travel", "todo", "document"]
        category = self.openai_client.classify_text(user_input, categories)

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

        # Get or create the assistant
        assistants = await self.assistant_manager.list_assistants()
        if assistant_name in assistants:
            assistant_id = assistants[assistant_name]
        else:
            assistant_id = await self.create_assistant(assistant_name)

        thread = await self.assistant_manager.create_thread()

        # Create a run with the selected assistant
        run = self.assistant_manager.create_run(
            assistant_id=assistant_id,
            thread_id=thread.id
        )
        return run, thread

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
                            "required": ["destination"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_return_flights",
                        "description": "Search for return flights using a departure token and return date.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "departure_token": {
                                    "type": "string",
                                    "description": "The departure token obtained from the initial flight search"
                                },
                                "return_date": {
                                    "type": "string",
                                    "description": "The date of return in YYYY-MM-DD format"
                                }
                            },
                            "required": ["departure_token", "return_date"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "generate_travel_suggestions",
                        "description": "Generate travel suggestions for a given destination, including popular attractions, local cuisine, and cultural experiences.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "destination": {
                                    "type": "string",
                                    "description": "The destination for which to generate travel suggestions"
                                }
                            },
                            "required": ["destination"]
                        }
                    }
                },
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

        return tools, model

