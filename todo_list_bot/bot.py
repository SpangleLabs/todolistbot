import dataclasses
import json
from typing import Dict, Any, List

from telethon import TelegramClient
from telethon.events import NewMessage, StopPropagation

from todo_list_bot.todo_viewer import TodoViewer


@dataclasses.dataclass
class BotConfig:
    api_id: int
    api_hash: str
    bot_token: str
    storage_dir: str
    allowed_chat_ids: List[int]
    viewer_store_filename: str = "viewer_state.json"

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'BotConfig':
        return BotConfig(
            json_data["telegram"]["api_id"],
            json_data["telegram"]["api_hash"],
            json_data["telegram"]["bot_token"],
            json_data["storage_dir"],
            json_data["allowed_chat_ids"],
            json_data.get("viewer_store_filename", "viewer_store.json")
        )


class TodoListBot:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.client = TelegramClient("todolistbot", self.config.api_id, self.config.api_hash)
        self.viewer_store = ViewerStore.load_from_json(config.viewer_store_filename)

    def start(self) -> None:
        self.client.add_event_handler(self.welcome, NewMessage(pattern="/start", incoming=True))
        self.client.start(bot_token=self.config.bot_token)
        self.client.run_until_disconnected()

    async def welcome(self, event: NewMessage.Event) -> None:
        if event.chat_id not in self.config.allowed_chat_ids:
            await event.respond("Apologies, but this bot is only available to certain users.")
            raise StopPropagation
        viewer = self.viewer_store.get_viewer(event.chat_id)
        response = viewer.current_message()
        await event.reply(
            "Welcome to Spangle's todo list bot.\n" + response.text,
            parse_mode="html",
            buttons=response.buttons()
        )
        raise StopPropagation


class ViewerStore:

    def __init__(self):
        self.store = {}

    def add_viewer(self, viewer: TodoViewer) -> None:
        self.store[viewer.chat_id] = viewer

    def create_viewer(self, chat_id: int) -> TodoViewer:
        viewer = TodoViewer(chat_id)
        self.store[chat_id] = viewer
        return viewer

    def get_viewer(self, chat_id: int) -> TodoViewer:
        return self.store.get(chat_id, self.create_viewer(chat_id))

    def save_to_json(self, filename: str) -> None:
        data = {
            "viewers": [viewer.to_json() for viewer in self.store.values()]
        }
        with open(filename, "w") as f:
            json.dump(data, f)

    @classmethod
    def load_from_json(cls, filename: str) -> 'ViewerStore':
        with open(filename, "r") as f:
            data = json.load(f)
        store = ViewerStore()
        for viewer_data in data["viewers"]:
            viewer = TodoViewer.from_json(viewer_data)
            store.add_viewer(viewer)
        return store
