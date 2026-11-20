import re


class WarpConstants:
    """How Warp is addressed from outside."""

    SESSION_URI_FORMAT = "warp://session/%s"
    PANE_UUID_PATTERN = re.compile(r"[0-9a-f]{32}")
