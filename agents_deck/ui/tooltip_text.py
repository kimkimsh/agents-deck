from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TooltipText:
    mTitle: str
    mLines: Tuple[str, ...]
