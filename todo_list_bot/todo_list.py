class TodoList:
    def __init__(self, path: str):
        self.path = path
        self.sections = []
        self.items = []

    def parse(self) -> None:
        with open(self.path, "r") as f:
            contents = f.read()
        current_section = TodoSection("root", 0)
        all_sections = []
        for line in contents:
            if line.strip() == "":
                continue
            if line.startswith("#"):
                section_title = line.lstrip("#")
                section_depth = len(line) - len(section_title)
                section_title = section_title.strip()
                new_section = TodoSection(section_title, section_depth)
                all_sections.append(new_section)
                current_section = new_section
            if line.strip().startswith("-"):
                item
                # TODO: parse item
            if line.startswith(TodoStatus.TEXT):
        # TODO: parse item with status
        # After all, set up sections tree
        current_section = None
        for section in all_sections:

    def list_sections(self) -> List[TodoSection]:
        # TODO
        pass

    def list_items(self) -> List[TodoItem]:
        # Todo
        pass

    def to_text(self) -> str:
        pass


class TodoSection:
    def __init__(self, title: str, depth: int):
        self.title = str
        self.depth = int
        self.sub_sections = []
        self.items = []
        self.parent = None


class TodoItem:
    def __init__(self):
        self.status = TodoStatus
        self.name = str
        self.sub_items = List[TodoItem]


class TodoStatus(Enum):
    COMPLETE = "DONE"
    IN_PROGRESS = "INP"
    TODO = ""
