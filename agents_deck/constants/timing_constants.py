class TimingConstants:
    """Collector timings (polling and linking windows) and the second/millisecond conversion."""

    MS_PER_SECOND = 1000.0
    POLL_INTERVAL_SECONDS = 1.0

    # Clock skew allowed between a TUI's /proc start time and the mtime of a
    # marker it wrote.
    CODEX_LINK_SLACK_SECONDS = 1.0

    # A TUI attaches its first thread within this long after starting
    # (observed 2 s for `resume`, 10 s for a new thread).
    CODEX_ATTACH_WINDOW_SECONDS = 30.0

    # How long an exited Codex TUI is still considered when crediting
    # attach markers written while it was alive.
    CODEX_TUI_MEMORY_SECONDS = 600.0

    # An agy log file is named after the second its process started.
    AGY_LOG_START_SLACK_SECONDS = 2.0

    # An agy log is opened during start-up, so it is named no later than this
    # after the process started; a later log with the same pid is another process.
    AGY_LOG_OPEN_WINDOW_SECONDS = 30.0

    # A snapshot older than this many polls means the collector has stalled.
    STALE_SNAPSHOT_POLLS = 3
