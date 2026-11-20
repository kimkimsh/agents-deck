from enum import Enum


class AgentKind(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    AGY = "agy"
