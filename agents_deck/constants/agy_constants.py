import re


class AgyConstants:
    """Record shapes of the Antigravity CLI (agy 1.0.x) glog and brain transcript."""

    LOG_NAME_TIME_FORMAT = "cli-%Y%m%d_%H%M%S.log"

    # glog header: "I0529 14:03:09.986603 <pid> file.go:123] message"
    GLOG_PID_FIELD = 2

    # The whole line, as written by server.go and conversation_manager.go.
    CONVERSATION_LINE = re.compile(
        rb"[IWEF]\d{4} \d{2}:\d{2}:\d{2}\.\d+ +(\d+) [\w.-]+\.go:\d+\] (?:Created|Streaming) conversation "
        rb"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    )
    LINE_PID_GROUP = 1
    LINE_CONVERSATION_GROUP = 2
    CONVERSATION_LINE_NEEDLES = (b"] Created conversation ", b"] Streaming conversation ")

    STEP_INDEX = "step_index"
    STATUS_ERROR = "ERROR"
    STEP_PLANNER = "PLANNER_RESPONSE"
    STEP_ERROR_MESSAGE = "ERROR_MESSAGE"
    # Bookkeeping steps that say nothing about what the agent is doing now.
    META_STEPS = ("CONVERSATION_HISTORY", "GENERIC", "SYSTEM_MESSAGE")

    LOG_SUFFIX = ".log"
