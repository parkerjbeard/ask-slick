from app.google_client import get_google_service
from googleapiclient.errors import HttpError
from utils.logger import logger
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import mimetypes
import os

class GmailManager:
    def __init__(self, user_id: str):
        logger.debug(f"Initializing GmailManager for user_id: {user_id}")
        self.user_id = user_id
        self.service = get_google_service(user_id, 'gmail', 'v1')
        logger.debug(f"GmailManager initialized for user: {user_id}")

    def _create_message(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject

        msg = MIMEText(body)
        message.attach(msg)

        if attachments:
            for file in attachments:
                content_type, encoding = mimetypes.guess_type(file)
                if content_type is None or encoding is not None:
                    content_type = 'application/octet-stream'
                main_type, sub_type = content_type.split('/', 1)
                with open(file, 'rb') as fp:
                    msg = MIMEBase(main_type, sub_type)
                    msg.set_payload(fp.read())
                filename = os.path.basename(file)
                msg.add_header('Content-Disposition', 'attachment', filename=filename)
                encoders.encode_base64(msg)
                message.attach(msg)

        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    async def create_draft(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> str:
        try:
            message = self._create_message(to, subject, body, attachments)
            draft = self.service.users().drafts().create(userId='me', body={'message': message}).execute()
            logger.debug(f"[User: {self.user_id}] Draft created successfully")
            return f"Draft created successfully. Draft ID: {draft['id']}"
        except HttpError as error:
            logger.error(f'[User: {self.user_id}] An error occurred while creating draft: {error}')
            return f"An error occurred while creating draft: {error}"

    async def send_email(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> str:
        try:
            message = self._create_message(to, subject, body, attachments)
            sent_message = self.service.users().messages().send(userId='me', body=message).execute()
            logger.debug(f"[User: {self.user_id}] Email sent successfully")
            return f"Email sent successfully. Message ID: {sent_message['id']}"
        except HttpError as error:
            logger.error(f'[User: {self.user_id}] An error occurred while sending email: {error}')
            return f"An error occurred while sending email: {error}"