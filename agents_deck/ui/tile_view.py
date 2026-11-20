from dataclasses import dataclass
from typing import Optional

from agents_deck.ui.sprite_frame import SpriteFrame


@dataclass(frozen=True)
class TileView:
    """One tile as it is drawn this frame, in window pixels."""

    mX: float
    mY: float
    mFrame: SpriteFrame
    mOpacity: float
    mBadgeCount: Optional[int]
    mName: Optional[str]
