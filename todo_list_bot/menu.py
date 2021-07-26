from abc import ABC, abstractmethod
from typing import List, Dict


class Menu(ABC):
    @abstractmethod
    @property
    def text(self) -> str:
        return None

    @abstractmethod
    @property
    def buttons(self) -> List[List[Button]]:
        return None

    @abstractmethod
    def handle_callback(self, callback_data: bytes) -> None:
        return None


class PersistentMenu(Menu, ABC):
    @abstractmethod
    def to_json(self) -> Dict:
        return None

    @classmethod
    @abstractmethod
    def from_json(cls, data: Dict) -> 'PersistentMenu':
        raise NotImplementedError


class SentMenu:
    menu: Menu
    msg: Message
    ?
    chat_id: int
    msg_id: int
