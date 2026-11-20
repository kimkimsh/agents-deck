from dataclasses import dataclass
from typing import Optional

from agents_deck.model.background_kind import BackgroundKind


@dataclass(frozen=True)
class BackgroundTask:
    """One unit of work running outside the session's foreground turn.

    Carries no text an agent or a user wrote. mProcessName is the kernel's
    short executable name for a PROCESS task, reduced to file-name
    characters, and None for every other kind.
    """

    mId: str
    mKind: BackgroundKind
    mProcessName: Optional[str]
