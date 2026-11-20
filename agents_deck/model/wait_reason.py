from enum import Enum


class WaitReason(str, Enum):
    """What a WAITING session needs from the user."""

    PERMISSION = "permission"
    INPUT = "input"
