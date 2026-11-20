from enum import Enum


class ShelfMode(str, Enum):
    """When the translucent plate behind the tiles is drawn."""

    HOVER = "hover"
    ALWAYS = "always"
