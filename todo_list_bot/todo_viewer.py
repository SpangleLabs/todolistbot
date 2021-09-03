import os
from os import listdir
from os.path import isfile, join, isdir
from typing import Dict, Optional, List

from prometheus_client import Counter
from telethon import Button

from todo_list_bot.response import Response
from todo_list_bot.todo_list import TodoList, TodoSection, TodoItem, TodoStatus, TodoContainer, line_is_item, \
    line_is_section, line_is_empty

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
replace = Counter("todolistbot_cmd_replace_total", "Number of times a section has been replaced")
cancel_replace = Counter("todolist_cmd_replace_total", "Number of times a replacement was cancelled")
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
        self.replacing: bool = False
        self._dir_list = None
        self._file_list = None

    def to_json(self) -> Dict:
        return {
            "chat_id": self.chat_id,
            "directory": self.base_directory,
            "current_directory": self.current_directory,
            "current_todo": self.current_todo.to_json() if self.current_todo is not None else None,
            "current_todo_path": self.current_todo_path,
            "replacing": self.replacing,
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
        viewer.replacing = json_data.get("replacing", False)
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
            if section == self.current_todo.root_section and section.is_empty():
                os.remove(self.current_todo.path)
                self.current_todo = None
                self.current_todo_path = []
                return self.list_files_message()
            section.remove()
            self.current_todo_path = self.current_todo_path[:len(self.current_todo_path)-1]
            self.current_todo.save()
            return self.current_todo_list_message()
        if cmd == b"replace":
            replace.inc()
            self.replacing = True
            return self.current_todo_list_message("Replacing todo list section, please enter the replacement todo list")
        if cmd == b"cancel_replace":
            cancel_replace.inc()
            self.replacing = False
            return self.current_todo_list_message("Replacement cancelled.")
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
        # If replacing, then remove the current section and set current to parent
        if self.replacing:
            self.replacing = False
            del_section = section
            section = section.parent_section
            del_section.remove()
            if section is None:
                section = TodoSection("root", 0, None)
                self.current_todo.root_section = section
        # Prepare for adding
        todo_contents = [l for l in entry_text.split("\n") if not line_is_empty(l)]
        # Ensure items are minimally indented
        items = [line for line in todo_contents if line_is_item(line)]
        if items:
            min_item_depth = min(len(line) - len(line.lstrip("- ")) for line in items)
            if min_item_depth < 2:
                add_depth = 2 - min_item_depth
                for n in range(len(todo_contents)):
                    if line_is_item(todo_contents[n]):
                        todo_contents[n] = "-" * add_depth + todo_contents[n]
        # Add to a section
        if isinstance(section, TodoSection):
            # Ensure subsections are minimally indented
            base_depth = section.depth
            sections = [line for line in todo_contents if line_is_section(line)]
            if sections:
                lowest_section = min(len(line) - len(line.lstrip("#")) for line in sections)
                if lowest_section <= base_depth:
                    for n in range(len(todo_contents)):
                        if line_is_section(todo_contents[n]):
                            todo_contents[n] = "#" * base_depth + todo_contents[n]
            self.current_todo.parse_lines(todo_contents, section)
            return self.current_todo_list_message("Added to todo list section")
        # Append sub items to an item
        if isinstance(section, TodoItem):
            if any(l for l in todo_contents if line_is_section(l)):
                return Response("Cannot add sections under an item")
            # Ensure sub items are minimally indented
            base_depth = section.depth
            min_depth = min(len(line) - len(line.lstrip(" -")) for line in todo_contents)
            add_depth = base_depth - min_depth + 2
            for n in range(len(todo_contents)):
                if add_depth > 0:
                    todo_contents[n] = "-" * add_depth + todo_contents[n]
                elif add_depth < 0:
                    todo_contents[n] = todo_contents[n][-add_depth:]
            current_item = section
            parent_section = section.parent_section
            for line in todo_contents:
                current_item = self.current_todo.parse_item(line, parent_section, current_item)
            return self.current_todo_list_message("Added to sub-items to todo list item")
        errors.inc()
        return Response("What")

    def current_section(self) -> Optional[TodoContainer]:
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
            current_section: TodoContainer,
            path_part: str
    ) -> Optional[TodoContainer]:
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
        buttons = []
        if section == self.current_todo.root_section:
            buttons += [Button.inline("🔙 Back to listing", "list")]
        else:
            buttons += [
                Button.inline("🔼 Up one level", "up")
            ]
        if section.is_empty():
            buttons += [
                Button.inline("🗑 Delete", "delete")
            ]
        buttons += [Button.inline("✏️ Edit/Replace", "replace")]
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
        if self.replacing:
            buttons = [Button.inline("❌ Cancel edit", "cancel_replace")]
        text = f"Opened todo list: <code>{self.current_todo.path}</code>.\n"
        text += f"<pre>{self.current_todo.to_text(section)}</pre>"
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
        text = "You have not selected a todo list. Please choose one:\n"
        if self.current_directory.strip("/").count("/") > self.base_directory.strip("/").count("/"):
            buttons += [Button.inline("🔼 Up directory", "up_folder")]
        buttons += [Button.inline(f"📂 {directory}", f"folder:{n}") for n, directory in enumerate(directories)]
        entries = [f"📂 <code>{directory}</code>" for directory in directories]
        buttons += [Button.inline(file, f"file:{n}") for n, file in enumerate(files)]
        entries += [f"- <code>{file}</code>" for file in files]
        text += "\n".join(entries)
        return Response(
            text,
            buttons
        )
