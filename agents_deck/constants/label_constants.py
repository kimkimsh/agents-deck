import re


class LabelConstants:
    """Limits on the short text the overlay is allowed to show."""

    MAX_TITLE_CHARS = 24
    ELLIPSIS = "…"

    # /proc comm is at most 15 bytes; anything outside file-name characters
    # (spaces, slashes, quotes) is not shown.
    PROCESS_NAME_PATTERN = re.compile(r"[A-Za-z0-9._+-]{1,15}")
