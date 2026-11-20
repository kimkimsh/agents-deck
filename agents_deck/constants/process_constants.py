class ProcessConstants:
    """Names and field positions used to read /proc and recognise Warp and agent processes."""

    PROC_ROOT = "/proc"

    # /proc/<pid>/stat fields after the closing ")" of comm, zero-based.
    # Field 3 (state) is index 0, so field N is index N - 3.
    STAT_PPID_INDEX = 1
    STAT_PGRP_INDEX = 2
    STAT_TTY_INDEX = 4
    STAT_TPGID_INDEX = 5
    STAT_START_TICKS_INDEX = 19
    BOOT_TIME_KEY = "btime"
    NO_CONTROLLING_TTY = 0

    WARP_SERVER_COMM = "warp"
    WARP_SERVER_ARG = "terminal-server"
    WARP_PANE_UUID_VAR = "WARP_TERMINAL_SESSION_UUID"

    CLAUDE_COMM = "claude"
    CODEX_COMM = "codex"
    AGY_COMM = "agy"

    CODEX_THREAD_ID_VAR = "CODEX_THREAD_ID"

    # Upper bound on ancestry walks; guards against a corrupted ppid cycle.
    MAX_TREE_DEPTH = 64
