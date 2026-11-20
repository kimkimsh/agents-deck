"""Renders the app icon from the deck's own sprites into a hicolor icon tree.

Usage, from the repository root: python3 -m tools.render_app_icon build/icons

Writes <out>/hicolor/<size>x<size>/apps/<app id>.png for every size GTK and
GNOME Shell ask for. Only pycairo is needed, which the app needs anyway.

The plate is drawn smooth at the target size; the characters stay on their
own pixel grid at a whole-number scale, so no size is resampled into blur.
"""
import math
import os
import sys
from typing import Sequence, Tuple

import cairo

from agents_deck.constants.app_constants import AppConstants
from agents_deck.constants.sprite_constants import SpriteConstants
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_atlas import SpriteAtlas
from agents_deck.ui.sprite_palette import SpritePalette

# 16 is missing on purpose: the hero is 18 sprite pixels wide and is never
# drawn below one screen pixel per sprite pixel, so GTK scales the 24 down.
ICON_SIZES = (24, 32, 48, 64, 96, 128, 256, 512)
# Below this the thought bubble is too small to read, so the hero idles.
BUBBLE_MIN_SIZE = 64
# From this size the three-character lineup fits at two pixels per sprite pixel.
LINEUP_MIN_SIZE = 128
HICOLOR_DIR = "hicolor"
APPS_DIR = "apps"
SIZE_DIR_FORMAT = "%dx%d"
PNG_SUFFIX = ".png"

CONTENT_FILL = 0.80
PLATE_MARGIN = 0.07
SQUIRCLE_EXPONENT = 5.0
SQUIRCLE_STEPS = 360
PLATE_TOP = "#433c63"
PLATE_BOTTOM = "#1d1a2a"
SHADOW_DROP = 0.02
SHADOW_ALPHA = 0.28
SHEEN_ALPHA = 0.10
SHEEN_DEPTH = 0.5
EDGE_ALPHA = 0.10
EDGE_WIDTH_PER_PIXEL = 1.0 / 128
GLOW_ALPHA = 0.22
GLOW_CENTER_Y = 0.52
GLOW_RADIUS = 0.5
BODY_COLOR_KEY = "b"
ALPHA_SHIFT = 24

Layer = Tuple[str, str, Tuple[str, ...], int, int]

IDLE_HERO: Sequence[Layer] = ((SpriteArt.EMBER, "idle", (), 0, 0),)
THINKING_HERO: Sequence[Layer] = ((SpriteArt.EMBER, "think0", ("think3",), 0, 0),)
# The deck's own lineup. The Claude character is raised and drawn last, so
# its bubble clears the other two and its body overlaps theirs.
LINEUP: Sequence[Layer] = (
    (SpriteArt.CUBIT, "idle", (), 0, 6),
    (SpriteArt.FLOATY, "idle", (), 30, 6),
    (SpriteArt.EMBER, "think0", ("think3",), 15, 0),
)


def scene(size: int) -> Sequence[Layer]:
    if size >= LINEUP_MIN_SIZE:
        return LINEUP
    if size >= BUBBLE_MIN_SIZE:
        return THINKING_HERO
    return IDLE_HERO


def composite(atlas: SpriteAtlas, layers: Sequence[Layer]) -> cairo.ImageSurface:
    """The layers drawn together at one pixel per sprite pixel, trimmed to what is visible."""
    tWidth = max(tLayer[3] for tLayer in layers) + SpriteConstants.CANVAS
    tHeight = max(tLayer[4] for tLayer in layers) + SpriteConstants.CANVAS
    tLoose = cairo.ImageSurface(cairo.FORMAT_ARGB32, tWidth, tHeight)
    tContext = cairo.Context(tLoose)
    for tSpecies, tFrame, tOverlays, tX, tY in layers:
        tContext.set_source_surface(atlas.character(tSpecies, tFrame, tOverlays), tX, tY)
        tContext.paint()
    tLeft, tTop, tRight, tBottom = opaqueBounds(tLoose)
    tTrimmed = cairo.ImageSurface(cairo.FORMAT_ARGB32, tRight - tLeft, tBottom - tTop)
    tTrimmedContext = cairo.Context(tTrimmed)
    tTrimmedContext.set_source_surface(tLoose, -tLeft, -tTop)
    tTrimmedContext.paint()
    return tTrimmed


def opaqueBounds(surface: cairo.ImageSurface) -> Tuple[int, int, int, int]:
    """Left, top, right, bottom (exclusive) of the pixels with any alpha."""
    surface.flush()
    # ARGB32 is a native-endian 32-bit word per pixel; alpha is its top byte.
    tPixels = memoryview(surface.get_data()).cast("I")
    tRowWords = surface.get_stride() // tPixels.itemsize
    tXs = []
    tYs = []
    for tY in range(surface.get_height()):
        for tX in range(surface.get_width()):
            if tPixels[tY * tRowWords + tX] >> ALPHA_SHIFT:
                tXs.append(tX)
                tYs.append(tY)
    return min(tXs), min(tYs), max(tXs) + 1, max(tYs) + 1


def plateBounds(size: int) -> Tuple[float, float]:
    """Offset and side of the plate inside an icon of this size."""
    tMargin = size * PLATE_MARGIN
    return tMargin, size - 2 * tMargin


def spriteScale(size: int, content: cairo.ImageSurface) -> int:
    """Screen pixels per sprite pixel for this content at this icon size."""
    return int(CONTENT_FILL * size) // max(content.get_width(), content.get_height())


def squircle(context: cairo.Context, left: float, top: float, side: float):
    tRadius = side / 2
    tCenterX = left + tRadius
    tCenterY = top + tRadius
    for tStep in range(SQUIRCLE_STEPS):
        tAngle = 2 * math.pi * tStep / SQUIRCLE_STEPS
        tCos = math.cos(tAngle)
        tSin = math.sin(tAngle)
        tX = tCenterX + tRadius * math.copysign(abs(tCos) ** (2 / SQUIRCLE_EXPONENT), tCos)
        tY = tCenterY + tRadius * math.copysign(abs(tSin) ** (2 / SQUIRCLE_EXPONENT), tSin)
        if tStep == 0:
            context.move_to(tX, tY)
        else:
            context.line_to(tX, tY)
    context.close_path()


def paintPlate(context: cairo.Context, size: int, glow: Tuple[float, float, float, float]):
    tMargin, tSide = plateBounds(size)
    squircle(context, tMargin, tMargin + size * SHADOW_DROP, tSide)
    context.set_source_rgba(0, 0, 0, SHADOW_ALPHA)
    context.fill()

    squircle(context, tMargin, tMargin, tSide)
    tFill = cairo.LinearGradient(0, tMargin, 0, tMargin + tSide)
    tFill.add_color_stop_rgba(0, *SpritePalette.parse(PLATE_TOP))
    tFill.add_color_stop_rgba(1, *SpritePalette.parse(PLATE_BOTTOM))
    context.set_source(tFill)
    context.fill_preserve()

    context.save()
    context.clip()
    tSheen = cairo.LinearGradient(0, tMargin, 0, tMargin + tSide * SHEEN_DEPTH)
    tSheen.add_color_stop_rgba(0, 1, 1, 1, SHEEN_ALPHA)
    tSheen.add_color_stop_rgba(1, 1, 1, 1, 0)
    context.set_source(tSheen)
    context.paint()
    tGlowY = size * GLOW_CENTER_Y
    tGlow = cairo.RadialGradient(size / 2, tGlowY, 0, size / 2, tGlowY, tSide * GLOW_RADIUS)
    tGlow.add_color_stop_rgba(0, glow[0], glow[1], glow[2], GLOW_ALPHA)
    tGlow.add_color_stop_rgba(1, glow[0], glow[1], glow[2], 0)
    context.set_source(tGlow)
    context.paint()
    context.restore()

    tEdge = max(1.0, size * EDGE_WIDTH_PER_PIXEL)
    squircle(context, tMargin + tEdge / 2, tMargin + tEdge / 2, tSide - tEdge)
    context.set_line_width(tEdge)
    context.set_source_rgba(1, 1, 1, EDGE_ALPHA)
    context.stroke()


def paintIcon(atlas: SpriteAtlas, palette: SpritePalette, size: int) -> cairo.ImageSurface:
    tIcon = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    tContext = cairo.Context(tIcon)
    paintPlate(tContext, size, palette.colors(SpriteArt.EMBER)[BODY_COLOR_KEY])
    tContent = composite(atlas, scene(size))
    tScale = spriteScale(size, tContent)
    tContext.translate((size - tContent.get_width() * tScale) // 2, (size - tContent.get_height() * tScale) // 2)
    tContext.scale(tScale, tScale)
    tContext.set_source_surface(tContent, 0, 0)
    tContext.get_source().set_filter(cairo.FILTER_NEAREST)
    tContext.paint()
    return tIcon


def main() -> int:
    tOutDir = sys.argv[1]
    tPalette = SpritePalette()
    tAtlas = SpriteAtlas(SpriteArt(), tPalette)
    for tSize in ICON_SIZES:
        tDir = os.path.join(tOutDir, HICOLOR_DIR, SIZE_DIR_FORMAT % (tSize, tSize), APPS_DIR)
        os.makedirs(tDir, exist_ok=True)
        paintIcon(tAtlas, tPalette, tSize).write_to_png(os.path.join(tDir, AppConstants.APP_ID + PNG_SUFFIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
