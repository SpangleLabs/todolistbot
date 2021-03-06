from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Tuple

from prometheus_client import Counter

list_parsed = Counter("todolistbot_parse_list_total", "Number of todo lists parsed")
sections_parsed = Counter("todolistbot_parse_section_total", "Number of todo list sections parsed")
items_parsed = Counter("todolistbot_parse_items_total", "Number of todo list items parsed")


def line_is_section(line: str) -> bool:
    return line.startswith("#")


def line_is_empty(line: str) -> bool:
    return line.strip() == ""


def line_is_item(line: str) -> bool:
    return not line_is_empty(line) and not line_is_section(line)


# noinspection PyMethodMayBeStatic
class TodoList:
    def __init__(self, path: str):
        self.path = path
        self.root_section = TodoSection("root", 0, None)

    def parse(self) -> None:
        list_parsed.inc()
        with open(self.path, "r") as f:
            contents = f.readlines()
        self.parse_lines(contents)

    def parse_lines(self, contents: List[str], current_section: Optional['TodoSection'] = None):
        current_section = current_section or self.root_section
        current_item = None
        for line in contents:
            if line_is_empty(line):
                continue
            if line_is_section(line):
                current_section = self.parse_section(line, current_section)
                current_item = None
            else:
                current_item = self.parse_item(line, current_section, current_item)

    def parse_section(self, line: str, current_section: 'TodoSection') -> 'TodoSection':
        sections_parsed.inc()
        section_title = line.lstrip("#")
        section_depth = len(line) - len(section_title)
        section_title = section_title.strip()
        if section_depth > current_section.depth:
            parent_section = current_section
        else:
            while section_depth <= current_section.depth:
                current_section = current_section.parent_section
            parent_section = current_section
        return TodoSection(section_title, section_depth, parent_section)
   
    def parse_item(self, line: str, current_section: 'TodoSection', current_item: Optional['TodoItem']) -> 'TodoItem':
        items_parsed.inc()
        status, line = self.parse_status(line)
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

    def parse_status(self, line: str) -> Tuple['TodoStatus', str]:
        status = TodoStatus.TODO
        for enum_status in TodoStatus:
            if line.startswith(enum_status.value):
                status = enum_status
                line = line[len(enum_status.value):]
                break
        return status, line

    def to_text(self, section: Optional['TodoSection'] = None) -> str:
        section = section or self.root_section
        max_length = 4096
        text = section.to_text()
        if len(text) < max_length:
            return text
        max_depth = 10
        while len(section.to_text(max_depth)) > max_length and max_depth >= 1:
            max_depth -= 1
        return section.to_text(max_depth)

    def save(self) -> None:
        with open(self.path, "w") as f:
            f.write(self.root_section.to_text())

    def to_json(self) -> Dict:
        return {
            "path": self.path
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'TodoList':
        todo = TodoList(data["path"])
        todo.parse()
        return todo


class TodoContainer(ABC):

    def __init__(self, parent_section: Optional['TodoSection']):
        self.parent_section: Optional[TodoSection] = parent_section

    @property
    @abstractmethod
    def parent(self) -> Optional['TodoContainer']:
        raise NotImplementedError

    @abstractmethod
    def remove(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_empty(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def to_text(self, max_depth: Optional[int] = None) -> str:
        raise NotImplementedError


class TodoSection(TodoContainer):

    def __init__(self, title: str, depth: int, parent: Optional['TodoSection']):
        super().__init__(parent)
        self.title: str = title
        self.depth: int = depth
        self.sub_sections: List['TodoSection'] = []
        if parent:
            parent.sub_sections.append(self)
        self.root_items: List['TodoItem'] = []

    @property
    def parent(self) -> Optional['TodoSection']:
        return self.parent_section

    def is_empty(self) -> bool:
        return not self.sub_sections and not self.root_items

    def remove(self) -> None:
        if self.parent_section:
            self.parent_section.sub_sections.remove(self)

    def to_text(self, max_depth: Optional[int] = None) -> str:
        lines = []
        if self.depth != 0:
            lines += ["#" * self.depth + " " + self.title]
        if max_depth is None:
            lines += [item.to_text(max_depth) for item in self.root_items]
        if max_depth is None or self.depth < max_depth:
            lines += [("\n" if max_depth is None else "") + section.to_text(max_depth) for section in self.sub_sections]
        return "\n".join(lines)


class TodoItem(TodoContainer):

    def __init__(
            self,
            status: 'TodoStatus',
            name: str,
            depth: int,
            parent_section: TodoSection,
            parent_item: Optional['TodoItem']
    ):
        super().__init__(parent_section)
        self.status: 'TodoStatus' = status
        self.name: str = name
        self.depth: int = depth
        self.parent_item: Optional['TodoItem'] = parent_item
        self.sub_items: List['TodoItem'] = []
        if parent_item:
            parent_item.sub_items.append(self)
        else:
            parent_section.root_items.append(self)

    @property
    def parent(self) -> TodoContainer:
        if self.parent_item:
            return self.parent_item
        return self.parent_section

    def is_empty(self) -> bool:
        return not self.sub_items

    def remove(self) -> None:
        if self.parent_item:
            self.parent_item.sub_items.remove(self)
        else:
            self.parent_section.root_items.remove(self)

    def to_text(self, max_depth: Optional[int] = None) -> str:
        lines = [self.status.value + ("- " * self.depth)[:self.depth] + self.name]
        if not max_depth or (self.parent_item.depth + self.depth) < max_depth:
            lines += [item.to_text(max_depth) for item in self.sub_items]
        return "\n".join(lines)


class TodoStatus(Enum):
    COMPLETE = "DONE"
    IN_PROGRESS = "INP"
    TODO = ""
