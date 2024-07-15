import datetime
from typing import List, Dict, Optional
from google_client import GoogleClient
from openai_client import OpenAIClient

# ... (previous CalendarAssistant code) ...

class EmailSender:
    def __init__(self, google_client: GoogleClient, openai_client: OpenAIClient):
        self.google_client = google_client
        self.openai_client = openai_client
        self.email_thread = {}  # Store email threads by recipient

    def initiate_scheduling(self, request: str) -> str:
        """
        Initiate the scheduling process by sending an email to the assistant of another executive.
        """
        parsed_request = self.openai_client.parse_scheduling_request(request)
        
        recipient = parsed_request['recipient']
        executive = parsed_request['executive']
        meeting_details = parsed_request['meeting_details']
        
        email_body = self.generate_initial_email(executive, meeting_details)
        
        self.google_client.send_email(
            to=recipient,
            subject=f"Meeting Request with {executive}",
            body=email_body
        )
        
        self.update_email_thread(recipient, "assistant", email_body)
        
        return f"Scheduling request sent to {recipient} for a meeting with {executive}."

    def generate_initial_email(self, executive: str, meeting_details: Dict) -> str:
        """
        Generate the initial email to request a meeting.
        """
        return self.openai_client.generate_email(
            prompt=f"Generate a professional email to request a meeting with {executive}. "
                   f"Meeting details: {meeting_details}"
        )

    def process_response(self, email_content: str, sender: str) -> str:
        """
        Process the response from the other assistant and determine the next action.
        """
        self.update_email_thread(sender, "other", email_content)
        
        parsed_response = self.openai_client.parse_email_response(email_content)
        
        if parsed_response['action'] == 'confirm':
            return self.confirm_meeting(parsed_response['meeting_details'], sender)
        elif parsed_response['action'] == 'propose_alternative':
            return self.handle_alternative_proposal(parsed_response['proposed_times'], sender)
        else:
            return self.request_clarification(parsed_response['unclear_points'], sender)

    def confirm_meeting(self, meeting_details: Dict, sender: str) -> str:
        """
        Confirm the meeting and add it to the calendar.
        """
        event = self.google_client.create_calendar_event(meeting_details)
        
        confirmation_email = self.generate_confirmation_email(event, sender)
        self.google_client.send_email(
            to=sender,
            subject=f"Confirmed: Meeting with {meeting_details['attendees'][0]}",
            body=confirmation_email
        )
        
        self.update_email_thread(sender, "assistant", confirmation_email)
        
        return f"Meeting confirmed and added to the calendar for {event['start']['dateTime']}."

    def handle_alternative_proposal(self, proposed_times: List[datetime.datetime], sender: str) -> str:
        """
        Handle alternative time proposals from the other assistant.
        """
        available_slots = self.find_available_slots(proposed_times)
        
        if available_slots:
            response_email = self.generate_response_email(available_slots, sender)
            self.google_client.send_email(
                to=sender,
                subject="Re: Meeting Request - Alternative Times",
                body=response_email
            )
            self.update_email_thread(sender, "assistant", response_email)
            return "Responded with available time slots from the proposed alternatives."
        else:
            return self.request_more_options(sender)

    def request_clarification(self, unclear_points: List[str], sender: str) -> str:
        """
        Request clarification on unclear points in the email response.
        """
        clarification_email = self.generate_clarification_email(unclear_points, sender)
        self.google_client.send_email(
            to=sender,
            subject="Re: Meeting Request - Clarification Needed",
            body=clarification_email
        )
        self.update_email_thread(sender, "assistant", clarification_email)
        return "Sent a request for clarification on unclear points."

    def generate_confirmation_email(self, event: Dict, recipient: str) -> str:
        """
        Generate a confirmation email for the scheduled meeting.
        """
        context = self.get_email_thread_context(recipient)
        return self.openai_client.generate_email(
            prompt=f"Generate a professional email to confirm a meeting. "
                   f"Meeting details: {event}\n\n"
                   f"Previous email context:\n{context}"
        )

    def generate_response_email(self, available_slots: List[datetime.datetime], recipient: str) -> str:
        """
        Generate an email response with available time slots.
        """
        context = self.get_email_thread_context(recipient)
        return self.openai_client.generate_email(
            prompt=f"Generate a professional email to respond with available time slots. "
                   f"Available slots: {available_slots}\n\n"
                   f"Previous email context:\n{context}"
        )

    def generate_clarification_email(self, unclear_points: List[str], recipient: str) -> str:
        """
        Generate an email to request clarification on unclear points.
        """
        context = self.get_email_thread_context(recipient)
        return self.openai_client.generate_email(
            prompt=f"Generate a professional email to request clarification. "
                   f"Unclear points: {unclear_points}\n\n"
                   f"Previous email context:\n{context}"
        )

    def request_more_options(self, recipient: str) -> str:
        """
        Request more time options if none of the proposed times work.
        """
        context = self.get_email_thread_context(recipient)
        more_options_email = self.openai_client.generate_email(
            prompt=f"Generate a professional email to request more time options for a meeting.\n\n"
                   f"Previous email context:\n{context}"
        )
        self.google_client.send_email(
            to=recipient,
            subject="Re: Meeting Request - More Options Needed",
            body=more_options_email
        )
        self.update_email_thread(recipient, "assistant", more_options_email)
        return "Requested more time options for the meeting."

    def update_email_thread(self, recipient: str, sender: str, content: str):
        """
        Update the email thread with the latest message.
        """
        if recipient not in self.email_thread:
            self.email_thread[recipient] = []
        
        self.email_thread[recipient].append({
            'sender': sender,
            'content': content,
            'timestamp': datetime.datetime.now()
        })

    def get_email_thread_context(self, recipient: str, max_messages: int = 5) -> str:
        """
        Get the context of the email thread for a specific recipient.
        """
        if recipient not in self.email_thread:
            return ""
        
        context = ""
        for message in self.email_thread[recipient][-max_messages:]:
            context += f"{message['sender'].capitalize()}: {message['content']}\n\n"
        
        return context.strip()

    def find_available_slots(self, proposed_times: List[datetime.datetime]) -> List[datetime.datetime]:
        """
        Find available slots from the proposed times.
        This method should be implemented to check against the user's calendar.
        """
        # Placeholder implementation
        return [time for time in proposed_times if self.is_time_available(time)]

    def is_time_available(self, time: datetime.datetime) -> bool:
        """
        Check if a specific time is available in the user's calendar.
        This method should be implemented to check against the user's calendar.
        """
        # Placeholder implementation
        return True

# Example usage:
# email_sender = EmailSender(GoogleClient(), OpenAIClient())
# result = email_sender.initiate_scheduling("Schedule a meeting with John Doe's assistant for a 1-hour discussion on project updates next week")
# print(result)
#
# # Simulating a response from John Doe's assistant
# response = "Thank you for reaching out. John is available on Tuesday at 2 PM or Thursday at 11 AM next week. Would either of these times work?"
# result = email_sender.process_response(response, "john.doe.assistant@example.com")
# print(result)