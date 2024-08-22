from enum import Enum
from typing import Dict, Union
from app.config.email_config import EmailConfig
from app.config.travel_config import TravelConfig
from app.config.calendar_config import CalendarConfig
from app.config.general_config import GeneralConfig
from app.config.classifier_config import ClassifierConfig

class AssistantCategory(Enum):
    TRAVEL = "travel"
    SCHEDULE = "schedule"
    FAMILY = "family"
    TODO = "todo"
    DOCUMENT = "document"
    EMAIL = "email"
    SCHEDULE_EMAIL = "scheduleemail"
    GENERAL = "general"
    CLASSIFIER = "classifier"

class AssistantConfig:
    CONFIGS = {
        AssistantCategory.TRAVEL: TravelConfig(),
        AssistantCategory.SCHEDULE: CalendarConfig(),
        AssistantCategory.EMAIL: EmailConfig(),
        AssistantCategory.GENERAL: GeneralConfig(),
        AssistantCategory.CLASSIFIER: ClassifierConfig(),
        # Add other categories as needed
    }

    CATEGORY_DESCRIPTIONS = {
        category: config.CATEGORY_DESCRIPTION
        for category, config in CONFIGS.items()
    }

    CATEGORY_FUNCTIONS = {
        category: config.FUNCTIONS
        for category, config in CONFIGS.items()
    }

    @classmethod
    def get_all_assistant_names(cls):
        return [config.ASSISTANT_NAME for config in cls.CONFIGS.values()]

    @classmethod
    def get_assistant_name(cls, category: Union[str, AssistantCategory]) -> str:
        if isinstance(category, str):
            try:
                category = AssistantCategory(category.lower())
            except ValueError:
                return cls.CONFIGS[AssistantCategory.GENERAL].ASSISTANT_NAME
        return cls.CONFIGS.get(category, cls.CONFIGS[AssistantCategory.GENERAL]).ASSISTANT_NAME

    @classmethod
    def get_category_functions(cls, category: AssistantCategory) -> list:
        return cls.CONFIGS[category].FUNCTIONS

    @classmethod
    def get_category_description(cls, category: AssistantCategory) -> str:
        return cls.CONFIGS[category].CATEGORY_DESCRIPTION

