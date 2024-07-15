import datetime
from typing import List, Dict, Optional
from app.google_client import GoogleClient
from app.openai_client import OpenAIClient

class CalendarAssistant:
    def __init__(self, google_client: GoogleClient, openai_client: OpenAIClient):
        self.google_client = google_client
        self.openai_client = openai_client

    def schedule_meeting(self, request: str) -> str:
        """
        Schedule a meeting based on the user's natural language request.
        """
        # Use OpenAI to parse the request
        parsed_request = self.openai_client.parse_meeting_request(request)
        
        # Extract relevant information
        attendees = parsed_request['attendees']
        duration = parsed_request['duration']
        preferred_time = parsed_request.get('preferred_time')
        
        # Find available time slots
        available_slots = self.find_available_slots(attendees, duration, preferred_time)
        
        if not available_slots:
            return "Sorry, I couldn't find any available time slots for all attendees."
        
        # Choose the best slot (for simplicity, we'll choose the first available slot)
        chosen_slot = available_slots[0]
        
        # Create the event
        event = self.create_event(attendees, chosen_slot, duration, parsed_request['title'])
        
        # Send invitation emails
        self.send_invitations(event)
        
        return f"Meeting '{event['summary']}' scheduled for {event['start']['dateTime']}."

    def find_available_slots(self, attendees: List[str], duration: int, preferred_time: Optional[datetime.datetime] = None) -> List[datetime.datetime]:
        """
        Find available time slots for all attendees.
        """
        # Get free/busy information for all attendees
        free_busy = self.google_client.get_free_busy(attendees)
        
        # Logic to find common free slots
        # This is a simplified version and should be expanded for real-world use
        available_slots = []
        start_time = preferred_time or datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = start_time.replace(hour=17)  # Assuming 9 AM to 5 PM workday
        
        while start_time < end_time:
            if all(self.is_time_free(attendee, start_time, duration, free_busy) for attendee in attendees):
                available_slots.append(start_time)
            start_time += datetime.timedelta(minutes=30)
        
        return available_slots

    def is_time_free(self, attendee: str, start_time: datetime.datetime, duration: int, free_busy: Dict) -> bool:
        """
        Check if a specific time slot is free for an attendee.
        """
        end_time = start_time + datetime.timedelta(minutes=duration)
        for busy_period in free_busy.get(attendee, []):
            if (start_time >= busy_period['start'] and start_time < busy_period['end']) or \
               (end_time > busy_period['start'] and end_time <= busy_period['end']):
                return False
        return True

    def create_event(self, attendees: List[str], start_time: datetime.datetime, duration: int, title: str) -> Dict:
        """
        Create a calendar event.
        """
        end_time = start_time + datetime.timedelta(minutes=duration)
        event = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat()},
            'end': {'dateTime': end_time.isoformat()},
            'attendees': [{'email': attendee} for attendee in attendees],
        }
        return self.google_client.create_calendar_event(event)

    def send_invitations(self, event: Dict) -> None:
        """
        Send email invitations for the event.
        """
        for attendee in event['attendees']:
            self.google_client.send_email(
                to=attendee['email'],
                subject=f"Invitation: {event['summary']}",
                body=f"You've been invited to {event['summary']} at {event['start']['dateTime']}."
            )

    def find_open_slots(self, request: str) -> str:
        """
        Find open time slots based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_open_slots_request(request)
        
        duration = parsed_request['duration']
        date_range = parsed_request['date_range']
        
        open_slots = self.google_client.get_open_slots(duration, date_range)
        
        if not open_slots:
            return "Sorry, I couldn't find any open time slots in the specified date range."
        
        return f"Here are your open time slots:\n" + "\n".join([slot.strftime("%Y-%m-%d %H:%M") for slot in open_slots])

    def send_coordination_email(self, request: str) -> str:
        """
        Send a coordination email based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_coordination_email_request(request)
        
        recipients = parsed_request['recipients']
        subject = parsed_request['subject']
        body = parsed_request['body']
        
        for recipient in recipients:
            self.google_client.send_email(to=recipient, subject=subject, body=body)
        
        return f"Coordination email sent to {', '.join(recipients)}."

    def get_daily_schedule(self) -> str:
        """
        Retrieve the user's daily schedule.
        """
        today = datetime.date.today()
        events = self.google_client.get_events(today, today + datetime.timedelta(days=1))
        
        if not events:
            return "You have no events scheduled for today."
        
        schedule = "Here's your schedule for today:\n"
        for event in events:
            start_time = datetime.datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
            end_time = datetime.datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
            schedule += f"- {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}: {event['summary']}\n"
        
        return schedule

    def reschedule_meeting(self, request: str) -> str:
        """
        Reschedule an existing meeting based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_reschedule_request(request)
        
        event_id = parsed_request['event_id']
        new_time = parsed_request['new_time']
        
        event = self.google_client.get_event(event_id)
        if not event:
            return "Sorry, I couldn't find the specified event."
        
        old_time = event['start']['dateTime']
        event['start']['dateTime'] = new_time.isoformat()
        event['end']['dateTime'] = (new_time + datetime.timedelta(minutes=parsed_request['duration'])).isoformat()
        
        updated_event = self.google_client.update_event(event_id, event)
        
        # Notify attendees
        for attendee in updated_event['attendees']:
            self.google_client.send_email(
                to=attendee['email'],
                subject=f"Meeting Rescheduled: {updated_event['summary']}",
                body=f"The meeting '{updated_event['summary']}' has been rescheduled from {old_time} to {updated_event['start']['dateTime']}."
            )
        
        return f"Meeting '{updated_event['summary']}' rescheduled to {updated_event['start']['dateTime']}."

    def cancel_meeting(self, request: str) -> str:
        """
        Cancel an existing meeting based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_cancel_request(request)
        
        event_id = parsed_request['event_id']
        
        event = self.google_client.get_event(event_id)
        if not event:
            return "Sorry, I couldn't find the specified event."
        
        self.google_client.delete_event(event_id)
        
        # Notify attendees
        for attendee in event['attendees']:
            self.google_client.send_email(
                to=attendee['email'],
                subject=f"Meeting Cancelled: {event['summary']}",
                body=f"The meeting '{event['summary']}' scheduled for {event['start']['dateTime']} has been cancelled."
            )
        
        return f"Meeting '{event['summary']}' has been cancelled."

    def get_meeting_details(self, request: str) -> str:
        """
        Retrieve details of a specific meeting based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_meeting_details_request(request)
        
        event_id = parsed_request['event_id']
        
        event = self.google_client.get_event(event_id)
        if not event:
            return "Sorry, I couldn't find the specified event."
        
        details = f"Meeting: {event['summary']}\n"
        details += f"Time: {event['start']['dateTime']} - {event['end']['dateTime']}\n"
        details += f"Attendees: {', '.join([attendee['email'] for attendee in event['attendees']])}\n"
        if 'description' in event:
            details += f"Description: {event['description']}\n"
        if 'location' in event:
            details += f"Location: {event['location']}\n"
        
        return details

    def set_out_of_office(self, request: str) -> str:
        """
        Set an out-of-office period based on the user's natural language request.
        """
        parsed_request = self.openai_client.parse_out_of_office_request(request)
        
        start_date = parsed_request['start_date']
        end_date = parsed_request['end_date']
        message = parsed_request['message']
        
        self.google_client.set_out_of_office(start_date, end_date, message)
        
        return f"Out-of-office set from {start_date} to {end_date}."

# Example usage:
# calendar_assistant = CalendarAssistant(GoogleClient(), OpenAIClient())
# result = calendar_assistant.schedule_meeting("Schedule a meeting with John and Sarah for 1 hour next Tuesday at 2 PM")
# print(result)