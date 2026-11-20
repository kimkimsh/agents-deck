import re


class CodexConstants:
    """Record shapes of Codex state_5.sqlite, TUI markers and rollouts (0.170/0.171)."""

    ROLLOUT_FILE_GLOB = "rollout-*-%s.jsonl"
    ROLLOUT_DATE_DIR_FORMAT = "%Y/%m/%d"
    TOOL_CALL_ID_VAR = "CODEX_TOOL_CALL_ID"

    # Thread ids are UUIDv7: the first 48 bits are the creation time in ms.
    UUID7_TIME_HEX_CHARS = 12
    SECONDS_PER_DAY = 86400.0

    SUBAGENT_SOURCE_PREFIX = "{"

    # Thread ids are canonical lowercase UUIDs; marker files are named by them.
    THREAD_ID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

    RECORD_EVENT = "event_msg"
    RECORD_RESPONSE = "response_item"
    EVENT_TASK_STARTED = "task_started"
    EVENT_TASK_COMPLETE = "task_complete"
    EVENT_TURN_ABORTED = "turn_aborted"
    EVENT_ITEM_COMPLETED = "item_completed"
    EVENT_SUBAGENT_ACTIVITY = "sub_agent_activity"
    ITEM_SUBAGENT_ACTIVITY = "SubAgentActivity"
    SUBAGENT_STARTED = "started"
    SUBAGENT_FINISHED_KINDS = ("completed", "interrupted")

    CALL_TYPES = ("function_call", "custom_tool_call")
    CALL_OUTPUT_TYPES = ("function_call_output", "custom_tool_call_output")

    # Codex's tool for asking the user a question. Its handler awaits the
    # answer, so while the call is open the session waits on the user. The
    # `request_user_input_async` variant returns at once and is an ordinary call.
    USER_INPUT_TOOL = "request_user_input"

    # Raw-line markers of the records that carry turn, call and subagent state;
    # each is the quoted JSON string value, as Codex serializes it.
    STATE_NEEDLES = (
        b'"task_started"',
        b'"task_complete"',
        b'"turn_aborted"',
        b'"function_call"',
        b'"custom_tool_call"',
        b'"function_call_output"',
        b'"custom_tool_call_output"',
        b'"sub_agent_activity"',
        b'"SubAgentActivity"',
    )
    SQLITE_TIMEOUT_SECONDS = 0.2
