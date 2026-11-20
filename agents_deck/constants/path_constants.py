class PathConstants:
    """Locations of agent state, relative to the user's home directory."""

    CLAUDE_SESSIONS = ".claude/sessions"
    CLAUDE_REGISTRY_FILE_FORMAT = "%d.json"
    CLAUDE_PROJECTS = ".claude/projects"
    CLAUDE_TRANSCRIPT_SUFFIX = ".jsonl"

    CODEX_STATE_DB = ".codex/state_5.sqlite"
    CODEX_TUI_MARKERS = ".codex/tui-thread-reference-capabilities"
    CODEX_SESSIONS = ".codex/sessions"

    AGY_ROOT = ".gemini/antigravity-cli"
    AGY_LOG_DIR = "log"
    AGY_BRAIN_DIR = "brain"
    AGY_TRANSCRIPT = ".system_generated/logs/transcript.jsonl"

    SETTINGS_DIR = "agents-deck"
    SETTINGS_FILE = "settings.json"
