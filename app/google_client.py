import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
import datetime
import pickle
import io
from email.mime.text import MIMEText
import base64

class GoogleClient:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        self.creds = None
        self.calendar_service = None
        self.gmail_service = None
        self.drive_service = None
        self.authenticate()

    def authenticate(self):
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = Flow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    # Calendar methods
    def get_upcoming_events(self, max_results=10):
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = self.calendar_service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime').execute()
        return events_result.get('items', [])

    def create_event(self, summary, start_time, end_time, description=None, location=None):
        event = {
            'summary': summary,
            'start': {'dateTime': start_time},
            'end': {'dateTime': end_time},
        }
        if description:
            event['description'] = description
        if location:
            event['location'] = location

        return self.calendar_service.events().insert(calendarId='primary', body=event).execute()

    def get_free_busy(self, attendees):
        body = {
            "timeMin": datetime.datetime.utcnow().isoformat() + 'Z',
            "timeMax": (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z',
            "items": [{"id": attendee} for attendee in attendees]
        }
        return self.calendar_service.freebusy().query(body=body).execute().get('calendars', {})

    def get_events(self, start_date, end_date):
        events_result = self.calendar_service.events().list(
            calendarId='primary', timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z', singleEvents=True,
            orderBy='startTime').execute()
        return events_result.get('items', [])

    def create_calendar_event(self, event):
        return self.calendar_service.events().insert(calendarId='primary', body=event).execute()

    def get_event(self, event_id):
        return self.calendar_service.events().get(calendarId='primary', eventId=event_id).execute()

    def update_event(self, event_id, event):
        return self.calendar_service.events().update(calendarId='primary', eventId=event_id, body=event).execute()

    def delete_event(self, event_id):
        return self.calendar_service.events().delete(calendarId='primary', eventId=event_id).execute()

    def set_out_of_office(self, start_date, end_date, message):
        event = {
            'summary': 'Out of Office',
            'start': {'dateTime': start_date.isoformat()},
            'end': {'dateTime': end_date.isoformat()},
            'description': message,
            'transparency': 'opaque'
        }
        return self.create_calendar_event(event)

    # Gmail methods
    def send_email(self, to, subject, body):
        message = self.create_message('me', to, subject, body)
        return self.gmail_service.users().messages().send(userId='me', body=message).execute()

    def create_message(self, sender, to, subject, message_text):
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def schedule_recurring_event(self, summary, description, recurrence, callback):
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': datetime.datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + 'Z'},
            'recurrence': [recurrence]
        }
        created_event = self.create_calendar_event(event)
        # Assuming callback is a function that sends the email
        callback()
        return created_event

    # Drive methods
    def list_files(self, max_results=10):
        results = self.drive_service.files().list(
            pageSize=max_results, fields="nextPageToken, files(id, name)").execute()
        return results.get('files', [])

    def get_file_content(self, file_id):
        request = self.drive_service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file.getvalue().decode()

    def search_files(self, query):
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType)').execute()
        return results.get('files', [])