from enum import Enum


class ToolCategory(str, Enum):
    """Coarse tool family; selects the prop a character holds."""

    SHELL = "shell"
    EDIT = "edit"
    SEARCH = "search"
    WEB = "web"
    AGENT = "agent"
    OTHER = "other"
