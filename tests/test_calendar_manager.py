import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from app.services.calendar.calendar_manager import CalendarAssistant
from app.google_client import GoogleClient
from app.openai_helper import OpenAIClient

class TestCalendarAssistant(unittest.TestCase):
    def setUp(self):
        self.google_client = MagicMock(spec=GoogleClient)
        self.openai_client = MagicMock(spec=OpenAIClient)
        self.calendar_assistant = CalendarAssistant(self.google_client, self.openai_client)

    def test_schedule_meeting(self):
        request = "Schedule a meeting with John and Sarah for 1 hour next Tuesday at 2 PM"
        parsed_request = {
            'attendees': ['john@example.com', 'sarah@example.com'],
            'duration': 60,
            'preferred_time': datetime(2023, 10, 10, 14, 0),
            'title': 'Team Meeting'
        }
        self.openai_client.parse_meeting_request.return_value = parsed_request
        self.google_client.get_free_busy.return_value = {
            'john@example.com': [],
            'sarah@example.com': []
        }
        self.google_client.create_calendar_event.return_value = {
            'summary': 'Team Meeting',
            'start': {'dateTime': '2023-10-10T14:00:00'},
            'end': {'dateTime': '2023-10-10T15:00:00'},
            'attendees': [{'email': 'john@example.com'}, {'email': 'sarah@example.com'}]
        }

        result = self.calendar_assistant.schedule_meeting(request)
        self.assertIn("Meeting 'Team Meeting' scheduled for 2023-10-10T14:00:00.", result)

    def test_find_open_slots(self):
        request = "Find open slots for a 1-hour meeting next week"
        parsed_request = {
            'duration': 60,
            'date_range': (datetime(2023, 10, 9), datetime(2023, 10, 15))
        }
        self.openai_client.parse_open_slots_request.return_value = parsed_request
        self.google_client.get_open_slots.return_value = [
            datetime(2023, 10, 10, 10, 0),
            datetime(2023, 10, 11, 14, 0)
        ]

        result = self.calendar_assistant.find_open_slots(request)
        self.assertIn("Here are your open time slots:", result)
        self.assertIn("2023-10-10 10:00", result)
        self.assertIn("2023-10-11 14:00", result)

    def test_send_coordination_email(self):
        request = "Send an email to John and Sarah about the project update"
        parsed_request = {
            'recipients': ['john@example.com', 'sarah@example.com'],
            'subject': 'Project Update',
            'body': 'Please find the latest project update attached.'
        }
        self.openai_client.parse_coordination_email_request.return_value = parsed_request

        result = self.calendar_assistant.send_coordination_email(request)
        self.assertIn("Coordination email sent to john@example.com, sarah@example.com.", result)

    def test_get_daily_schedule(self):
        today = datetime.today().date()
        events = [
            {
                'summary': 'Morning Meeting',
                'start': {'dateTime': (datetime.now() + timedelta(hours=1)).isoformat()},
                'end': {'dateTime': (datetime.now() + timedelta(hours=2)).isoformat()}
            },
            {
                'summary': 'Lunch with Sarah',
                'start': {'dateTime': (datetime.now() + timedelta(hours=4)).isoformat()},
                'end': {'dateTime': (datetime.now() + timedelta(hours=5)).isoformat()}
            }
        ]
        self.google_client.get_events.return_value = events

        result = self.calendar_assistant.get_daily_schedule()
        self.assertIn("Here's your schedule for today:", result)
        self.assertIn("Morning Meeting", result)
        self.assertIn("Lunch with Sarah", result)

    def test_reschedule_meeting(self):
        request = "Reschedule the meeting with ID 12345 to next Wednesday at 3 PM"
        parsed_request = {
            'event_id': '12345',
            'new_time': datetime(2023, 10, 11, 15, 0),
            'duration': 60
        }
        self.openai_client.parse_reschedule_request.return_value = parsed_request
        event = {
            'summary': 'Team Meeting',
            'start': {'dateTime': '2023-10-10T14:00:00'},
            'end': {'dateTime': '2023-10-10T15:00:00'},
            'attendees': [{'email': 'john@example.com'}, {'email': 'sarah@example.com'}]
        }
        self.google_client.get_event.return_value = event
        self.google_client.update_event.return_value = {
            'summary': 'Team Meeting',
            'start': {'dateTime': '2023-10-11T15:00:00'},
            'end': {'dateTime': '2023-10-11T16:00:00'},
            'attendees': [{'email': 'john@example.com'}, {'email': 'sarah@example.com'}]
        }

        result = self.calendar_assistant.reschedule_meeting(request)
        self.assertIn("Meeting 'Team Meeting' rescheduled to 2023-10-11T15:00:00.", result)

    def test_cancel_meeting(self):
        request = "Cancel the meeting with ID 12345"
        parsed_request = {
            'event_id': '12345'
        }
        self.openai_client.parse_cancel_request.return_value = parsed_request
        event = {
            'summary': 'Team Meeting',
            'start': {'dateTime': '2023-10-10T14:00:00'},
            'end': {'dateTime': '2023-10-10T15:00:00'},
            'attendees': [{'email': 'john@example.com'}, {'email': 'sarah@example.com'}]
        }
        self.google_client.get_event.return_value = event

        result = self.calendar_assistant.cancel_meeting(request)
        self.assertIn("Meeting 'Team Meeting' has been cancelled.", result)

    def test_get_meeting_details(self):
        request = "Get details of the meeting with ID 12345"
        parsed_request = {
            'event_id': '12345'
        }
        self.openai_client.parse_meeting_details_request.return_value = parsed_request
        event = {
            'summary': 'Team Meeting',
            'start': {'dateTime': '2023-10-10T14:00:00'},
            'end': {'dateTime': '2023-10-10T15:00:00'},
            'attendees': [{'email': 'john@example.com'}, {'email': 'sarah@example.com'}],
            'description': 'Discuss project updates',
            'location': 'Conference Room'
        }
        self.google_client.get_event.return_value = event

        result = self.calendar_assistant.get_meeting_details(request)
       