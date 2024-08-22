from app.config.base_config import BaseConfig

class EmailConfig(BaseConfig):
    SYSTEM_MESSAGE = """You are an email assistant parsing email requests. 
    When extracting information, follow these rules:
    1. Always extract the recipient's email address. If not provided, use 'example@example.com'.
    2. Always generate a suitable subject line based on the content.
    3. Always compose an appropriate email body based on the user's request.
    4. If any information is missing or unclear, use your best judgment to fill in the gaps.
    5. Always include 'to', 'subject', and 'body' fields in the output."""

    CATEGORY = "email"
    ASSISTANT_NAME = "GmailAssistant"
    CATEGORY_DESCRIPTION = "Messages about sending, responding to, or managing emails."
    FUNCTIONS = ["send_email", "create_draft"]

    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_MESSAGE},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following email request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]