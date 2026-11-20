class SpriteConstants:
    """Geometry of the sprite canvas, in sprite pixels."""

    CANVAS = 24

    # Pixel x and CANVAS - 1 - x mirror each other; in continuous
    # coordinates the axis is at 12.0, between columns 11 and 12.
    CENTER_X = 12.0
    CENTER_LEFT = 11

    TRANSPARENT = "."
    SHADOW_KEY = "d"

    # Top-left of the count badge on the tile: above-left of the head, where
    # no species draws its face and no bubble or prop is placed.
    BADGE_LEFT = 0
    BADGE_TOP = 2
    BADGE_DIGIT_WIDTH = 3
    BADGE_DIGIT_HEIGHT = 5
    BADGE_DIGIT_GAP = 1
    # Fill between the digits and the outline. Without the vertical pad the
    # digit's top and bottom strokes merge into the outline and the glyph
    # reads as its own negative.
    BADGE_PAD_X = 2
    BADGE_PAD_Y = 1
    BADGE_OUTLINE = 1
    # Per-row inset from the outer rows inward, rounding the pill's corners.
    BADGE_CORNER_INSETS = (2, 1)
    BADGE_MAX_COUNT = 9
    BADGE_OVERFLOW = "+"
