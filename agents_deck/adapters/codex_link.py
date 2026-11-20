from dataclasses import dataclass
from typing import Optional

from agents_deck.model.link_confidence import LinkConfidence


@dataclass(frozen=True)
class CodexLink:
    mThreadId: Optional[str]
    mConfidence: LinkConfidence
