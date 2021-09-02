from os import listdir
from os.path import isfile, join, isdir
from typing import Dict, Optional, List, Union

from prometheus_client import Counter
from telethon import Button

from todo_list_bot.response import Response
from todo_list_bot.todo_list import TodoList, TodoSection, TodoItem, TodoStatus

errors = Counter("todolistbot_viewer_errors_total", "Number of errors in the todo viewer")
file_selected = Counter("todolistbot_cmd_file_total", "Number of times a file has been opened")
file_list = Counter("todolistbot_cmd_file_list_total", "Number of times a user has listed the files")
folder_selected = Counter("todolistbot_cmd_folder_total", "Number of times a user has selected a folder")
up_folder = Counter("todolistbot_cmd_folder_up_total", "Number of times user has requested to go up a directors")
section_selected = Counter("todolistbot_cmd_section_total", "Number of times user has selected a section")
item_selected = Counter("todolistbot_cmd_item_total", "Number of times user has selected an item")
nav_up = Counter("todolistbot_cmd_up_total", "Number of times a user has navigated out of a section or item")
item_done = Counter("todolistbot_cmd_item_done_total", "Number of items marked done")
item_inp = Counter("todolistbot_cmd_item_inp_total", "Number of items marked in progress")
item_todo = Counter("todolistbot_cmd_item_todo_total", "Number of items marked to do")
delete = Counter("todolistbot_cmd_delete_total", "Number of items or sections deleted")
create_file = Counter("todolistbot_create_file_total", "Number of files created")
create_section = Counter("todolistbot_create_section_total", "Number of sections created")
create_item = Counter("todolistbot_create_item_total", "Number of items created")


class TodoViewer:

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.base_directory = "store/"
        self.current_directory = self.base_directory
        self.current_todo: Optional[TodoList] = None
        self.current_todo_path: Optional[List[str]] = None
        self._dir_list = None
        self._file_list = None

    def to_json(self) -> Dict:
        return {
            "chat_id": self.chat_id,
            "directory": self.base_directory,
            "current_directory": self.current_directory,
            "current_todo": self.current_todo.to_json() if self.current_todo is not None else None,
            "current_todo_path": self.current_todo_path,
            "_dir_list": self._dir_list,
            "_file_list": self._file_list
        }

    @classmethod
    def from_json(cls, json_data) -> 'TodoViewer':
        viewer = TodoViewer(json_data["chat_id"])
        viewer.directory = json_data["directory"]
        viewer.current_directory = json_data.get("current_directory", json_data["directory"])
        if json_data["current_todo"]:
            viewer.current_todo = TodoList.from_json(json_data["current_todo"])
        viewer.current_todo_path = json_data.get("current_todo_path")
        viewer._dir_list = json_data.get("_dir_list")
        viewer._file_list = json_data["_file_list"]
        return viewer

    def list_directories(self) -> List[str]:
        directories = sorted([f for f in listdir(self.current_directory) if isdir(join(self.current_directory, f))])
        self._dir_list = directories
        return directories

    def list_files(self) -> List[str]:
        files = sorted([f for f in listdir(self.current_directory) if isfile(join(self.current_directory, f))])
        self._file_list = files
        return files

    def handle_callback(self, callback_data: bytes) -> Response:
        cmd, *args = callback_data.split(b":", 1)
        args = args[0] if args else None
        if cmd == b"file":
            file_selected.inc()
            file_num = int(args.decode())
            filename = self._file_list[file_num]
            self.current_todo = TodoList(join(self.current_directory, filename))
            self.current_todo_path = []
            self.current_todo.parse()
            return self.current_todo_list_message()
        if cmd == b"list":
            file_list.inc()
            self.current_todo = None
            self.current_todo_path = []
            return self.list_files_message()
        if cmd == b"folder":
            folder_selected.inc()
            self.current_todo = None
            self.current_todo_path = []
            folder_num = int(args.decode())
            dir_split = self.current_directory.strip("/").split("/")
            self.current_directory = "/".join(dir_split + [self._dir_list[folder_num]])
            return self.list_files_message()
        if cmd == b"up_folder":
            up_folder.inc()
            self.current_todo = None
            self.current_todo_path = []
            if self.current_directory.strip("/") == self.base_directory.strip("/"):
                errors.inc()
                return Response("Can't go up from base directory")
            dir_split = self.current_directory.strip("/").split("/")
            self.current_directory = "/".join(dir_split[:len(dir_split)-1])
            return self.list_files_message()
        if cmd == b"section":
            section_selected.inc()
            if self.current_todo is None:
                errors.inc()
                return Response("No todo list is selected.")
            section = self.current_section()
            if isinstance(section, TodoSection):
                new_section = section.sub_sections[int(args.decode())]
            else:
                errors.inc()
                return Response("Invalid section")
            self.current_todo_path.append(new_section.title)
            return self.current_todo_list_message()
        if cmd == b"item":
            item_selected.inc()
            if self.current_todo is None:
                errors.inc()
                return Response("No todo list is selected.")
            section = self.current_section()
            if isinstance(section, TodoSection):
                new_section = section.root_items[int(args.decode())]
            elif isinstance(section, TodoItem):
                new_section = section.sub_items[int(args.decode())]
            else:
                errors.inc()
                return Response("Invalid item")
            self.current_todo_path.append(new_section.name)
            return self.current_todo_list_message()
        if cmd == b"up":
            nav_up.inc()
            if self.current_todo is None:
                errors.inc()
                return Response("No todo list is selected.")
            self.current_todo_path = self.current_todo_path[:len(self.current_todo_path)-1]
            return self.current_todo_list_message()
        if cmd == b"item_done":
            item_done.inc()
            item = self.current_section()
            if not isinstance(item, TodoItem):
                errors.inc()
                return Response("Item not currently selected.")
            item.status = TodoStatus.COMPLETE
            self.current_todo.save()
            return self.current_todo_list_message()
        if cmd == b"item_inp":
            item_inp.inc()
            item = self.current_section()
            if not isinstance(item, TodoItem):
                errors.inc()
                return Response("Item not currently selected.")
            item.status = TodoStatus.IN_PROGRESS
            self.current_todo.save()
            return self.current_todo_list_message()
        if cmd == b"item_todo":
            item_todo.inc()
            item = self.current_section()
            if not isinstance(item, TodoItem):
                errors.inc()
                return Response("Item not currently selected.")
            item.status = TodoStatus.TODO
            self.current_todo.save()
            return self.current_todo_list_message()
        if cmd == b"delete":
            delete.inc()
            section = self.current_section()
            if section is None:
                errors.inc()
                return Response("Unknown section.")
            section.remove()
            self.current_todo_path = self.current_todo_path[:len(self.current_todo_path)-1]
            self.current_todo.save()
            return self.current_todo_list_message()
        errors.inc()
        return Response("I do not understand that button.")

    def append_todo(self, entry_text: str) -> Response:
        if self.current_todo is None:
            create_file.inc()
            full_path = join(self.current_directory, entry_text)
            with open(full_path, "w") as f:
                f.write("")
            self.current_todo = TodoList(full_path)
            self.current_todo_path = []
            self.current_todo.parse()
            return self.current_todo_list_message("Created new todo list")
        section = self.current_section()
        if section is None:
            errors.inc()
            return Response("No todo list section selected.")
        if entry_text.startswith("#"):
            create_section.inc()
            title = entry_text.lstrip("#").strip()
            if section.sub_sections:
                depth = section.sub_sections[0].depth
            else:
                depth = section.depth + 1
            new_section = TodoSection(title, depth, section)
            self.current_todo.save()
            return self.current_todo_list_message(f"Added new section {new_section.to_text()}")
        create_item.inc()
        status, line = self.current_todo.parse_status(entry_text)
        item_text = line.lstrip(" -")
        depth = len(line) - len(item_text)
        parent_item = None
        if isinstance(section, TodoSection):
            if section.root_items:
                depth = max(depth, section.root_items[0].depth)
            parent_section = section
        elif isinstance(section, TodoItem):
            if section.sub_items:
                depth = max(depth, section.sub_items[0].depth)
            else:
                depth = max(depth, section.depth + 2)
            parent_section = section.parent_section
            parent_item = section
        else:
            errors.inc()
            return Response("Invalid state.")
        new_item = TodoItem(status, item_text.strip(), depth, parent_section, parent_item)
        self.current_todo.save()
        return self.current_todo_list_message(f"Added new item: {new_item.to_text()}")

    def current_section(self) -> Optional[Union['TodoSection', 'TodoItem']]:
        if self.current_todo is None:
            return None
        current_section = self.current_todo.root_section
        for path_part in self.current_todo_path:
            found = self.find_in_section(current_section, path_part)
            if not found:
                return self.current_todo.root_section
            else:
                current_section = found
        return current_section

    # noinspection PyMethodMayBeStatic
    def find_in_section(
            self,
            current_section: Union[TodoSection, TodoItem],
            path_part: str
    ) -> Optional[Union[TodoSection, TodoItem]]:
        if isinstance(current_section, TodoSection):
            for sub_section in current_section.sub_sections:
                if sub_section.title == path_part:
                    return sub_section
            for item in current_section.root_items:
                if item.name == path_part:
                    return item
        if isinstance(current_section, TodoItem):
            for item in current_section.sub_items:
                if item.name == path_part:
                    return item
        return None

    def current_message(self) -> Response:
        if self.current_todo is None:
            return self.list_files_message()
        return self.current_todo_list_message()

    def current_todo_list_message(self, prefix: Optional[str] = None) -> Response:
        section = self.current_section()
        buttons = [Button.inline("🔙 Back to listing", "list")]
        if section != self.current_todo.root_section:
            buttons += [
                Button.inline("🔼 Up one level", "up"),
                Button.inline("🗑 Delete", "delete")
            ]
        if isinstance(section, TodoSection):
            buttons += [
                Button.inline(item.name, f"item:{n}") for n, item in enumerate(section.root_items)
            ]
            buttons += [
                Button.inline(f"📂 {s.title}", f"section:{n}") for n, s in enumerate(section.sub_sections)
            ]
        if isinstance(section, TodoItem):
            if section.status != TodoStatus.COMPLETE:
                buttons += [Button.inline("✔️ Done", "item_done")]
            if section.status != TodoStatus.IN_PROGRESS:
                buttons += [Button.inline("⏳ In progress", "item_inp")]
            if section.status != TodoStatus.TODO:
                buttons += [Button.inline("❌ Not done", "item_todo")]
            buttons += [
                Button.inline(item.name, f"item:{n}") for n, item in enumerate(section.sub_items)
            ]
        text = f"Opened todo list: {self.current_todo.path}.\n{section.to_text()}"
        if prefix:
            text = prefix + "\n-----\n" + text
        return Response(
            text,
            buttons=buttons
        )

    def list_files_message(self) -> Response:
        directories = self.list_directories()
        files = self.list_files()
        buttons = []
        if self.current_directory.strip("/").count("/") > self.base_directory.strip("/").count("/"):
            buttons += [Button.inline("🔼 Up directory", "up_folder")]
        buttons += [Button.inline(f"📂 {directory}", f"folder:{n}") for n, directory in enumerate(directories)]
        buttons += [Button.inline(file, f"file:{n}") for n, file in enumerate(files)]
        return Response(
            "You have not selected a todo list. Please choose one:\n" + "\n".join(f"- {file}" for file in files),
            buttons
        )
