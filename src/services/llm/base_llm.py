from abc import ABC, abstractmethod


class LLMService(ABC):

    @abstractmethod
    def create_embedding(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        pass
