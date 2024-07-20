from typing import Dict, Any, Tuple, List

class AssistantFactory:
    @staticmethod
    def get_assistant_name(category: str) -> str:
        return {
            "travel": "TravelAssistant",
            "schedule": "ScheduleAssistant",
            "family": "FamilyAssistant",
            "todo": "TodoAssistant",
            "document": "DocumentAssistant"
        }.get(category, "GeneralAssistant")

    @staticmethod
    def get_tools_for_assistant(name: str) -> Tuple[List[Dict[str, Any]], str]:
        if name == "TravelAssistant":
            return AssistantFactory._get_travel_assistant_tools(), "gpt-4o-mini"
        elif name == "EmailAssistant":
            return AssistantFactory._get_email_assistant_tools(), "gpt-4o-mini"
        else:
            return [], "gpt-4o-mini"

    @staticmethod
    def get_assistant_instructions(name: str) -> str:
        instructions = {
            "TravelAssistant": """You are a Travel Assistant. Your responsibilities include:
            - Assisting users in planning their trips.
            - Searching for flights and hotels.
            - Providing travel recommendations.
            The travel recommendations you provide the user should be specific to their needs and preferences. You will provide the user with:

            1. Top 5 must-visit attractions or landmarks, with a brief description of each.
            2. 5 unique or off-the-beaten-path experiences that showcase the local culture.
            3. 5 recommended restaurants or food experiences, ranging from local street food to fine dining. Specify the budget with a range from $ (cheap) to $$$ (expensive).
            4. 3 suggested day trips or nearby areas worth exploring.
            5. 3 accommodation options for different budgets (budget, mid-range, luxury).
            6. Tips for getting around the destination (public transportation, car rental, etc.).
            7. Any annual events or festivals that are worth planning a trip around.
            8. Safety tips or areas to be cautious about, if applicable.

            Please provide specific names, locations, and brief explanations for each recommendation. Tailor the suggestions to appeal to a variety of interests, including history, culture, nature, and cuisine.
            
            Do not offer acommodation or flight recommendations unless specifically and explicityly prompted to, as a function will be called to handle the request if needed.

            Rememeber that you are an assistant and will be responding inside a chatbot. Make it sound human and conversational while being polite, helpful and organized.
            All of your response should be included in a single message.
            """,

            "EmailAssistant": "You are an Email Assistant. Your job is to help users compose, send, and manage emails efficiently.",
            "GeneralAssistant": "You are a General Assistant. You can help with a wide range of tasks and answer various questions on different topics.",
            "ClassifierAssistant": """You are a ClassifierAssistant. Your job is to classify user messages into predefined categories. 
            Pay close attention to the context of the conversation and the current message. 
            Your output should always be a single word from the given categories.""",
            "ScheduleAssistant": "You are a Schedule Assistant. Your role is to help users manage their calendars, set appointments, and organize their time effectively.",
            "FamilyAssistant": "You are a Family Assistant. You help with family-related tasks, planning activities, and providing advice on family matters.",
            "TodoAssistant": "You are a Todo Assistant. Your job is to help users manage their tasks, create to-do lists, and track their progress on various activities.",
            "DocumentAssistant": "You are a Document Assistant. You help users with document-related tasks such as formatting, proofreading, and providing writing suggestions."
        }
        return instructions.get(name, f"You are a {name}.")

    @staticmethod
    def _get_travel_assistant_tools() -> List[Dict[str, Any]]:
        return [
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
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "plan_trip",
            #         "description": "Plan a trip based on the parsed travel request.",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "travel_request": {
            #                     "type": "object",
            #                     "description": "The parsed travel request",
            #                     "properties": {
            #                         "origin": {"type": "string"},
            #                         "destination": {"type": "string"},
            #                         "departure_date": {"type": "string"},
            #                         "return_date": {"type": "string"},
            #                         "check_in": {"type": "string"},
            #                         "check_out": {"type": "string"}
            #                     },
            #                     "required": ["origin", "destination", "departure_date"]
            #                 }
            #             },
            #             "required": ["travel_request"]
            #         }
            #     }
            # }
        ]

    @staticmethod
    def _get_email_assistant_tools() -> List[Dict[str, Any]]:
        return [
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