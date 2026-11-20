from dataclasses import dataclass
from typing import Optional, Tuple

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.settings.shelf_mode import ShelfMode
from agents_deck.settings.theme_choice import ThemeChoice


@dataclass(frozen=True)
class Settings:
    """User choices persisted between runs. Changed only on the UI thread."""

    mColumns: int
    mRows: int
    mScale: int
    mShelfMode: ShelfMode
    mShowNames: bool
    mTheme: ThemeChoice
    mOrder: Tuple[str, ...]
    mPosition: Optional[Tuple[int, int]]
    mFirstRunDone: bool

    @staticmethod
    def defaults() -> "Settings":
        return Settings(
            mColumns=LayoutConstants.DEFAULT_COLUMNS,
            mRows=LayoutConstants.DEFAULT_ROWS,
            mScale=LayoutConstants.DEFAULT_SCALE,
            mShelfMode=ShelfMode.HOVER,
            mShowNames=False,
            mTheme=ThemeChoice.SYSTEM,
            mOrder=(),
            mPosition=None,
            mFirstRunDone=False,
        )
