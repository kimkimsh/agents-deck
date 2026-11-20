class TailConstants:
    """Limits for reading append-only, newline-framed files."""

    # On first attach only the end of a file is parsed: Claude transcripts
    # reach hundreds of MB. Records before this window are recovered from
    # the lines that contain the owner's needles (LineTail).
    INITIAL_WINDOW_BYTES = 8 * 1024 * 1024

    # Bytes read per poll at most; the rest is picked up on later polls.
    MAX_READ_BYTES_PER_POLL = 16 * 1024 * 1024
