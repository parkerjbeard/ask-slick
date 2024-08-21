from enum import Enum
from typing import Dict

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
    ASSISTANT_NAMES = {
        AssistantCategory.TRAVEL: "TravelAssistant",
        AssistantCategory.SCHEDULE: "CalendarAssistant",
        AssistantCategory.FAMILY: "FamilyAssistant",
        AssistantCategory.TODO: "TodoAssistant",
        AssistantCategory.DOCUMENT: "DocumentAssistant",
        AssistantCategory.EMAIL: "GmailAssistant",
        AssistantCategory.SCHEDULE_EMAIL: "ScheduleEmailAssistant",
        AssistantCategory.GENERAL: "GeneralAssistant",
        AssistantCategory.CLASSIFIER: "ClassifierAssistant"
    }

    CATEGORY_DESCRIPTIONS: Dict[AssistantCategory, str] = {
        AssistantCategory.SCHEDULE: "Messages about appointments, meetings, or time-specific events that don't involve sending emails.",
        AssistantCategory.FAMILY: "Messages related to family members, relationships, or household matters.",
        AssistantCategory.TRAVEL: "Messages about trips, vacations, flights, hotels, or any travel-related queries.",
        AssistantCategory.TODO: "Messages about tasks, to-do lists, or things that need to be done.",
        AssistantCategory.DOCUMENT: "Messages about creating, editing, or managing documents, files, or paperwork.",
        AssistantCategory.EMAIL: "Messages about sending, responding to, or managing emails.",
        AssistantCategory.SCHEDULE_EMAIL: "Messages that involve both scheduling an event and sending an email about it.",
        AssistantCategory.GENERAL: "Messages that don't fit into the other categories."
    }

    @classmethod
    def get_all_assistant_names(cls):
        return list(cls.ASSISTANT_NAMES.values())

    @classmethod
    def get_assistant_name(cls, category: str) -> str:
        try:
            return cls.ASSISTANT_NAMES[AssistantCategory(category.lower())]
        except ValueError:
            return cls.ASSISTANT_NAMES[AssistantCategory.GENERAL]