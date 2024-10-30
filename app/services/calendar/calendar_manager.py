from app.google_client import get_google_service
from googleapiclient.errors import HttpError
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from app.config.settings import settings
from utils.logger import logger
from dotenv import load_dotenv
from datetime import time
load_dotenv()
import pytz

class CalendarManager:
    def __init__(self, user_id: str):
        logger.debug(f"Initializing CalendarManager for user_id: {user_id}")
        self.user_id = user_id  # Store user_id for logging purposes
        self.service = get_google_service(user_id, 'calendar', 'v3')
        self.default_timezone = settings.DEFAULT_TIMEZONE
        logger.debug(f"CalendarManager initialized with default timezone: {self.default_timezone}")

    def check_available_slots(self, start_date: str, end_date: str, duration: int, timezone: str = None) -> str:
        logger.debug(f"[User: {self.user_id}] Checking available slots: start_date={start_date}, end_date={end_date}, duration={duration}, timezone={timezone}")
        timezone = timezone or self.default_timezone
        tz = pytz.timezone(timezone)
        
        try:
            start_datetime = tz.localize(datetime.strptime(start_date, '%Y-%m-%d'))
            end_datetime = tz.localize(datetime.strptime(end_date, '%Y-%m-%d')) + timedelta(days=1)

            freebusy_query = {
                "timeMin": start_datetime.isoformat(),
                "timeMax": end_datetime.isoformat(),
                "timeZone": timezone,
                "items": [{"id": 'primary'}]
            }
            logger.debug(f"[User: {self.user_id}] Executing freebusy query: {freebusy_query}")
            freebusy = self.service.freebusy().query(body=freebusy_query).execute()
            busy_times = freebusy.get('calendars', {}).get('primary', {}).get('busy', [])
            logger.debug(f"[User: {self.user_id}] Found {len(busy_times)} busy time slots")

            available_blocks = self._find_available_blocks(start_datetime, end_datetime, busy_times, (9, 17), timedelta(minutes=duration), 5, tz)
            return self._format_availability(available_blocks, timezone)

        except Exception as e:
            logger.error(f'[User: {self.user_id}] Unexpected error in check_available_slots: {e}')
            return f"An unexpected error occurred: {e}"

    def _find_available_blocks(self, start: datetime, end: datetime, busy_times: List[Dict[str, Any]], working_hours: Tuple[int, int], duration: timedelta, interval: int, tz: pytz.tzinfo) -> List[Tuple[datetime, List[Tuple[datetime, datetime]]]]:
        logger.debug(f"Finding available blocks: start={start}, end={end}, duration={duration}, interval={interval}, timezone={tz}")
        available_blocks = []

        current_date = start.date()
        end_date = end.date()

        while current_date <= end_date:
            day_start = tz.localize(datetime.combine(current_date, time(working_hours[0], 0)))
            day_end = tz.localize(datetime.combine(current_date, time(working_hours[1], 0)))

            if day_start < start:
                day_start = start
            if day_end > end:
                day_end = end

            day_busy_times = [
                (datetime.fromisoformat(busy['start']).astimezone(tz),
                 datetime.fromisoformat(busy['end']).astimezone(tz))
                for busy in busy_times
                if datetime.fromisoformat(busy['start']).astimezone(tz).date() == current_date
            ]

            if not day_busy_times:
                available_blocks.append((day_start, [(day_start, day_end)]))
            else:
                day_blocks = []
                current_time = day_start

                for busy_start, busy_end in sorted(day_busy_times):
                    if current_time + duration <= busy_start:
                        day_blocks.append((current_time, busy_start))
                    current_time = max(current_time, busy_end)

                if current_time + duration <= day_end:
                    day_blocks.append((current_time, day_end))

                if day_blocks:
                    available_blocks.append((day_start, day_blocks))

            current_date += timedelta(days=1)

        logger.debug(f"Available blocks after processing: {available_blocks}")
        return available_blocks

    def _format_availability(self, available_blocks: List[Tuple[datetime, List[Tuple[datetime, datetime]]]], timezone: str) -> str:
        if not available_blocks:
            return "No available slots found in the given date range."

        result = f"Available time blocks (timezone: {timezone}):\n\n"
        for date, blocks in available_blocks:
            result += f"{date.strftime('%A, %B %d, %Y')}:\n"
            for start, end in blocks:
                if end - start >= timedelta(hours=7):  # Full day or close to it
                    result += f"  All day ({start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')})\n"
                else:
                    result += f"  {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}\n"
            result += "\n"

        return result.strip()

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = '', location: str = '', timezone: str = None) -> str:
        timezone = timezone or self.default_timezone
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
            'reminders': {
                'useDefault': True,
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

    def list_events(self, start_date: str, end_date: str, timezone: str = None) -> List[Dict[str, Any]]:
        logger.debug(f"Listing events: start_date={start_date}, end_date={end_date}, timezone={timezone}")
        timezone = timezone or self.default_timezone
        tz = pytz.timezone(timezone)
        
        try:
            start_datetime = tz.localize(datetime.strptime(start_date, '%Y-%m-%d'))
            end_datetime = tz.localize(datetime.strptime(end_date, '%Y-%m-%d')) + timedelta(days=1)

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_datetime.isoformat(),
                timeMax=end_datetime.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            return [
                {
                    'id': event['id'],
                    'summary': event['summary'],
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                }
                for event in events
            ]

        except Exception as e:
            logger.error(f'Unexpected error in list_events: {e}')
            raise

def create_calendar_manager(user_id: str) -> CalendarManager:
    logger.debug("Creating CalendarManager instance")
    return CalendarManager(user_id)