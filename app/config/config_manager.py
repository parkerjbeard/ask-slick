from app.config.assistant_config import AssistantCategory
from app.config.travel_config import TravelConfig
from app.config.calendar_config import CalendarConfig
from app.config.email_config import EmailConfig

class ConfigManager:
    def __init__(self):
        self.configs = {
            AssistantCategory.TRAVEL: TravelConfig(),
            AssistantCategory.CALENDAR: CalendarConfig(),
            AssistantCategory.EMAIL: EmailConfig()
        }

    def get_config(self, category: AssistantCategory):
        return self.configs.get(category)

    def add_config(self, category: AssistantCategory, config):
        self.configs[category] = config

    def get_assistant_names(self) -> dict:
        return {category: config.ASSISTANT_NAME for category, config in self.configs.items()}