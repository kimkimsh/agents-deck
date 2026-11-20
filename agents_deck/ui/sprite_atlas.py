import sys
from typing import Dict, Sequence, Tuple

import cairo

from agents_deck.constants.sprite_constants import SpriteConstants
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_palette import Rgba, SpritePalette


class SpriteAtlas:
    """Cairo surfaces of sprites at one pixel per sprite pixel, cached.

    Characters and stickers (badges) float over the desktop and always get
    the palette's light rim; plate shapes sit on the themed plate and take
    the theme's ink instead. The floor shadow grows no rim: it is meant to
    fade into whatever is below.

    UI thread only.
    """

    RIMLESS_KEYS = (SpriteConstants.SHADOW_KEY,)
    NEIGHBOURS = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    NO_SPECIES = ""

    mArt: SpriteArt
    mPalette: SpritePalette
    mCache: Dict[Tuple, cairo.ImageSurface]

    def __init__(self, art: SpriteArt, palette: SpritePalette):
        self.mArt = art
        self.mPalette = palette
        self.mCache = {}

    def character(self, species: str, frame: str, overlays: Tuple[str, ...]) -> cairo.ImageSurface:
        tKey = ("character", species, frame, overlays)
        tSurface = self.mCache.get(tKey)
        if tSurface is None:
            tSurface = self._surface(self.mArt.composite(species, frame, overlays), self.mPalette.colors(species), True)
            self.mCache[tKey] = tSurface
        return tSurface

    def sticker(self, name: str, rows: Sequence[str]) -> cairo.ImageSurface:
        """A species-neutral shape drawn over the desktop, such as a badge."""
        tKey = ("sticker", name)
        tSurface = self.mCache.get(tKey)
        if tSurface is None:
            tSurface = self._surface(rows, self.mPalette.colors(self.NO_SPECIES), True)
            self.mCache[tKey] = tSurface
        return tSurface

    def plateShape(self, name: str, rows: Sequence[str], dark: bool) -> cairo.ImageSurface:
        """A control drawn on the plate: the gear or the grip."""
        tKey = ("plate", name, dark)
        tSurface = self.mCache.get(tKey)
        if tSurface is None:
            tSurface = self._surface(rows, self.mPalette.plateColors(dark), False)
            self.mCache[tKey] = tSurface
        return tSurface

    def _surface(self, rows: Sequence[str], colors: Dict[str, Rgba], rim: bool) -> cairo.ImageSurface:
        tHeight = len(rows)
        tWidth = len(rows[0])
        tSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tWidth, tHeight)
        tStride = tSurface.get_stride()
        tData = tSurface.get_data()
        for tY, tRow in enumerate(rows):
            for tX, tKey in enumerate(tRow):
                if tKey == SpriteConstants.TRANSPARENT:
                    if not rim or not self._touchesSolid(rows, tX, tY):
                        continue
                    tColor = self.mPalette.rim()
                else:
                    tColor = colors[tKey]
                tOffset = tY * tStride + tX * 4
                tData[tOffset:tOffset + 4] = self._premultiplied(tColor)
        tSurface.mark_dirty()
        return tSurface

    def _touchesSolid(self, rows: Sequence[str], x: int, y: int) -> bool:
        for tDx, tDy in self.NEIGHBOURS:
            tX = x + tDx
            tY = y + tDy
            if 0 <= tY < len(rows) and 0 <= tX < len(rows[tY]):
                tKey = rows[tY][tX]
                if tKey != SpriteConstants.TRANSPARENT and tKey not in self.RIMLESS_KEYS:
                    return True
        return False

    @staticmethod
    def _premultiplied(color: Rgba) -> bytes:
        tRed, tGreen, tBlue, tAlpha = color
        tChannels = (int(tBlue * tAlpha * 255 + 0.5), int(tGreen * tAlpha * 255 + 0.5), int(tRed * tAlpha * 255 + 0.5), int(tAlpha * 255 + 0.5))
        # FORMAT_ARGB32 is a native-endian 32-bit word: B, G, R, A in memory on little-endian hosts.
        return bytes(tChannels) if sys.byteorder == "little" else bytes(reversed(tChannels))
