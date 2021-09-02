from typing import List, Optional, Dict

from telethon import Button
from telethon.tl.types import KeyboardButtonCallback


class Response:
    per_page = 6
    text_length_limit = 4096

    def __init__(self, text: str, buttons: Optional[List[KeyboardButtonCallback]] = None):
        self._text = text
        self.all_buttons = buttons
        self.page = 1

    def prefix(self, prefix: str) -> None:
        self._text = prefix + self._text

    @property
    def text(self) -> str:
        return self._text[:self.text_length_limit - 4] + "\n..."

    @property
    def pages(self) -> Optional[int]:
        if self.all_buttons is None:
            return None
        return ((len(self.all_buttons) - 1) // self.per_page) + 1

    @property
    def has_next(self) -> bool:
        if self.pages == 1 or self.all_buttons is None:
            return False
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        if self.pages == 1 or self.all_buttons is None:
            return False
        return self.page > 1

    def buttons(self) -> Optional[List[List[KeyboardButtonCallback]]]:
        if self.all_buttons is None:
            return None
        buttons = self.all_buttons[(self.page - 1) * self.per_page: self.page * self.per_page]
        if self.pages == 1:
            return [[b] for b in buttons]
        page_buttons = [
            Button.inline(
                "< Prev" if self.has_prev else " ",
                f"page:{self.page - 1}" if self.has_prev else f"page:{self.page}"
            ),
            Button.inline(
                "> Next" if self.has_next else " ",
                f"page:{self.page + 1}" if self.has_next else f"page:{self.page}"
            )
        ]
        return [
            *([b] for b in buttons),
            page_buttons
        ]

    def to_json(self) -> Dict:
        return {
            "text": self.text,
            "all_buttons": [
                {
                    "text": button.text,
                    "data": button.data.decode()
                } for button in self.all_buttons
            ] if self.all_buttons is not None else None,
            "page": self.page
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'Response':
        response = Response(
            data["text"],
            [Button.inline(d["text"], d["data"]) for d in data["all_buttons"]] if data["all_buttons"] is not None else None
        )
        response.page = data["page"]
        return response
