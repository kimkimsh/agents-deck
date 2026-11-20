import json
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.constants.warp_constants import WarpConstants
from agents_deck.settings.settings import Settings
from agents_deck.settings.shelf_mode import ShelfMode
from agents_deck.settings.theme_choice import ThemeChoice


class SettingsStore:
    """Reads and writes settings.json.

    Writes go to a new, exclusively created temporary file in the same
    directory and are renamed over the old file, so a crash never leaves a
    half-written file and nothing else can hold the temporary file open. The
    file and its directory are private to the user: the order list holds
    pane ids.
    Every field is validated on load; a bad field falls back to its default
    without discarding the others. UI thread only.
    """

    DIR_MODE = 0o700
    TEMP_SUFFIX = ".tmp"
    POSITION_FIELDS = 2

    mPath: str

    def __init__(self, path: str):
        self.mPath = path

    def load(self) -> Tuple[Settings, Optional[str]]:
        """The settings, plus a note for the user when the file was unusable."""
        tDefaults = Settings.defaults()
        try:
            with open(self.mPath, "r", encoding="utf-8") as tFile:
                tRaw = json.load(tFile)
        except FileNotFoundError:
            return tDefaults, None
        except (OSError, ValueError):
            return tDefaults, "Settings file could not be read; using defaults."
        if not isinstance(tRaw, dict):
            return tDefaults, "Settings file could not be read; using defaults."
        return self._parse(tRaw, tDefaults), None

    def save(self, settings: Settings):
        tDirectory = os.path.dirname(self.mPath)
        os.makedirs(tDirectory, mode=self.DIR_MODE, exist_ok=True)
        # mkstemp creates the file O_EXCL with mode 0600.
        tDescriptor, tTemp = tempfile.mkstemp(dir=tDirectory, prefix=os.path.basename(self.mPath), suffix=self.TEMP_SUFFIX)
        try:
            with os.fdopen(tDescriptor, "w", encoding="utf-8") as tFile:
                json.dump(self._serialize(settings), tFile, indent=2)
                tFile.flush()
                os.fsync(tFile.fileno())
            os.replace(tTemp, self.mPath)
        except BaseException:
            os.unlink(tTemp)
            raise

    def _parse(self, raw: Dict[str, Any], defaults: Settings) -> Settings:
        return Settings(
            mColumns=self._clampedInt(raw.get("columns"), LayoutConstants.MIN_GRID, LayoutConstants.MAX_GRID, defaults.mColumns),
            mRows=self._clampedInt(raw.get("rows"), LayoutConstants.MIN_GRID, LayoutConstants.MAX_GRID, defaults.mRows),
            mScale=self._clampedInt(raw.get("scale"), LayoutConstants.MIN_SCALE, LayoutConstants.MAX_SCALE, defaults.mScale),
            mShelfMode=self._enum(ShelfMode, raw.get("shelf"), defaults.mShelfMode),
            mShowNames=raw["showNames"] if isinstance(raw.get("showNames"), bool) else defaults.mShowNames,
            mTheme=self._enum(ThemeChoice, raw.get("theme"), defaults.mTheme),
            mOrder=self._order(raw.get("order")),
            mPosition=self._position(raw.get("position")),
            mFirstRunDone=raw["firstRunDone"] if isinstance(raw.get("firstRunDone"), bool) else defaults.mFirstRunDone,
        )

    @staticmethod
    def _serialize(settings: Settings) -> Dict[str, Any]:
        return {
            "columns": settings.mColumns,
            "rows": settings.mRows,
            "scale": settings.mScale,
            "shelf": settings.mShelfMode.value,
            "showNames": settings.mShowNames,
            "theme": settings.mTheme.value,
            "order": list(settings.mOrder),
            "position": None if settings.mPosition is None else list(settings.mPosition),
            "firstRunDone": settings.mFirstRunDone,
        }

    @staticmethod
    def _clampedInt(value: Any, low: int, high: int, fallback: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return fallback
        return min(max(value, low), high)

    @staticmethod
    def _enum(kind, value: Any, fallback):
        try:
            return kind(value)
        except ValueError:
            return fallback

    def _order(self, value: Any) -> Tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        tPanes = [tPane for tPane in value if isinstance(tPane, str) and WarpConstants.PANE_UUID_PATTERN.fullmatch(tPane)]
        return tuple(dict.fromkeys(tPanes))[: LayoutConstants.ORDER_CAP]

    def _position(self, value: Any) -> Optional[Tuple[int, int]]:
        if not isinstance(value, list) or len(value) != self.POSITION_FIELDS:
            return None
        if not all(self._isCoordinate(tPart) for tPart in value):
            return None
        return (value[0], value[1])

    @staticmethod
    def _isCoordinate(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return LayoutConstants.MIN_SCREEN_COORDINATE <= value <= LayoutConstants.MAX_SCREEN_COORDINATE
