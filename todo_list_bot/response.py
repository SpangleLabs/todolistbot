from typing import List, Optional, Dict

from telethon import Button


class Response:
    per_page = 6

    def __init__(self, text: str, buttons: Optional[List[Button]] = None):
        self.text = text
        self.all_buttons = buttons
        self.page = 1

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

    def buttons(self) -> Optional[List[List[Button]]]:
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
            ],
            "page": self.page
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'Response':
        response = Response(
            data["text"],
            [Button.inline(d["text"], d["data"]) for d in data["all_buttons"]]
        )
        response.page = data["page"]
        return response
