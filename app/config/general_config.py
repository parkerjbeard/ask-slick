from app.config.base_config import BaseConfig

class GeneralConfig(BaseConfig):
    SYSTEM_MESSAGE = "You are a general-purpose assistant."
    CATEGORY = "general"
    ASSISTANT_NAME = "GeneralAssistant"
    CATEGORY_DESCRIPTION = "General-purpose tasks and queries."
    FUNCTIONS = []

    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_MESSAGE},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nUser input:\n{user_input}"}
        ]