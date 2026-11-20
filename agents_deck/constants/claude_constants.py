class ClaudeConstants:
    """Record shapes of Claude Code's session registry and transcript (2.1.32x)."""

    STATUS_BUSY = "busy"
    STATUS_SHELL = "shell"
    STATUS_IDLE = "idle"
    STATUS_WAITING = "waiting"

    NAME_SOURCE_USER = "user"

    RECORD_ASSISTANT = "assistant"
    RECORD_USER = "user"
    RECORD_QUEUE_OPERATION = "queue-operation"
    QUEUE_ENQUEUE = "enqueue"

    BLOCK_TOOL_USE = "tool_use"
    BLOCK_TOOL_RESULT = "tool_result"
    STOP_END_TURN = "end_turn"

    TASK_NOTIFICATION_TAG = "<task-notification>"
    TASK_TERMINAL_STATUSES = ("completed", "failed", "killed", "stopped")
    ASYNC_LAUNCHED = "async_launched"

    # Background task ids carry their kind as a one-letter prefix.
    TASK_PREFIX_SHELL = "b"
    TASK_PREFIX_AGENT = "a"
    TASK_PREFIX_REMOTE = "r"
    TASK_PREFIX_TEAMMATE = "t"
    TASK_PREFIX_WORKFLOW = "w"
    TASK_PREFIXES_MONITOR = ("m", "s")

    WAITING_PERMISSION_REASONS = ("permission prompt", "sandbox request")

    # Tools whose result ends a background task; their toolUseResult is
    # {task_id, task_type, command, message}.
    STOP_TOOL_NAMES = ("TaskStop",)
    STOP_RESULT_TASK_ID = "task_id"

    # Raw-line markers of the records that open or close a background task.
    # A stop result is only trusted next to its tool call, so the call's
    # line is needed too.
    BACKGROUND_NEEDLES = (b"backgroundTaskId", b"async_launched", b"task-notification", b'"name":"TaskStop"', b'"task_type"')

    # Synthetic id for the background shell the registry reports when its
    # launch record is outside the transcript window.
    UNSEEN_SHELL_TASK_ID = "registry-shell"
