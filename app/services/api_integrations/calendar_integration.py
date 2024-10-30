from app.services.calendar.calendar_manager import CalendarManager
from app.services.api_integrations import APIIntegration
from app.openai_helper import OpenAIClient
from app.config.settings import settings
from typing import Dict, Any, List
from utils.logger import logger
import asyncio

class CalendarIntegration(APIIntegration):
    def __init__(self, user_id: str):
        logger.debug(f"Initializing CalendarIntegration with user_id: {user_id}")
        if not user_id:
            logger.error("Attempted to initialize CalendarIntegration with empty user_id")
            raise ValueError("user_id is required for CalendarIntegration")
        self.user_id = user_id
        logger.info(f"Creating CalendarManager for user_id: {user_id}")
        self.calendar_manager = CalendarManager(user_id)
        self.default_timezone = settings.DEFAULT_TIMEZONE
        self.openai_client = OpenAIClient()

    async def execute(self, function_name: str, params: dict) -> str:
        logger.debug(f"CalendarIntegration executing function for user {self.user_id}: {function_name} with params: {params}")
        
        if function_name == "check_available_slots":
            return await self._check_available_slots(params)
        elif function_name == "create_event":
            return await self._create_event(params)
        elif function_name == "update_event":
            return await self._update_event(params)
        elif function_name == "delete_event":
            return await self._delete_event(params)
        elif function_name == "list_events":
            return await self._list_events(params)
        elif function_name == "identify_event":
            return await self._identify_event(params['user_message'], params['start_date'], params['end_date'])
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
            # Remove user_id from params before passing to calendar_manager
            calendar_params = {k: v for k, v in params.items() if k != 'user_id'}
            logger.debug(f"Filtered parameters for calendar manager: {calendar_params}")
            
            # Run the synchronous method in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.calendar_manager.check_available_slots(**calendar_params))
            return result
        except Exception as e:
            logger.error(f"Error in checking available slots: {str(e)}", exc_info=True)
            return f"An error occurred while checking available slots: {str(e)}"

    async def _create_event(self, params: dict) -> str:
        required_params = ["summary", "start_time", "end_time"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for creating an event: {', '.join(missing_params)}"
        
        # Replace NULL timezone with default timezone
        if params.get('timezone') == 'NULL':
            params['timezone'] = self.default_timezone
            logger.info(f"Using default timezone: {self.default_timezone}")
        
        try:
            # Run the synchronous method in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.calendar_manager.create_event(**params))
            return result
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

    async def _list_events(self, params: dict) -> str:
        required_params = ["start_date", "end_date"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for listing events: {', '.join(missing_params)}"
        
        # Replace NULL timezone with default timezone
        if params.get('timezone') == 'NULL':
            params['timezone'] = self.default_timezone
            logger.info(f"Using default timezone: {self.default_timezone}")
        
        try:
            # Run the synchronous method in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(None, lambda: self.calendar_manager.list_events(**params))
            
            # Format the events into a readable string
            result = "Events:\n\n"
            for event in events:
                result += f"ID: {event['id']}\n"
                result += f"Title: {event['summary']}\n"
                result += f"Start: {event['start']}\n"
                result += f"End: {event['end']}\n"
                if event['description']:
                    result += f"Description: {event['description']}\n"
                if event['location']:
                    result += f"Location: {event['location']}\n"
                result += "\n"
            
            return result.strip()
        except Exception as e:
            logger.error(f"Error in listing events: {str(e)}", exc_info=True)
            return f"An error occurred while listing events: {str(e)}"

    async def _identify_event(self, user_message: str, start_date: str, end_date: str) -> str:
        try:
            # Get events for the specified date range
            events = await self._list_events({"start_date": start_date, "end_date": end_date})
            
            # Use OpenAI to identify the event
            event_id = self.openai_client.identify_event(user_message, events)
            
            if event_id == 'UNCLEAR':
                return "I'm sorry, I couldn't determine which event you're referring to. Could you please provide more details?"
            
            # Find the identified event in the list
            identified_event = next((event for event in events if event['id'] == event_id), None)
            
            if identified_event:
                return f"I believe you're referring to the event '{identified_event['summary']}' (ID: {event_id}). Is that correct?"
            else:
                return "I'm sorry, I couldn't find the event you're referring to. Could you please provide more details?"
        
        except Exception as e:
            logger.error(f"Error in identifying event: {str(e)}", exc_info=True)
            return f"An error occurred while identifying the event: {str(e)}"

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
                            "timezone": {"type": "string", "description": "The timezone for the search (optional, default is NULL)"}
                        },
                        "required": ["start_date", "end_date", "duration", "timezone"],
                        "additionalProperties": False
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
                            "timezone": {"type": "string", "description": "The timezone for the event (optional, default is NULL)"}
                        },
                        "required": ["summary", "start_time", "end_time", "description", "location", "timezone"],
                        "additionalProperties": False
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
                        },
                        "required": ["event_id", "summary", "start_time", "end_time"],
                        "additionalProperties": False
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
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_events",
                    "description": "List events in the calendar within a given date range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "The start date of the range to check (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "The end date of the range to check (YYYY-MM-DD)"},
                            "timezone": {"type": "string", "description": "The timezone for the search (optional, default is NULL)"}
                        },
                        "required": ["start_date", "end_date", "timezone"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "identify_event",
                    "description": "Identify which event the user is referring to based on their message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_message": {"type": "string", "description": "The user's message about the event"},
                            "start_date": {"type": "string", "description": "The start date of the range to check (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "The end date of the range to check (YYYY-MM-DD)"}
                        },
                        "required": ["user_message", "start_date", "end_date"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        ]

    def get_instructions(self) -> str:
        return """You are a Calendar Assistant. Use the provided functions to complete the user's requests.
        - Checking available time slots in the calendar.
        - Creating new events in the calendar.
        - Updating existing events in the calendar.
        - Deleting events from the calendar.
        - Listing events within a given date range.
        - Identifying specific events based on user descriptions.

        When a user asks about updating or deleting an event, first use the identify_event function to determine which event they're referring to. Always confirm with the user before making any changes to preexisting events.

        When listing events, provide the event IDs along with other details to allow for easy updating or deleting of specific events.

        Provide clear and concise responses, and offer additional assistance if needed.
        
        Remember that you are an assistant and will be responding inside a chatbot. Make it sound human and conversational while being polite, helpful, and organized.
        All of your responses should be included in a single message.
        """