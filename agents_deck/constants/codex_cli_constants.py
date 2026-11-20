class CodexCliConstants:
    """Command-line grammar of `codex` (0.170 `--help`) needed to tell a TUI from other modes."""

    # Subcommands that open the interactive TUI.
    TUI_SUBCOMMANDS = ("resume", "fork", "agents")

    # Every other subcommand, including aliases; none of them is an interactive pane session.
    OTHER_SUBCOMMANDS = (
        "exec", "e", "review", "login", "logout", "mcp", "mcp-server", "plugin", "app-server",
        "remote-control", "completion", "update", "doctor", "sandbox", "debug", "apply", "a",
        "queue", "archive", "delete", "migrate-rollouts", "migrate-nfs-db", "unarchive", "cloud",
        "exec-server", "features", "help",
    )

    # Options that consume the next argument as their value (unless written `--opt=value`
    # or, for a short option, `-oVALUE`).
    VALUE_OPTIONS = (
        "-c", "--config", "--enable", "--disable", "--remote", "--remote-auth-token-env",
        "-m", "--model", "--local-provider", "-p", "--profile", "-s", "--sandbox",
        "-C", "--cd", "--add-dir", "-a", "--ask-for-approval",
    )

    # Options that consume every following non-option argument (`-i a.png b.png`).
    MULTI_VALUE_OPTIONS = ("-i", "--image")

    # Options that print and exit.
    EXIT_OPTIONS = ("-h", "--help", "-V", "--version")

    END_OF_OPTIONS = "--"
    OPTION_PREFIX = "-"
    LONG_OPTION_PREFIX = "--"
    OPTION_VALUE_SEPARATOR = "="
    SHORT_OPTION_LENGTH = 2
