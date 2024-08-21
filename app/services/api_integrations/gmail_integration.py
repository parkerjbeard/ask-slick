from typing import Dict, Any, List
from app.services.api_integrations import APIIntegration
from app.services.gmail.gmail_manager import GmailManager
from utils.logger import logger

class GmailIntegration(APIIntegration):
    def __init__(self):
        self.gmail_manager = GmailManager()

    async def execute(self, function_name: str, params: dict) -> str:
        logger.debug(f"GmailIntegration executing function: {function_name} with params: {params}")
        
        if function_name == "send_email":
            return await self._send_email(params)
        elif function_name == "create_draft":
            return await self._create_draft(params)
        else:
            logger.warning(f"Unknown function in GmailIntegration: {function_name}")
            return f"Unknown function: {function_name}"

    async def _send_email(self, params: dict) -> str:
        logger.debug(f"Structured JSON for email: {params}")
        attachments = params.get("attachments", [])
        return await self.gmail_manager.send_email(params["to"], params["subject"], params["body"], attachments)

    async def _create_draft(self, params: dict) -> str:
        logger.debug(f"Structured JSON for draft: {params}")
        attachments = params.get("attachments", [])
        return await self.gmail_manager.create_draft(params["to"], params["subject"], params["body"], attachments)

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send a new email with the provided details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body content"},
                            "attachments": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to attach"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_draft",
                    "description": "Create a draft email with the provided details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body content"},
                            "attachments": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to attach"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            }
        ]

    def get_instructions(self) -> str:
        return """You are a Gmail Assistant. Your responsibility is to compose and send emails or create drafts based on user requests.
        When a user asks to send an email, use the 'send_email' function.
        When a user asks to create a draft, use the 'create_draft' function.
        Send the email or create the draft immediately without asking for confirmation unless the user specifically requests to review it first.
        Provide clear and concise responses, and offer additional assistance if needed.
        """