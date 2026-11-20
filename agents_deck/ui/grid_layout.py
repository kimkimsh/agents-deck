import math
from typing import List, Optional

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.ui.rect import Rect


class GridLayout:
    """Geometry of the deck for one configuration, in window pixels. Pure.

    Tiles fill the configured columns row by row; more sessions than cells
    add rows rather than shrinking tiles. A fixed column on the right holds
    the gear (top) and the resize grip (bottom), so they stay reachable even
    with zero sessions.
    """

    mColumns: int
    mRows: int
    mScale: int
    mTileCount: int
    mNameRow: int

    def __init__(self, columns: int, rows: int, scale: int, tileCount: int, showNames: bool):
        self.mColumns = columns
        self.mRows = max(rows, math.ceil(tileCount / columns)) if tileCount else rows
        self.mScale = scale
        self.mTileCount = tileCount
        self.mNameRow = LayoutConstants.NAME_ROW_PX if showNames else 0

    def tileSize(self) -> int:
        return LayoutConstants.TILE * self.mScale

    def tileRect(self, index: int) -> Rect:
        tColumn = index % self.mColumns
        tRow = index // self.mColumns
        tPadding = LayoutConstants.PLATE_PADDING * self.mScale
        tStep = (LayoutConstants.TILE + LayoutConstants.GAP) * self.mScale
        return Rect(tPadding + tColumn * tStep, tPadding + tRow * (tStep + self.mNameRow), self.tileSize(), self.tileSize())

    def tileRects(self) -> List[Rect]:
        return [self.tileRect(tIndex) for tIndex in range(self.mTileCount)]

    def gridWidth(self) -> int:
        return (self.mColumns * LayoutConstants.TILE + (self.mColumns - 1) * LayoutConstants.GAP) * self.mScale

    def width(self) -> int:
        return (2 * LayoutConstants.PLATE_PADDING + LayoutConstants.SIDE_GAP + LayoutConstants.GEAR) * self.mScale + self.gridWidth()

    def height(self) -> int:
        tGrid = self.mRows * (self.tileSize() + self.mNameRow) + (self.mRows - 1) * LayoutConstants.GAP * self.mScale
        return 2 * LayoutConstants.PLATE_PADDING * self.mScale + tGrid

    def plateRect(self) -> Rect:
        return Rect(0, 0, self.width(), self.height())

    def gearRect(self) -> Rect:
        tSize = LayoutConstants.GEAR * self.mScale
        return Rect(self.width() - LayoutConstants.PLATE_PADDING * self.mScale - tSize, LayoutConstants.PLATE_PADDING * self.mScale, tSize, tSize)

    def gripRect(self) -> Rect:
        tSize = LayoutConstants.GRIP * self.mScale
        tInset = LayoutConstants.PLATE_PADDING * self.mScale
        return Rect(self.width() - tInset - tSize, self.height() - tInset - tSize, tSize, tSize)

    def tileAt(self, x: float, y: float) -> Optional[int]:
        for tIndex in range(self.mTileCount):
            if self.tileRect(tIndex).contains(x, y):
                return tIndex
        return None

    def slotNearest(self, x: float, y: float) -> int:
        """The tile slot a dragged tile would drop into; always a valid index."""
        tBest = 0
        tBestDistance = None
        for tIndex in range(self.mTileCount):
            tRect = self.tileRect(tIndex)
            tDistance = (tRect.centerX() - x) ** 2 + (tRect.centerY() - y) ** 2
            if tBestDistance is None or tDistance < tBestDistance:
                tBest = tIndex
                tBestDistance = tDistance
        return tBest
