from enum import Enum
from typing import List, Optional


class TodoList:
    def __init__(self, path: str):
        self.path = path
        self.root_section = TodoSection("root", 0, None)
        self.sections = []
        self.items = []

    def parse(self) -> None:
        with open(self.path, "r") as f:
            contents = f.read()
        current_section = self.root_section
        current_item = None
        for line in contents:
            if line.strip() == "":
                continue
            if line.startswith("#"):
                current_section = self.parse_section(line, current_section)
                current_item = None
            else:
                self.parse_item(line, current_section, current_item)
        self.sections = self.root_section.sub_sections
        self.items = self.root_section.root_items

    def parse_section(self, line: str, current_section: 'TodoSection') -> 'TodoSection':
        section_title = line.lstrip("#")
        section_depth = len(line) - len(section_title)
        section_title = section_title.strip()
        if section_depth > current_section.depth:
            parent_section = current_section
        else:
            parent_section = current_section.parent
            while section_depth >= parent_section.depth:
                parent_section = parent_section.parent
        return TodoSection(section_title, section_depth, parent_section)
   
    def parse_item(self, line: str, current_section: 'TodoSection', current_item: 'TodoItem') -> 'TodoItem':
        status = TodoStatus.TODO
        for enum_status in TodoStatus:
            if line.startswith(enum_status.value):
                status = enum_status
                line = line[len(enum_status.value):]
                break
        item_text = line.lstrip(" -")
        item_depth = len(line) - len(item_text)
        item_text = item_text.strip()
        if item_depth > current_item.depth:
            parent_item = current_item
        else:
            parent_item = current_item
            while item_depth >= parent_item.depth:
                if parent_item.parent_item is not None:
                    parent_item = parent_item.parent_item
                else:
                    parent_item = None
                    break
        return TodoItem(status, item_text, item_depth, current_section, parent_item)

    def list_sections(self) -> List['TodoSection']:
        # TODO
        pass

    def list_items(self) -> List['TodoItem']:
        # Todo
        pass

    def to_text(self) -> str:
        pass

    def to_json(self):
        pass  # TODO

    @classmethod
    def from_json(cls):
        pass  # TODO


class TodoSection:
    def __init__(self, title: str, depth: int, parent: 'TodoSection'):
        self.title = title
        self.depth = depth
        self.parent = parent
        self.sub_sections = []
        parent.sub_sections.append(self)
        self.root_items = []
        self.all_items = []


class TodoItem:
    def __init__(
            self,
            status: 'TodoStatus',
            name: str,
            depth: int,
            parent_section: TodoSection,
            parent_item: Optional['TodoItem']
    ):
        self.status = status
        self.name = name
        self.depth = depth
        self.parent_section = parent_section
        parent_section.all_items.append(self)
        self.parent_item = parent_item
        self.sub_items = []
        if parent_item:
            parent_item.sub_items.append(self)
        else:
            parent_section.root_items.append(self)


class TodoStatus(Enum):
    COMPLETE = "DONE"
    IN_PROGRESS = "INP"
    TODO = ""
