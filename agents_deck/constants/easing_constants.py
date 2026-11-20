class EasingConstants:
    """Control points of the timing curves, as CSS cubic-bezier arguments."""

    # Strong ease-out for things responding to the pointer.
    EASE_OUT = (0.23, 1.0, 0.32, 1.0)
    # Ease-in-out for things moving across the screen.
    EASE_IN_OUT = (0.77, 0.0, 0.175, 1.0)
