from abc import ABC, abstractmethod


class BotPlatform(ABC):
    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
