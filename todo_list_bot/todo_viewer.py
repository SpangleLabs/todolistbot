from os import listdir
from os.path import isfile, join
from typing import Dict, Optional

from todo_list_bot.todo_list import TodoList


class TodoViewer:

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.directory = "store/"
        self.current_todo: Optional[TodoList] = None

    def to_json(self) -> Dict:
        return {
            "chat_id": self.chat_id,
            "directory": self.directory,
            "current_todo": self.current_todo.to_json() if self.current_todo is not None else None
        }

    @classmethod
    def from_json(cls, json_data) -> 'TodoViewer':
        viewer = TodoViewer(json_data["chat_id"])
        viewer.directory = json_data["directory"]
        viewer.current_todo = TodoList.from_json()
        return viewer

    def current_message(self) -> str:
        if self.current_todo is None:
            return self.list_files_message()
        return "I am in an invalid state."

    def list_files_message(self):
        files = [f for f in listdir(self.directory) if isfile(join(self.directory, f))]
        return "You have not selected a todo list. Please choose one:\n" + "\n".join(f"- {file}" for file in files)
