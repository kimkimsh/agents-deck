from agents_deck.constants.sprite_constants import SpriteConstants


class LayoutConstants:
    """Overlay geometry. Sizes in sprite pixels unless named _PX (window pixels)."""

    # A tile is one sprite, painted at the deck's scale with no resampling.
    TILE = SpriteConstants.CANVAS
    GAP = 2
    PLATE_PADDING = 3
    SIDE_GAP = 2
    GEAR = 12
    GRIP = 8
    PLATE_CORNER = 5

    MIN_SCALE = 2
    MAX_SCALE = 6
    DEFAULT_SCALE = 3
    MIN_GRID = 1
    MAX_GRID = 8
    DEFAULT_COLUMNS = 4
    DEFAULT_ROWS = 1

    # A press that moves farther than this is a drag, not a click.
    DRAG_THRESHOLD_PX = 6

    NAME_ROW_PX = 16
    NAME_FONT = "Sans 9"
    NAME_HALO_PX = 1

    # Remembered tile order is capped at this many panes; panes not seen for
    # longest are dropped first, and a live pane is never dropped.
    ORDER_CAP = 64

    # X11 window coordinates are signed 16-bit.
    MIN_SCREEN_COORDINATE = -32768
    MAX_SCREEN_COORDINATE = 32767

    # Window pixels of grip drag per one-step change of scale.
    SCALE_STEP_PX = 24

    TOOLTIP_MAX_WIDTH_PX = 280
    TOOLTIP_PADDING_PX = 8
    TOOLTIP_GAP_PX = 6
    TOOLTIP_RADIUS_PX = 6
    TOOLTIP_TITLE_FONT = "Sans Semi-Bold 10"
    TOOLTIP_BODY_FONT = "Sans 9"
    TOOLTIP_MAX_TASK_LINES = 4

    UNKNOWN_OPACITY = 0.55
    STALE_OPACITY = 0.6
    GHOST_OPACITY = 0.4
