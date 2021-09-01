from os import listdir
from os.path import isfile, join
from typing import Dict, Optional, List

from telethon import Button

from todo_list_bot.response import Response
from todo_list_bot.todo_list import TodoList


class TodoViewer:

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.directory = "store/"
        self.current_todo: Optional[TodoList] = None
        self._file_list = None

    def to_json(self) -> Dict:
        return {
            "chat_id": self.chat_id,
            "directory": self.directory,
            "current_todo": self.current_todo.to_json() if self.current_todo is not None else None,
            "_file_list": self._file_list
        }

    @classmethod
    def from_json(cls, json_data) -> 'TodoViewer':
        viewer = TodoViewer(json_data["chat_id"])
        viewer.directory = json_data["directory"]
        if json_data["current_todo"]:
            viewer.current_todo = TodoList.from_json(json_data["current_todo"])
        viewer._file_list = json_data["_file_list"]
        return viewer

    def list_files(self) -> List[str]:
        files = sorted([f for f in listdir(self.directory) if isfile(join(self.directory, f))])
        self._file_list = files
        return files

    def handle_callback(self, callback_data: bytes) -> Response:
        if callback_data.split(b":", 1)[0] == b"file":
            file_num = int(callback_data.split(b":")[1])
            filename = self._file_list[file_num]
            self.current_todo = TodoList(join(self.directory, filename))
            self.current_todo.parse()
            return self.current_todo_list_message()
        if callback_data == b"list":
            return self.list_files_message()
        return Response("I do not understand that button.")

    def current_message(self) -> Response:
        if self.current_todo is None:
            return self.list_files_message()
        return self.current_todo_list_message()

    def current_todo_list_message(self) -> Response:
        section = self.current_todo.root_section
        section_buttons = [
            Button.inline(f"📂 {s.title}", f"section:{n}") for n, s in enumerate(section.sub_sections)
        ]
        item_buttons = [
            Button.inline(item.title, f"item:{n}") for n, item in enumerate(section.root_items)
        ]
        return Response(
            f"Opened todo list: {self.current_todo.path}.\n{self.current_todo.to_text()}",
            buttons=[Button.inline("🔙 Back to listing", "list")] + section_buttons + item_buttons
        )

    def list_files_message(self) -> Response:
        files = self.list_files()
        return Response(
            "You have not selected a todo list. Please choose one:\n" + "\n".join(f"- {file}" for file in files),
            [Button.inline(file, f"file:{n}") for n, file in enumerate(files)]
        )

