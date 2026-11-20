import math
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from agents_deck.constants.sprite_constants import SpriteConstants

Grid = List[List[str]]
Point = Tuple[int, int]


class SpriteArt:
    """The pixel art: three characters, their poses, and the overlays.

    Every frame is SpriteConstants.CANVAS square, one palette key per pixel
    ("." is transparent). Bodies are centred on x = 11.5 so a mirrored part
    lands on x and 23 - x. Bubbles and status marks use the top-right band
    (x 12-21, y 0-7), the background-count badge the top-left (x 0-7, y 0-6),
    and props sit front-right (x 16-22, y 15-21) where the working arm
    reaches them.

    Pure data built once; the atlas turns it into pixels per theme.
    """

    mFrames: Dict[str, Dict[str, Tuple[str, ...]]]

    EMBER = "claude"
    CUBIT = "codex"
    FLOATY = "agy"

    # Row widths of Ember's body from its top row down.
    EMBER_ROWS = (6, 10, 12, 14, 14, 14, 14, 12, 10, 6)
    EMBER_TOP = 11

    CUBIT_LEFT = 5
    CUBIT_RIGHT = 18
    CUBIT_TOP = 10
    CUBIT_BOTTOM = 20
    CUBIT_CORNER = 3

    FLOATY_CENTER_Y = 14.0
    FLOATY_RADIUS = 6.2
    FLOATY_RING_Y = 16

    # Upper-left share of the body that stays base colour; the rest of the
    # lower-right crescent is shaded.
    SHADE_THRESHOLD = 0.62

    FRAMES = ("idle", "blink", "think0", "think1", "work0", "work1", "raise0", "raise1", "error0", "error1", "sleep0", "sleep1")

    OVERLAYS: Dict[str, Tuple[int, int, Tuple[str, ...]]] = {
        "think1": (12, 0, ("..oooooo..", ".oBBBBBBo.", "oBBeBBBBBo", ".oBBBBBBo.", "..oooooo..", "...oo.....", "..o.......")),
        "think2": (12, 0, ("..oooooo..", ".oBBBBBBo.", "oBBeBeBBBo", ".oBBBBBBo.", "..oooooo..", "...oo.....", "..o.......")),
        "think3": (12, 0, ("..oooooo..", ".oBBBBBBo.", "oBBeBeBeBo", ".oBBBBBBo.", "..oooooo..", "...oo.....", "..o.......")),
        # A fill row above and below each glyph: a glyph touching the outline
        # merges with it and reads as its own negative.
        "bang": (15, 0, (".ooooo.", "oyyyyyo", "oyyeyyo", "oyyeyyo", "oyyeyyo", "oyyyyyo", "oyyeyyo", "oyyyyyo", ".ooooo.")),
        "ask": (15, 0, (".ooooo.", "oyyyyyo", "oyeeeyo", "oyyyeyo", "oyyeeyo", "oyyeyyo", "oyyyyyo", "oyyeyyo", "oyyyyyo", ".ooooo.")),
        "zzz0": (15, 1, ("......", "......", "......", "eee...", ".e....", "eee...")),
        "zzz1": (15, 1, ("...eee", "....e.", "...eee", "eee...", ".e....", "eee...")),
        "smoke0": (9, 4, (".ggg..", "gGGGg.", "gGGGGg", ".gggg.")),
        "smoke1": (9, 3, ("..ggg.", ".gGGGg", "gGGGGg", ".gggg.")),
        "prop.shell0": (16, 16, ("ooooooo", "ozzzzzo", "onzzzzo", "oznzzzo", "onzwwzo", "ooooooo")),
        "prop.shell1": (16, 16, ("ooooooo", "ozzzzzo", "onzzzzo", "oznzzzo", "onzzzzo", "ooooooo")),
        "prop.edit": (17, 15, ("....oo", "...oGo", "..ouo.", ".ouo..", "oeo...", "oo....")),
        "prop.search": (17, 16, (".ooo..", "ocwco.", "occco.", ".ooou.", "....uu")),
        "prop.web": (17, 16, (".ooo.", "ocGco", "oGGGo", "ocGco", ".ooo.")),
        "prop.agent": (17, 15, ("..a..", "..o..", "ooooo", "ocoGo", "ooooo", ".o.o.")),
        "prop.other": (17, 15, ("oo.oo.", "oGoGo.", "oGGGo.", ".oGGGo", "..oGGo", "...ooo")),
    }

    GEAR = (
        "....oooo....",
        "..o.oGGo.o..",
        ".oGooGGooGo.",
        "..oGGGGGGo..",
        "ooGGGooGGGoo",
        "oGGGo..oGGGo",
        "oGGGo..oGGGo",
        "ooGGGooGGGoo",
        "..oGGGGGGo..",
        ".oGooGGooGo.",
        "..o.oGGo.o..",
        "....oooo....",
    )

    GRIP = (
        "........",
        "......i.",
        "........",
        "....i.i.",
        "........",
        "..i.i.i.",
        "........",
        "i.i.i.i.",
    )

    DIGITS: Dict[str, Tuple[str, ...]] = {
        "0": ("iii", "i.i", "i.i", "i.i", "iii"),
        "1": (".i.", "ii.", ".i.", ".i.", "iii"),
        "2": ("iii", "..i", "iii", "i..", "iii"),
        "3": ("iii", "..i", ".ii", "..i", "iii"),
        "4": ("i.i", "i.i", "iii", "..i", "..i"),
        "5": ("iii", "i..", "iii", "..i", "iii"),
        "6": ("iii", "i..", "iii", "i.i", "iii"),
        "7": ("iii", "..i", ".i.", ".i.", ".i."),
        "8": ("iii", "i.i", "iii", "i.i", "iii"),
        "9": ("iii", "i.i", "iii", "..i", "iii"),
        "+": ("...", ".i.", "iii", ".i.", "..."),
    }

    def __init__(self):
        self.mFrames = self._buildFrames()

    def badge(self, count: int) -> Tuple[str, ...]:
        """A rounded cream pill holding the count, "9+" above the cap."""
        tText = str(count) if count <= SpriteConstants.BADGE_MAX_COUNT else str(SpriteConstants.BADGE_MAX_COUNT) + SpriteConstants.BADGE_OVERFLOW
        tStep = SpriteConstants.BADGE_DIGIT_WIDTH + SpriteConstants.BADGE_DIGIT_GAP
        tLeft = SpriteConstants.BADGE_OUTLINE + SpriteConstants.BADGE_PAD_X
        tTop = SpriteConstants.BADGE_OUTLINE + SpriteConstants.BADGE_PAD_Y
        tWidth = 2 * tLeft + len(tText) * tStep - SpriteConstants.BADGE_DIGIT_GAP
        tHeight = 2 * tTop + SpriteConstants.BADGE_DIGIT_HEIGHT
        tInside = [[self._badgeInset(tY, tHeight) <= tX < tWidth - self._badgeInset(tY, tHeight) for tX in range(tWidth)] for tY in range(tHeight)]
        tGrid = [[SpriteConstants.TRANSPARENT] * tWidth for _ in range(tHeight)]
        for tY in range(tHeight):
            for tX in range(tWidth):
                if tInside[tY][tX]:
                    tGrid[tY][tX] = "o" if self._onBadgeEdge(tInside, tX, tY) else "w"
        for tIndex, tChar in enumerate(tText):
            for tDy, tRow in enumerate(self.DIGITS[tChar]):
                for tDx, tKey in enumerate(tRow):
                    if tKey != SpriteConstants.TRANSPARENT:
                        tGrid[tTop + tDy][tLeft + tIndex * tStep + tDx] = "e"
        return self._rows(tGrid)

    @staticmethod
    def _badgeInset(row: int, height: int) -> int:
        tFromEdge = min(row, height - 1 - row)
        return SpriteConstants.BADGE_CORNER_INSETS[tFromEdge] if tFromEdge < len(SpriteConstants.BADGE_CORNER_INSETS) else 0

    @staticmethod
    def _onBadgeEdge(inside: List[List[bool]], x: int, y: int) -> bool:
        for tDx, tDy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tX, tY = x + tDx, y + tDy
            if not (0 <= tY < len(inside) and 0 <= tX < len(inside[0])) or not inside[tY][tX]:
                return True
        return False

    def composite(self, species: str, frame: str, overlays: Sequence[str]) -> Tuple[str, ...]:
        tGrid = [list(tRow) for tRow in self.mFrames[species][frame]]
        for tName in overlays:
            tLeft, tTop, tRows = self.OVERLAYS[tName]
            self._stamp(tGrid, tRows, tLeft, tTop)
        return self._rows(tGrid)

    def frames(self) -> Dict[str, Dict[str, Tuple[str, ...]]]:
        """species -> frame name -> rows."""
        return self.mFrames

    def _buildFrames(self) -> Dict[str, Dict[str, Tuple[str, ...]]]:
        return {
            self.EMBER: {tName: self._rows(self._ember(tName)) for tName in self.FRAMES},
            self.CUBIT: {tName: self._rows(self._cubit(tName)) for tName in self.FRAMES},
            self.FLOATY: {tName: self._rows(self._floaty(tName)) for tName in self.FRAMES},
        }

    # Ember: Claude Code's flame sprite.

    def _ember(self, frame: str) -> Grid:
        tGrid = self._blank()
        tBody: Set[Point] = set()
        for tRow, tWidth in enumerate(self.EMBER_ROWS):
            tLeft = SpriteConstants.CENTER_LEFT + 1 - tWidth // 2
            for tX in range(tLeft, tLeft + tWidth):
                tBody.add((tX, self.EMBER_TOP + tRow))
        self._shade(tGrid, tBody, ((8, 13), (9, 13), (8, 14)))
        tTop = self.EMBER_TOP - 4
        self._stamp(tGrid, self._emberTuft(frame), 9, tTop)
        for tX in (8, 9, 14, 15):
            self._put(tGrid, tX, 21, "o")
        self._face(tGrid, frame, (9, 14), 14, 16)
        self._arms(tGrid, tBody, frame, 16)
        return tGrid

    @staticmethod
    def _emberTuft(frame: str) -> Sequence[str]:
        if frame.startswith("sleep"):
            return ("......", "......", "..oo..", ".ofFo.")
        if frame.endswith("1"):
            return ("..o...", ".ofo..", ".oFfo.", "ofFFo.")
        return ("...o..", "..ofo.", ".ofFo.", ".oFFfo")

    # Cubit: Codex's robot.

    def _cubit(self, frame: str) -> Grid:
        tGrid = self._blank()
        tBody = self._roundedRect(self.CUBIT_LEFT, self.CUBIT_TOP, self.CUBIT_RIGHT, self.CUBIT_BOTTOM, self.CUBIT_CORNER)
        self._shade(tGrid, tBody, ((7, 11), (8, 11), (7, 12)))
        tSleeping = frame.startswith("sleep")
        tWobble = 1 if frame.endswith("1") and not tSleeping else 0
        for tX in (11, 12):
            self._put(tGrid, tX, self.CUBIT_TOP - 1, "o")
            self._put(tGrid, tX + tWobble, self.CUBIT_TOP - 2, "o" if tSleeping else "q")
        for tY in (13, 14, 15):
            for tX in range(7, 17):
                self._put(tGrid, tX, tY, "v")
        self._visorEyes(tGrid, frame)
        for tX in (8, 15):
            self._put(tGrid, tX, 21, "o")
            self._put(tGrid, tX, 22, "o")
        self._arms(tGrid, tBody, frame, 16)
        return tGrid

    def _visorEyes(self, grid: Grid, frame: str):
        if frame.startswith("error"):
            for tX, tY in ((8, 13), (9, 14), (8, 15), (15, 13), (14, 14), (15, 15)):
                self._put(grid, tX, tY, "r")
            return
        if frame.startswith("sleep"):
            tRows, tShift, tKey = (15,), 0, "Q"
        elif frame == "blink":
            tRows, tShift, tKey = (14,), 0, "q"
        elif frame.startswith("think"):
            tRows, tShift, tKey = (13,), 1, "q"
        else:
            tRows, tShift, tKey = (13, 14), 0, "q"
        for tY in tRows:
            for tX in (8, 9, 14, 15):
                self._put(grid, tX + tShift, tY, tKey)

    # Floaty: Antigravity's ringed orb.

    def _floaty(self, frame: str) -> Grid:
        tGrid = self._blank()
        tBob = 1 if frame.endswith("1") and not frame.startswith("sleep") else 0
        tCenterY = self.FLOATY_CENTER_Y - tBob
        tBody = {
            (tX, tY)
            for tX in range(SpriteConstants.CANVAS)
            for tY in range(SpriteConstants.CANVAS)
            if math.hypot(tX + 0.5 - SpriteConstants.CENTER_X, tY + 0.5 - tCenterY) <= self.FLOATY_RADIUS
        }
        self._shade(tGrid, tBody, ((8, 10 - tBob), (9, 10 - tBob), (8, 11 - tBob)))
        tRingY = self.FLOATY_RING_Y - tBob
        for tX in range(4, 20):
            self._put(tGrid, tX, tRingY, "k")
        for tX in (3, 20):
            self._put(tGrid, tX, tRingY, "o")
        for tX in (4, 5, 18, 19):
            self._put(tGrid, tX, tRingY - 1, "o")
            self._put(tGrid, tX, tRingY + 1, "o")
        tHalf = 4 - tBob
        for tX in range(12 - tHalf, 12 + tHalf):
            self._put(tGrid, tX, 22, "d")
        for tX in range(13 - tHalf, 11 + tHalf):
            self._put(tGrid, tX, 23, "d")
        self._face(tGrid, frame, (9, 14), 12 - tBob, 14 - tBob)
        self._arms(tGrid, tBody, frame, tRingY + 1)
        return tGrid

    # Shared parts.

    def _face(self, grid: Grid, frame: str, eyeColumns: Tuple[int, int], eyeTop: int, cheekRow: int):
        tLeft, tRight = eyeColumns
        if frame.startswith("error"):
            for tX, tY in ((tLeft - 1, 0), (tLeft, 1), (tLeft - 1, 2), (tRight + 1, 0), (tRight, 1), (tRight + 1, 2)):
                self._put(grid, tX, eyeTop + tY, "e")
            return
        if frame == "blink":
            for tX in (tLeft - 1, tLeft, tRight, tRight + 1):
                self._put(grid, tX, eyeTop + 1, "e")
        elif frame.startswith("sleep"):
            for tX, tY in ((tLeft - 1, 0), (tLeft, 1), (tLeft + 1, 0), (tRight - 1, 0), (tRight, 1), (tRight + 1, 0)):
                self._put(grid, tX, eyeTop + tY, "e")
        elif frame.startswith("think"):
            for tX in (tLeft + 1, tRight + 1):
                self._put(grid, tX, eyeTop - 1, "e")
                self._put(grid, tX, eyeTop, "e")
        else:
            for tX in (tLeft, tRight):
                self._put(grid, tX, eyeTop, "e")
                self._put(grid, tX, eyeTop + 1, "e")
        self._put(grid, tLeft - 2, cheekRow, "p")
        self._put(grid, tRight + 2, cheekRow, "p")

    def _arms(self, grid: Grid, body: Set[Point], frame: str, armRow: int):
        tLeft = min(tX for tX, tY in body if tY == armRow) - 1
        tRight = max(tX for tX, tY in body if tY == armRow) + 1
        tPoints: List[Point] = [(tLeft, armRow), (tLeft, armRow + 1)]
        if frame == "work0":
            tPoints += [(tRight, armRow), (tRight + 1, armRow)]
        elif frame == "work1":
            tPoints += [(tRight, armRow + 1), (tRight + 1, armRow + 1)]
        elif frame == "raise0":
            tPoints += [(tRight, armRow - 1), (tRight + 1, armRow - 2), (tRight + 1, armRow - 3)]
        elif frame == "raise1":
            tPoints += [(tRight, armRow - 1), (tRight + 1, armRow - 2), (tRight + 2, armRow - 3)]
        else:
            tPoints += [(tRight, armRow), (tRight, armRow + 1)]
        for tX, tY in tPoints:
            self._put(grid, tX, tY, "o")

    def _shade(self, grid: Grid, body: Set[Point], highlight: Iterable[Point]):
        tXs = [tX for tX, _ in body]
        tYs = [tY for _, tY in body]
        tCenterX = (min(tXs) + max(tXs) + 1) / 2.0
        tCenterY = (min(tYs) + max(tYs) + 1) / 2.0
        tRadiusX = (max(tXs) - min(tXs) + 1) / 2.0
        tRadiusY = (max(tYs) - min(tYs) + 1) / 2.0
        tHighlight = set(highlight)
        for tX, tY in body:
            if any((tX + tDx, tY + tDy) not in body for tDx, tDy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                tKey = "o"
            elif (tX, tY) in tHighlight:
                tKey = "h"
            elif (tX + 0.5 - tCenterX) / tRadiusX + (tY + 0.5 - tCenterY) / tRadiusY > self.SHADE_THRESHOLD:
                tKey = "s"
            else:
                tKey = "b"
            self._put(grid, tX, tY, tKey)

    @staticmethod
    def _roundedRect(left: int, top: int, right: int, bottom: int, corner: int) -> Set[Point]:
        tCells: Set[Point] = set()
        for tX in range(left, right + 1):
            for tY in range(top, bottom + 1):
                tDx = min(tX - left, right - tX)
                tDy = min(tY - top, bottom - tY)
                if tDx < corner and tDy < corner and math.hypot(corner - 0.5 - tDx, corner - 0.5 - tDy) > corner - 0.3:
                    continue
                tCells.add((tX, tY))
        return tCells

    @staticmethod
    def _blank() -> Grid:
        return [["."] * SpriteConstants.CANVAS for _ in range(SpriteConstants.CANVAS)]

    @staticmethod
    def _put(grid: Grid, x: int, y: int, key: str):
        if 0 <= x < SpriteConstants.CANVAS and 0 <= y < SpriteConstants.CANVAS:
            grid[y][x] = key

    def _stamp(self, grid: Grid, rows: Sequence[str], left: int, top: int):
        for tDy, tRow in enumerate(rows):
            for tDx, tKey in enumerate(tRow):
                if tKey != ".":
                    self._put(grid, left + tDx, top + tDy, tKey)

    @staticmethod
    def _rows(grid: Grid) -> Tuple[str, ...]:
        return tuple("".join(tRow) for tRow in grid)
