from app.config.base_config import BaseConfig

class ClassifierConfig(BaseConfig):
    SYSTEM_MESSAGE = "You are a classifier assistant that categorizes user inputs."
    CATEGORY = "classifier"
    ASSISTANT_NAME = "ClassifierAssistant"
    CATEGORY_DESCRIPTION = "Classifies user inputs into appropriate categories."
    FUNCTIONS = []

    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_MESSAGE},
            {"role": "user", "content": f"Classify the following user input:\n{user_input}"}
        ]