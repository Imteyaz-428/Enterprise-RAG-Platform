from abc import ABC, abstractmethod
from typing import Iterator


class BaseProvider(ABC):

    @abstractmethod
    def generate(
        self,
        prompt: str,
    ) -> str:
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
    ) -> Iterator[str]:
        pass