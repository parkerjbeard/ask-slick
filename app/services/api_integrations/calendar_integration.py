from app.services.calendar.calendar_manager import CalendarManager
from app.services.api_integrations import APIIntegration
from typing import Dict, Any, List
from utils.logger import logger
import asyncio
import os

class CalendarIntegration(APIIntegration):
    def __init__(self):
        self.calendar_manager = CalendarManager()
        self.default_timezone = os.getenv('DEFAULT_TIMEZONE', 'UTC')

    async def execute(self, function_name: str, params: dict) -> str:
        logger.debug(f"CalendarIntegration executing function: {function_name} with params: {params}")
        
        if function_name == "check_available_slots":
            return await self._check_available_slots(params)
        elif function_name == "create_event":
            return await self._create_event(params)
        elif function_name == "update_event":
            return await self._update_event(params)
        elif function_name == "delete_event":
            return await self._delete_event(params)
        else:
            logger.warning(f"Unknown function in CalendarIntegration: {function_name}")
            return f"Unknown function: {function_name}"

    async def _check_available_slots(self, params: dict) -> str:
        required_params = ["start_date", "end_date", "duration"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for checking available slots: {', '.join(missing_params)}"
        
        # Replace NULL timezone with default timezone
        if params.get('timezone') == 'NULL':
            params['timezone'] = self.default_timezone
            logger.info(f"Using default timezone: {self.default_timezone}")
        
        try:
            # Run the synchronous method in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.calendar_manager.check_available_slots(**params))
            return result
        except Exception as e:
            logger.error(f"Error in checking available slots: {str(e)}", exc_info=True)
            return f"An error occurred while checking available slots: {str(e)}"

    async def _create_event(self, params: dict) -> str:
        required_params = ["summary", "start_time", "end_time"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for creating an event: {', '.join(missing_params)}"
        
        try:
            return self.calendar_manager.create_event(**params)
        except Exception as e:
            logger.error(f"Error in creating an event: {str(e)}", exc_info=True)
            return f"An error occurred while creating an event: {str(e)}"

    async def _update_event(self, params: dict) -> str:
        required_params = ["event_id"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for updating an event: {', '.join(missing_params)}"
        
        try:
            return self.calendar_manager.update_event(**params)
        except Exception as e:
            logger.error(f"Error in updating an event: {str(e)}", exc_info=True)
            return f"An error occurred while updating an event: {str(e)}"

    async def _delete_event(self, params: dict) -> str:
        required_params = ["event_id"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for deleting an event: {', '.join(missing_params)}"
        
        try:
            return self.calendar_manager.delete_event(**params)
        except Exception as e:
            logger.error(f"Error in deleting an event: {str(e)}", exc_info=True)
            return f"An error occurred while deleting an event: {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_available_slots",
                    "description": "Check available time slots in the calendar within a given date range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "The start date of the range to check (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "The end date of the range to check (YYYY-MM-DD)"},
                            "duration": {"type": "integer", "description": "The duration of the slot in minutes"},
                            "timezone": {"type": "string", "description": "The timezone for the search (optional)"}
                        },
                        "required": ["start_date", "end_date", "duration"],
                        "additionalProperties": False,
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_event",
                    "description": "Create a new event in the calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "The title of the event"},
                            "start_time": {"type": "string", "description": "The start time of the event (YYYY-MM-DDTHH:MM:SS)"},
                            "end_time": {"type": "string", "description": "The end time of the event (YYYY-MM-DDTHH:MM:SS)"},
                            "description": {"type": "string", "description": "The description of the event (optional)"},
                            "location": {"type": "string", "description": "The location of the event (optional)"},
                            "timezone": {"type": "string", "description": "The timezone for the event (optional)"}
                        },
                        "required": ["summary", "start_time", "end_time"],
                        "additionalProperties": False,
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_event",
                    "description": "Update an existing event in the calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "The ID of the event to update"},
                            "summary": {"type": "string", "description": "The updated title of the event (optional)"},
                            "start_time": {"type": "string", "description": "The updated start time of the event (YYYY-MM-DDTHH:MM:SS) (optional)"},
                            "end_time": {"type": "string", "description": "The updated end time of the event (YYYY-MM-DDTHH:MM:SS) (optional)"},
                            "description": {"type": "string", "description": "The updated description of the event (optional)"},
                            "location": {"type": "string", "description": "The updated location of the event (optional)"}
                        },
                        "required": ["event_id"],
                        "additionalProperties": False,
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_event",
                    "description": "Delete an event from the calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "The ID of the event to delete"}
                        },
                        "required": ["event_id"],
                        "additionalProperties": False,
                    },
                    "strict": True
                }
            }
        ]

    def get_instructions(self) -> str:
        return """You are a Calendar Assistant. Your responsibilities include:
        - Checking available time slots in the calendar.
        - Creating new events in the calendar.
        - Updating existing events in the calendar.
        - Deleting events from the calendar.

        When a user asks for calendar-related actions, use the provided functions to answer questions.

        Always confirm the action with the user before executing it, especially for create, update, and delete operations.

        Provide clear and concise responses, and offer additional assistance if needed.
        
        Remember that you are an assistant and will be responding inside a chatbot. Make it sound human and conversational while being polite, helpful, and organized.
        All of your responses should be included in a single message.
        """