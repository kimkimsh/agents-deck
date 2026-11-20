import math

import cairo
from gi.repository import Gdk, Gtk, Pango, PangoCairo

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.constants.theme_constants import ThemeConstants
from agents_deck.ui.rect import Rect
from agents_deck.ui.tooltip_text import TooltipText


class TooltipWindow(Gtk.Window):
    """Popup describing one tile, placed above it or, near the top of the
    screen, below it. Never takes focus or input. UI thread only."""

    mText: TooltipText
    mDark: bool

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.mText = TooltipText("", ())
        self.mDark = False
        tVisual = self.get_screen().get_rgba_visual()
        if tVisual is not None:
            self.set_visual(tVisual)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.TOOLTIP)
        self.connect("draw", self._onDraw)
        self.connect("realize", self._onRealize)

    def showFor(self, text: TooltipText, anchor: Rect, dark: bool):
        """`anchor` is the tile in root-window coordinates."""
        self.mText = text
        self.mDark = dark
        tWidth, tHeight = self._measure()
        self.resize(tWidth, tHeight)
        tX, tY = self._placement(anchor, tWidth, tHeight)
        self.move(tX, tY)
        self.show()
        self.queue_draw()

    def _placement(self, anchor: Rect, width: int, height: int):
        tDisplay = Gdk.Display.get_default()
        tMonitor = tDisplay.get_monitor_at_point(int(anchor.centerX()), int(anchor.centerY())) if tDisplay is not None else None
        tArea = tMonitor.get_workarea() if tMonitor is not None else None
        tX = int(anchor.centerX() - width / 2)
        tY = anchor.mY - LayoutConstants.TOOLTIP_GAP_PX - height
        if tArea is not None:
            if tY < tArea.y:
                tY = anchor.mY + anchor.mHeight + LayoutConstants.TOOLTIP_GAP_PX
            tX = min(max(tX, tArea.x), tArea.x + tArea.width - width)
        return tX, tY

    def _measure(self):
        tSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        tContext = cairo.Context(tSurface)
        tTitle, tBody = self._layouts(tContext)
        _, tTitleSize = tTitle.get_pixel_extents()
        tBodyWidth, tBodyHeight = (0, 0)
        if tBody is not None:
            _, tBodySize = tBody.get_pixel_extents()
            tBodyWidth, tBodyHeight = tBodySize.width, tBodySize.height
        tPadding = LayoutConstants.TOOLTIP_PADDING_PX
        return max(tTitleSize.width, tBodyWidth) + 2 * tPadding, tTitleSize.height + tBodyHeight + 2 * tPadding

    def _layouts(self, context):
        tInner = (LayoutConstants.TOOLTIP_MAX_WIDTH_PX - 2 * LayoutConstants.TOOLTIP_PADDING_PX) * Pango.SCALE
        tTitle = PangoCairo.create_layout(context)
        tTitle.set_font_description(Pango.FontDescription.from_string(LayoutConstants.TOOLTIP_TITLE_FONT))
        tTitle.set_text(self.mText.mTitle, -1)
        tTitle.set_width(tInner)
        tTitle.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        if not self.mText.mLines:
            return tTitle, None
        tBody = PangoCairo.create_layout(context)
        tBody.set_font_description(Pango.FontDescription.from_string(LayoutConstants.TOOLTIP_BODY_FONT))
        tBody.set_text("\n".join(self.mText.mLines), -1)
        tBody.set_width(tInner)
        tBody.set_wrap(Pango.WrapMode.WORD_CHAR)
        return tTitle, tBody

    def _onRealize(self, widget):
        tWindow = self.get_window()
        if tWindow is not None:
            tWindow.input_shape_combine_region(cairo.Region([]), 0, 0)

    def _onDraw(self, widget, context: cairo.Context):
        tWidth = self.get_allocated_width()
        tHeight = self.get_allocated_height()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        self._roundedRect(context, 0.5, 0.5, tWidth - 1, tHeight - 1, LayoutConstants.TOOLTIP_RADIUS_PX)
        context.set_source_rgba(*(ThemeConstants.TOOLTIP_BACKGROUND_DARK if self.mDark else ThemeConstants.TOOLTIP_BACKGROUND_LIGHT))
        context.fill_preserve()
        context.set_source_rgba(*(ThemeConstants.TOOLTIP_BORDER_DARK if self.mDark else ThemeConstants.TOOLTIP_BORDER_LIGHT))
        context.set_line_width(1)
        context.stroke()
        tTitle, tBody = self._layouts(context)
        tPadding = LayoutConstants.TOOLTIP_PADDING_PX
        context.move_to(tPadding, tPadding)
        context.set_source_rgba(*(ThemeConstants.TOOLTIP_TEXT_DARK if self.mDark else ThemeConstants.TOOLTIP_TEXT_LIGHT))
        PangoCairo.show_layout(context, tTitle)
        if tBody is not None:
            _, tTitleSize = tTitle.get_pixel_extents()
            context.move_to(tPadding, tPadding + tTitleSize.height)
            context.set_source_rgba(*(ThemeConstants.TOOLTIP_MUTED_DARK if self.mDark else ThemeConstants.TOOLTIP_MUTED_LIGHT))
            PangoCairo.show_layout(context, tBody)
        return True

    @staticmethod
    def _roundedRect(context: cairo.Context, x: float, y: float, width: float, height: float, radius: float):
        context.new_sub_path()
        context.arc(x + width - radius, y + radius, radius, -0.5 * math.pi, 0)
        context.arc(x + width - radius, y + height - radius, radius, 0, 0.5 * math.pi)
        context.arc(x + radius, y + height - radius, radius, 0.5 * math.pi, math.pi)
        context.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
        context.close_path()
