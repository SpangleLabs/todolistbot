import dataclasses
import json
from typing import Dict, Any, List, Optional

from telethon import TelegramClient
from telethon.events import NewMessage, StopPropagation, CallbackQuery

from todo_list_bot.response import Response
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
        self.client.add_event_handler(self.handle_callback, CallbackQuery())
        self.client.add_event_handler(self.append_todo, NewMessage(incoming=True))
        self.client.start(bot_token=self.config.bot_token)
        self.client.run_until_disconnected()

    def save(self) -> None:
        self.viewer_store.save_to_json(self.config.viewer_store_filename)

    async def welcome(self, event: NewMessage.Event) -> None:
        if event.chat_id not in self.config.allowed_chat_ids:
            await event.respond("Apologies, but this bot is only available to certain users.")
            raise StopPropagation
        viewer = self.viewer_store.get_viewer(event.chat_id)
        response = viewer.current_message()
        self.viewer_store.response_cache.add_response(event.chat_id, response)
        await event.reply(
            "Welcome to Spangle's todo list bot.\n" + response.text,
            parse_mode="html",
            buttons=response.buttons()
        )
        self.save()
        raise StopPropagation

    async def handle_callback(self, event: CallbackQuery.Event) -> None:
        if not self.viewer_store.has_viewer(event.chat_id):
            raise StopPropagation
        # Check if response cache does something
        response = self.viewer_store.response_cache.handle_callback(event.chat_id, event.data)
        self.viewer_store.response_cache.add_response(event.chat_id, response)
        if response:
            await event.edit(
                response.text,
                parse_mode="html",
                buttons=response.buttons()
            )
            self.save()
            raise StopPropagation
        # Ask the viewer
        viewer = self.viewer_store.get_viewer(event.chat_id)
        response = viewer.handle_callback(event.data)
        self.viewer_store.response_cache.add_response(event.chat_id, response)
        await event.edit(
            response.text,
            parse_mode="html",
            buttons=response.buttons()
        )
        self.save()
        raise StopPropagation

    async def append_todo(self, event: NewMessage.Event) -> None:
        if not self.viewer_store.has_viewer(event.chat_id):
            raise StopPropagation
        viewer = self.viewer_store.get_viewer(event.chat_id)
        response = viewer.append_todo(event.message.message)
        self.viewer_store.response_cache.add_response(event.chat_id, response)
        await event.respond(
            response.text,
            parse_mode="html",
            buttons=response.buttons()
        )
        self.save()
        raise StopPropagation


class ResponseCache:

    def __init__(self):
        self.store = {}

    def add_response(self, chat_id: int, response: Response):
        self.store[chat_id] = response

    def handle_callback(self, chat_id: int, callback_data: bytes) -> Optional[Response]:
        if chat_id not in self.store:
            return None
        if callback_data.split(b":", 1)[0] == b"page":
            page_num = int(callback_data.split(b":")[1].decode())
            response = self.store[chat_id]
            if page_num > response.pages:
                raise StopPropagation
            response.page = page_num
            return response

    def to_json(self) -> Dict:
        return {
            str(chat_id): response.to_json() for chat_id, response in self.store.items()
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'ResponseCache':
        cache = ResponseCache()
        for chat_id, response_data in data.items():
            cache.add_response(int(chat_id), Response.from_json(response_data))
        return cache


class ViewerStore:

    def __init__(self):
        self.store = {}
        self.response_cache = ResponseCache()

    def add_viewer(self, viewer: TodoViewer) -> None:
        self.store[viewer.chat_id] = viewer

    def create_viewer(self, chat_id: int) -> TodoViewer:
        viewer = TodoViewer(chat_id)
        self.store[chat_id] = viewer
        return viewer

    def get_viewer(self, chat_id: int) -> TodoViewer:
        if chat_id not in self.store:
            self.create_viewer(chat_id)
        return self.store[chat_id]

    def has_viewer(self, chat_id: int) -> bool:
        return chat_id in self.store

    def save_to_json(self, filename: str) -> None:
        data = {
            "viewers": [viewer.to_json() for viewer in self.store.values()],
            "response_cache": self.response_cache.to_json()
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_json(cls, filename: str) -> 'ViewerStore':
        store = ViewerStore()
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return store
        else:
            for viewer_data in data["viewers"]:
                viewer = TodoViewer.from_json(viewer_data)
                store.add_viewer(viewer)
            store.response_cache = ResponseCache.from_json(data["response_cache"])
            return store
