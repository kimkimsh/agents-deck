class AnimationConstants:
    """Overlay animation and interaction timings, in milliseconds unless named otherwise."""

    # Frames are recomputed on this tick; a tile is redrawn only when its frame changes.
    FRAME_TICK_MS = 50

    WORK_FRAME_MS = 250
    THINK_BODY_MS = 500
    THINK_DOTS_MS = 333
    RAISE_FRAME_MS = 400
    ERROR_FRAME_MS = 300
    SLEEP_FRAME_MS = 1000
    CURSOR_BLINK_MS = 500

    # An error animates this long, then holds its first frame.
    ERROR_LOOP_MS = 3000

    # Idle characters blink once per period; the period is spread over this
    # range per pane so a row of idle tiles does not blink in unison.
    BLINK_PERIOD_MIN_MS = 5000
    BLINK_PERIOD_SPREAD_MS = 3000
    BLINK_DURATION_MS = 160

    IDLE_SLEEP_AFTER_SECONDS = 600.0

    TOOLTIP_DELAY_MS = 400
    # After a tooltip closes, hovering another tile within this window opens its tooltip at once.
    TOOLTIP_WARM_MS = 300

    HOVER_LIFT_MS = 120
    SHELF_FADE_IN_MS = 150
    SHELF_FADE_OUT_MS = 150
    SHELF_HIDE_DELAY_MS = 300
    FIRST_RUN_SHELF_MS = 4000
    DROP_RETURN_MS = 200
    SHAKE_MS = 160
    SHAKE_AMPLITUDE_PX = 2
    SHAKE_CYCLES = 2

    SETTINGS_SAVE_DELAY_MS = 500
