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
    def get_api_integration(name: str, user_id: str = None) -> Any:
        # Allow general assistant without user_id
        if name == "GeneralAssistant":
            return None
        
        # Require user_id for specialized assistants
        if not user_id:
            logger.warning("User ID required for specialized assistants")
            return None
        
        if name == "TravelAssistant":
            return TravelIntegration()
        elif name == "CalendarAssistant":
            return CalendarIntegration(user_id)
        elif name == "GmailAssistant":
            return GmailIntegration(user_id)
        return None

    @staticmethod
    def get_tools_for_assistant(name: str, user_id: str) -> Tuple[List[Dict[str, Any]], str]:
        integration = AssistantFactory.get_api_integration(name, user_id)
        if integration:
            tools = integration.get_tools()
            return tools, "gpt-4o-2024-08-06"
        return [], "gpt-4o-2024-08-06"

    @staticmethod
    def get_assistant_instructions(name: str, user_id: str) -> str:
        integration = AssistantFactory.get_api_integration(name, user_id)
        return integration.get_instructions() if integration else f"You are a {name}."