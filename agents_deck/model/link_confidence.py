from enum import Enum


class LinkConfidence(str, Enum):
    """How certain the binding between a Warp pane and an agent's session record is."""

    EXACT = "exact"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
