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
    def get_api_integration(name: str):
        if name == "TravelAssistant":
            return TravelIntegration()
        # Add other API integrations as they are created
        else:
            return None

    @staticmethod
    def get_tools_for_assistant(name: str) -> Tuple[List[Dict[str, Any]], str]:
        integration = AssistantFactory.get_api_integration(name)
        if integration:
            return integration.get_tools(), "gpt-4o-mini"
        else:
            return [], "gpt-4o-mini"

    @staticmethod
    def get_assistant_instructions(name: str) -> str:
        integration = AssistantFactory.get_api_integration(name)
        if integration:
            return integration.get_instructions()
        else:
            return f"You are a {name}."