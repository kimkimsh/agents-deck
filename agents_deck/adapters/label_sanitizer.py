from typing import Any, Optional

from agents_deck.constants.label_constants import LabelConstants


class LabelSanitizer:
    """Reduces names read from agent state to a short single display line."""

    def title(self, text: Any) -> Optional[str]:
        return self._clip(text, LabelConstants.MAX_TITLE_CHARS)

    def processName(self, comm: str) -> Optional[str]:
        """The kernel's executable name, kept only when it is file-name characters."""
        if not LabelConstants.PROCESS_NAME_PATTERN.fullmatch(comm):
            return None
        return comm

    @staticmethod
    def _clip(text: Any, limit: int) -> Optional[str]:
        if not isinstance(text, str):
            return None
        tFlat = " ".join(text.split())
        if not tFlat:
            return None
        if len(tFlat) <= limit:
            return tFlat
        return tFlat[: limit - len(LabelConstants.ELLIPSIS)] + LabelConstants.ELLIPSIS
