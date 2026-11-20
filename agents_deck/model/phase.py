from enum import Enum


class Phase(str, Enum):
    """Foreground activity of one agent session.

    UNKNOWN means the session could not be observed; it is never a synonym
    for IDLE.
    """

    STARTING = "starting"
    IDLE = "idle"
    THINKING = "thinking"
    TOOL = "tool"
    WAITING = "waiting"
    ERROR = "error"
    UNKNOWN = "unknown"
