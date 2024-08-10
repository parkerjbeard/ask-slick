from typing import Dict, Any, Tuple, List
from app.services.api_integrations.travel_integration import TravelIntegration
from functools import lru_cache

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
    def get_api_integration(name: str) -> Any:
        if name == "TravelAssistant":
            return TravelIntegration()
        # Add other API integrations as they are created
        return None

    @staticmethod
    def get_tools_for_assistant(name: str) -> Tuple[List[Dict[str, Any]], str]:
        integration = AssistantFactory.get_api_integration(name)
        if integration:
            tools = integration.get_tools()
            for tool in tools:
                if tool['type'] == 'function':
                    tool['function']['parameters'] = AssistantFactory.get_json_schema(name, tool['function']['name'])
            return tools, "gpt-4o-mini"
        return [], "gpt-4o-mini"

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
        # Add schemas for other assistant types
        return {
            "type": "object",
            "properties": {},
            "required": []
        }