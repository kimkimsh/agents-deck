import math
from typing import Sequence, Tuple

import cairo
from gi.repository import Pango, PangoCairo

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.constants.sprite_constants import SpriteConstants
from agents_deck.constants.theme_constants import ThemeConstants
from agents_deck.ui.grid_layout import GridLayout
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_atlas import SpriteAtlas
from agents_deck.ui.tile_view import TileView


class DeckPainter:
    """Draws the overlay: the plate, the side controls, then the tiles.

    Sprites are scaled by an integer factor with nearest-neighbour sampling
    and every offset is rounded to a whole window pixel, so pixel art never
    smears. The plate's corners are stepped in sprite pixels for the same
    reason. UI thread only.
    """

    mAtlas: SpriteAtlas
    mArt: SpriteArt

    def __init__(self, atlas: SpriteAtlas, art: SpriteArt):
        self.mAtlas = atlas
        self.mArt = art

    def paint(self, context: cairo.Context, layout: GridLayout, tiles: Sequence[TileView], shelfAlpha: float, dark: bool):
        context.save()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.restore()
        if shelfAlpha > 0.0:
            self._plate(context, layout, shelfAlpha, dark)
            self._plateShape(context, "gear", SpriteArt.GEAR, layout.gearRect().mX, layout.gearRect().mY, layout.mScale, shelfAlpha, dark)
            self._plateShape(context, "grip", SpriteArt.GRIP, layout.gripRect().mX, layout.gripRect().mY, layout.mScale, shelfAlpha, dark)
        for tTile in tiles:
            self._tile(context, layout, tTile, dark)

    def _plate(self, context: cairo.Context, layout: GridLayout, alpha: float, dark: bool):
        tRed, tGreen, tBlue, tAlpha = ThemeConstants.PLATE_DARK if dark else ThemeConstants.PLATE_LIGHT
        context.set_source_rgba(tRed, tGreen, tBlue, tAlpha * alpha)
        tScale = layout.mScale
        tWidth = layout.width()
        tHeight = layout.height()
        tInsets = self._cornerInsets(LayoutConstants.PLATE_CORNER)
        tCorner = len(tInsets) * tScale
        context.rectangle(0, tCorner, tWidth, tHeight - 2 * tCorner)
        for tRow, tInset in enumerate(tInsets):
            tLeft = tInset * tScale
            context.rectangle(tLeft, tRow * tScale, tWidth - 2 * tLeft, tScale)
            context.rectangle(tLeft, tHeight - (tRow + 1) * tScale, tWidth - 2 * tLeft, tScale)
        context.fill()

    @staticmethod
    def _cornerInsets(radius: int) -> Tuple[int, ...]:
        """Per-row inset of a stepped quarter circle, top row first."""
        return tuple(radius - int(round(math.sqrt(radius * radius - (radius - tRow - 0.5) ** 2))) for tRow in range(radius))

    def _tile(self, context: cairo.Context, layout: GridLayout, tile: TileView, dark: bool):
        tFrame = tile.mFrame
        tSurface = self.mAtlas.character(tFrame.mSpecies, tFrame.mFrame, tFrame.mOverlays)
        self._blit(context, tSurface, round(tile.mX), round(tile.mY), layout.mScale, tile.mOpacity)
        if tile.mBadgeCount:
            # Every count past the largest digit draws the same "9+" badge.
            tShown = min(tile.mBadgeCount, SpriteConstants.BADGE_MAX_COUNT + 1)
            tBadge = self.mArt.badge(tShown)
            tBadgeSurface = self.mAtlas.sticker("badge-%d" % tShown, tBadge)
            tBadgeX = round(tile.mX) + SpriteConstants.BADGE_LEFT * layout.mScale
            tBadgeY = round(tile.mY) + SpriteConstants.BADGE_TOP * layout.mScale
            self._blit(context, tBadgeSurface, tBadgeX, tBadgeY, layout.mScale, tile.mOpacity)
        if tile.mName:
            self._name(context, layout, tile, dark)

    def _plateShape(self, context: cairo.Context, name: str, rows: Sequence[str], x: int, y: int, scale: int, alpha: float, dark: bool):
        self._blit(context, self.mAtlas.plateShape(name, rows, dark), x, y, scale, alpha)

    @staticmethod
    def _blit(context: cairo.Context, surface: cairo.ImageSurface, x: int, y: int, scale: int, alpha: float):
        context.save()
        context.translate(x, y)
        context.scale(scale, scale)
        context.set_source_surface(surface, 0, 0)
        context.get_source().set_filter(cairo.FILTER_NEAREST)
        context.paint_with_alpha(alpha)
        context.restore()

    def _name(self, context: cairo.Context, layout: GridLayout, tile: TileView, dark: bool):
        tWidth = layout.tileSize() + LayoutConstants.GAP * layout.mScale
        tText = PangoCairo.create_layout(context)
        tText.set_font_description(Pango.FontDescription.from_string(LayoutConstants.NAME_FONT))
        tText.set_text(tile.mName or "", -1)
        tText.set_width(tWidth * Pango.SCALE)
        tText.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        tText.set_alignment(Pango.Alignment.CENTER)
        context.save()
        context.translate(round(tile.mX) - LayoutConstants.GAP * layout.mScale // 2, round(tile.mY) + layout.tileSize())
        PangoCairo.layout_path(context, tText)
        context.set_source_rgba(*(ThemeConstants.NAME_HALO_DARK if dark else ThemeConstants.NAME_HALO_LIGHT))
        context.set_line_width(2 * LayoutConstants.NAME_HALO_PX)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.stroke()
        context.set_source_rgba(*(ThemeConstants.NAME_TEXT_DARK if dark else ThemeConstants.NAME_TEXT_LIGHT))
        PangoCairo.show_layout(context, tText)
        context.restore()

