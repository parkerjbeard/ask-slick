from abc import ABC, abstractmethod

class APIIntegration(ABC):
    @abstractmethod
    async def execute(self, function_name: str, params: dict) -> str:
        pass

    @abstractmethod
    def get_tools(self) -> list:
        pass

    @abstractmethod
    def get_instructions(self) -> str:
        pass