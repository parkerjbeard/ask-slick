from app.services.gmail.gmail_manager import GmailManager
from app.services.api_integrations import APIIntegration
from typing import Dict, Any, List
from utils.logger import logger

class GmailIntegration(APIIntegration):
    def __init__(self, user_id: str):
        logger.debug(f"Initializing GmailIntegration with user_id: {user_id}")
        if not user_id:
            logger.error("Attempted to initialize GmailIntegration with empty user_id")
            raise ValueError("user_id is required for GmailIntegration")
        self.user_id = user_id
        logger.info(f"Creating GmailManager for user_id: {user_id}")
        self.gmail_manager = GmailManager(user_id)

    async def execute(self, function_name: str, params: dict) -> str:
        logger.debug(f"GmailIntegration executing function for user {self.user_id}: {function_name}")
        
        # Remove user_id from params before passing to gmail_manager
        params = {k: v for k, v in params.items() if k != 'user_id'}
        
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
                        "required": ["to", "subject", "body", "attachments"],
                        "additionalProperties": False
                    },
                    "strict": True
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
                        "required": ["to", "subject", "body", "attachments"],
                        "additionalProperties": False
                    },
                    "strict": True
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