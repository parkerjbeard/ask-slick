from abc import ABC, abstractmethod

class BaseConfig(ABC):
    @property
    @abstractmethod
    def SYSTEM_MESSAGE(self) -> str:
        pass

    @abstractmethod
    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        pass

    @property
    @abstractmethod
    def CATEGORY(self) -> str:
        pass

    @property
    @abstractmethod
    def ASSISTANT_NAME(self) -> str:
        pass

    @property
    @abstractmethod
    def CATEGORY_DESCRIPTION(self) -> str:
        pass

    @property
    @abstractmethod
    def FUNCTIONS(self) -> list:
        pass