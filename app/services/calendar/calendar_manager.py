from app.google_client import get_google_service
from googleapiclient.errors import HttpError
from utils.logger import logger
from typing import Dict, Any, List
from datetime import datetime, timedelta

class CalendarManager:
    def __init__(self):
        self.service = get_google_service('calendar', 'v3')

    def check_available_slots(self, start_date: str, end_date: str, duration: int, timezone: str = 'UTC') -> str:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_datetime.isoformat() + 'Z',
                timeMax=end_datetime.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            available_slots = self._find_available_slots(events, start_datetime, end_datetime, duration, timezone)
            
            if not available_slots:
                return "No available slots found in the specified date range."
            
            formatted_slots = [slot.strftime('%Y-%m-%d %H:%M') for slot in available_slots]
            return f"Available slots:\n" + "\n".join(formatted_slots)

        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return f"An error occurred while checking available slots: {error}"

    def _find_available_slots(self, events: List[Dict[str, Any]], start: datetime, end: datetime, duration: int, timezone: str) -> List[datetime]:
        available_slots = []
        current = start
        
        for event in events:
            event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
            event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
            
            while current + timedelta(minutes=duration) <= event_start:
                if current + timedelta(minutes=duration) <= end:
                    available_slots.append(current)
                current += timedelta(minutes=30)  # Check every 30 minutes
            
            current = max(current, event_end)
        
        while current + timedelta(minutes=duration) <= end:
            available_slots.append(current)
            current += timedelta(minutes=30)
        
        return available_slots

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = '', location: str = '', timezone: str = 'UTC') -> str:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
        }

        try:
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            return f'Event created: {event.get("htmlLink")}'
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return f"An error occurred while creating the event: {error}"

    def update_event(self, event_id: str, summary: str = None, start_time: str = None, end_time: str = None, description: str = None, location: str = None) -> str:
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            
            if summary:
                event['summary'] = summary
            if start_time:
                event['start']['dateTime'] = start_time
            if end_time:
                event['end']['dateTime'] = end_time
            if description:
                event['description'] = description
            if location:
                event['location'] = location

            updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            return f'Event updated: {updated_event.get("htmlLink")}'
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return f"An error occurred while updating the event: {error}"

    def delete_event(self, event_id: str) -> str:
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return 'Event deleted successfully.'
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return f"An error occurred while deleting the event: {error}"

def create_calendar_manager() -> CalendarManager:
    return CalendarManager()