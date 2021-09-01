from enum import Enum
from typing import List, Optional, Dict


# noinspection PyMethodMayBeStatic
class TodoList:
    def __init__(self, path: str):
        self.path = path
        self.root_section = TodoSection("root", 0, None)

    def parse(self) -> None:
        with open(self.path, "r") as f:
            contents = f.readlines()
        current_section = self.root_section
        current_item = None
        for line in contents:
            if line.strip() == "":
                continue
            if line.startswith("#"):
                current_section = self.parse_section(line, current_section)
                current_item = None
            else:
                current_item = self.parse_item(line, current_section, current_item)

    def parse_section(self, line: str, current_section: 'TodoSection') -> 'TodoSection':
        section_title = line.lstrip("#")
        section_depth = len(line) - len(section_title)
        section_title = section_title.strip()
        if section_depth > current_section.depth:
            parent_section = current_section
        else:
            while section_depth <= current_section.depth:
                current_section = current_section.parent
            parent_section = current_section
        return TodoSection(section_title, section_depth, parent_section)
   
    def parse_item(self, line: str, current_section: 'TodoSection', current_item: Optional['TodoItem']) -> 'TodoItem':
        status = TodoStatus.TODO
        for enum_status in TodoStatus:
            if line.startswith(enum_status.value):
                status = enum_status
                line = line[len(enum_status.value):]
                break
        item_text = line.lstrip(" -")
        item_depth = len(line) - len(item_text)
        item_text = item_text.strip()
        if current_item is None:
            parent_item = None
        elif item_depth > current_item.depth:
            parent_item = current_item
        else:
            parent_item = current_item
            while item_depth <= parent_item.depth:
                if parent_item.parent_item is not None:
                    parent_item = parent_item.parent_item
                else:
                    parent_item = None
                    break
        return TodoItem(status, item_text, item_depth, current_section, parent_item)

    def to_text(self) -> str:
        return self.root_section.to_text()

    def save(self) -> None:
        with open(self.path, "w") as f:
            f.write(self.to_text())

    def to_json(self) -> Dict:
        return {
            "path": self.path
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'TodoList':
        todo = TodoList(data["path"])
        todo.parse()
        return todo


class TodoSection:
    def __init__(self, title: str, depth: int, parent: Optional['TodoSection']):
        self.title: str = title
        self.depth: int = depth
        self.parent: Optional['TodoSection'] = parent
        self.sub_sections: List['TodoSection'] = []
        if parent:
            parent.sub_sections.append(self)
        self.root_items: List['TodoItem'] = []
        self.all_items: List['TodoItem'] = []

    def to_text(self) -> str:
        lines = []
        if self.depth != 0:
            lines += ["#" * self.depth + " " + self.title]
        lines += [item.to_text() for item in self.root_items]
        lines += ["\n" + section.to_text() for section in self.sub_sections]
        return "\n".join(lines)


class TodoItem:
    def __init__(
            self,
            status: 'TodoStatus',
            name: str,
            depth: int,
            parent_section: TodoSection,
            parent_item: Optional['TodoItem']
    ):
        self.status: 'TodoStatus' = status
        self.name: str = name
        self.depth: int = depth
        self.parent_section: TodoSection = parent_section
        parent_section.all_items.append(self)
        self.parent_item: Optional['TodoItem'] = parent_item
        self.sub_items: List['TodoItem'] = []
        if parent_item:
            parent_item.sub_items.append(self)
        else:
            parent_section.root_items.append(self)

    def to_text(self) -> str:
        lines = [self.status.value + ("- " * self.depth)[:self.depth] + self.name]
        lines += [item.to_text() for item in self.sub_items]
        return "\n".join(lines)


class TodoStatus(Enum):
    COMPLETE = "DONE"
    IN_PROGRESS = "INP"
    TODO = ""
