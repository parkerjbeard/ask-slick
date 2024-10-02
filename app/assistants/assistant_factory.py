from app.services.api_integrations.calendar_integration import CalendarIntegration
from app.services.api_integrations.travel_integration import TravelIntegration
from app.services.api_integrations.gmail_integration import GmailIntegration
from app.config.assistant_config import AssistantConfig
from typing import Dict, Any, Tuple, List
from utils.logger import logger

class AssistantFactory:
    @staticmethod
    def get_assistant_name(category: str) -> str:
        return AssistantConfig.get_assistant_name(category)
    
    @staticmethod
    def get_api_integration(name: str) -> Any:
        if name == "TravelAssistant":
            return TravelIntegration()
        elif name == "CalendarAssistant":
            return CalendarIntegration()
        elif name == "GmailAssistant":
            return GmailIntegration()
        # Add other API integrations as they are created
        return None

    @staticmethod
    def get_tools_for_assistant(name: str) -> Tuple[List[Dict[str, Any]], str]:
        integration = AssistantFactory.get_api_integration(name)
        if integration:
            tools = integration.get_tools()
            logger.debug(f"Tools: {tools}")
            for tool in tools:
                if tool['type'] == 'function':
                    tool['function']['parameters'] = AssistantFactory.get_json_schema(name, tool['function']['name'])
            return tools, "gpt-4o"
        return [], "gpt-4o"

    @staticmethod
    def get_assistant_instructions(name: str) -> str:
        integration = AssistantFactory.get_api_integration(name)
        return integration.get_instructions() if integration else f"You are a {name}."

    @staticmethod
    def get_json_schema(name: str, function_name: str = None) -> Dict[str, Any]:
        if name == "TravelAssistant":
            if function_name == "search_flights":
                return {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                        "departure_date": {"type": "string"},
                        "return_date": {"type": "string"},
                        "passengers": {"type": "integer"},
                        "class": {"type": "string"}
                    },
                    "required": ["origin", "destination", "departure_date"]
                }
            elif function_name == "search_hotels":
                return {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "check_in": {"type": "string"},
                        "check_out": {"type": "string"},
                        "guests": {"type": "integer"},
                        "rooms": {"type": "integer"}
                    },
                    "required": ["location", "check_in", "check_out"]
                }
            
        elif name == "CalendarAssistant":
            if function_name == "check_available_slots":
                return {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "duration": {"type": "integer"},
                        "timezone": {"type": "string"}
                    },
                    "required": ["start_date", "end_date", "duration"]
                }
            elif function_name == "create_event":
                return {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time"},
                        "description": {"type": "string"},
                        "location": {"type": "string"},
                        "timezone": {"type": "string"}
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            elif function_name == "update_event":
                return {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "summary": {"type": "string"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time"},
                        "description": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["event_id"]
                }
            elif function_name == "delete_event":
                return {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"}
                    },
                    "required": ["event_id"]
                }

        elif name == "GmailAssistant":
            if function_name == "send_email":
                return {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"}
                    },
                    "required": ["to", "subject", "body"]
                }
            elif function_name == "create_draft":
                return {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"}
                    },
                    "required": ["to", "subject", "body"]
                    }
        # Add schemas for other assistant types
        return {
            "type": "object",
            "properties": {},
            "required": []
        }