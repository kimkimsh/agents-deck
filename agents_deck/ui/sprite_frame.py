from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SpriteFrame:
    """What one tile shows at one instant."""

    mSpecies: str
    mFrame: str
    mOverlays: Tuple[str, ...]
    mOpacity: float
