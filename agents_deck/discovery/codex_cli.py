from typing import Sequence

from agents_deck.constants.codex_cli_constants import CodexCliConstants


class CodexCli:
    """Tells from a `codex` argv whether the process is the interactive TUI.

    Only the mode comes out; no argument value is kept. Option values are
    skipped by the option's arity, so `codex -C exec` is a TUI in a folder
    named `exec`. The first remaining positional decides: a TUI subcommand,
    another subcommand, or else the TUI's start-up prompt.
    """

    @staticmethod
    def isTui(argv: Sequence[str]) -> bool:
        tIndex = 1
        while tIndex < len(argv):
            tArgument = argv[tIndex]
            if tArgument == CodexCliConstants.END_OF_OPTIONS:
                return True
            if tArgument in CodexCliConstants.EXIT_OPTIONS:
                return False
            if CodexCli._isOption(tArgument):
                tIndex += 1 + CodexCli._valueCount(argv, tIndex)
                continue
            if tArgument in CodexCliConstants.TUI_SUBCOMMANDS:
                return True
            return tArgument not in CodexCliConstants.OTHER_SUBCOMMANDS
        return True

    @staticmethod
    def _isOption(argument: str) -> bool:
        return argument.startswith(CodexCliConstants.OPTION_PREFIX) and argument != CodexCliConstants.OPTION_PREFIX

    @staticmethod
    def _valueCount(argv: Sequence[str], index: int) -> int:
        tOption = argv[index]
        tLong = tOption.startswith(CodexCliConstants.LONG_OPTION_PREFIX)
        if tLong:
            if CodexCliConstants.OPTION_VALUE_SEPARATOR in tOption:
                return 0
            tName = tOption
            tAttached = False
        else:
            tName = tOption[: CodexCliConstants.SHORT_OPTION_LENGTH]
            tAttached = len(tOption) > CodexCliConstants.SHORT_OPTION_LENGTH
        if tName in CodexCliConstants.VALUE_OPTIONS:
            return 0 if tAttached else 1
        if tName in CodexCliConstants.MULTI_VALUE_OPTIONS:
            tCount = 0
            while index + 1 + tCount < len(argv) and not CodexCli._isOption(argv[index + 1 + tCount]):
                tCount += 1
            return tCount
        return 0
