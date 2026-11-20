from enum import Enum


class BackgroundKind(str, Enum):
    SHELL = "shell"
    AGENT = "agent"
    MONITOR = "monitor"
    WORKFLOW = "workflow"
    REMOTE = "remote"
    PROCESS = "process"
