from app.config.assistant_config import AssistantCategory, AssistantConfig
from app.config.travel_config import TravelConfig
from app.config.calendar_config import CalendarConfig
from app.config.email_config import EmailConfig
from app.config.general_config import GeneralConfig
from app.config.classifier_config import ClassifierConfig

API_INTEGRATIONS = {
    AssistantCategory.TRAVEL.value: {
        "name": TravelConfig.ASSISTANT_NAME,
        "class": "app.services.api_integrations.travel_integration.TravelIntegration",
        "functions": TravelConfig.FUNCTIONS,
    },
    AssistantCategory.CALENDAR.value: {
        "name": CalendarConfig.ASSISTANT_NAME,
        "class": "app.services.api_integrations.calendar_integration.CalendarIntegration",
        "functions": CalendarConfig.FUNCTIONS,
    },
    AssistantCategory.EMAIL.value: {
        "name": EmailConfig.ASSISTANT_NAME,
        "class": "app.services.api_integrations.email_integration.EmailIntegration",
        "functions": EmailConfig.FUNCTIONS,
    },
    AssistantCategory.GENERAL.value: {
        "name": GeneralConfig.ASSISTANT_NAME,
        "class": "app.services.api_integrations.general_integration.GeneralIntegration",
        "functions": GeneralConfig.FUNCTIONS,
    },
    AssistantCategory.CLASSIFIER.value: {
        "name": ClassifierConfig.ASSISTANT_NAME,
        "class": "app.services.api_integrations.classifier_integration.ClassifierIntegration",
        "functions": ClassifierConfig.FUNCTIONS,
    },
}