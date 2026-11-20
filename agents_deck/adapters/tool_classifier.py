from typing import Dict, Tuple

from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.tool_category import ToolCategory


class ToolClassifier:
    """Maps an agent's tool name to the prop family the character shows.

    Names come from the agents' own records: Claude tool_use names, Codex
    custom_tool_call/function_call names, Antigravity step types and the
    tool-call names its planner emits before a step exists.
    """

    CLAUDE_TOOLS: Dict[str, ToolCategory] = {
        "Bash": ToolCategory.SHELL,
        "BashOutput": ToolCategory.SHELL,
        "KillShell": ToolCategory.SHELL,
        "Monitor": ToolCategory.SHELL,
        "Read": ToolCategory.SEARCH,
        "Glob": ToolCategory.SEARCH,
        "Grep": ToolCategory.SEARCH,
        "LS": ToolCategory.SEARCH,
        "ToolSearch": ToolCategory.SEARCH,
        "Write": ToolCategory.EDIT,
        "Edit": ToolCategory.EDIT,
        "MultiEdit": ToolCategory.EDIT,
        "NotebookEdit": ToolCategory.EDIT,
        "WebFetch": ToolCategory.WEB,
        "WebSearch": ToolCategory.WEB,
        "Task": ToolCategory.AGENT,
        "Agent": ToolCategory.AGENT,
        "Workflow": ToolCategory.AGENT,
        "SendMessage": ToolCategory.AGENT,
    }

    CODEX_TOOLS: Dict[str, ToolCategory] = {
        "exec": ToolCategory.SHELL,
        "shell": ToolCategory.SHELL,
        "wait": ToolCategory.SHELL,
        "sleep": ToolCategory.SHELL,
        "apply_patch": ToolCategory.EDIT,
        "view_image": ToolCategory.SEARCH,
        "web_search": ToolCategory.WEB,
        "spawn_agent": ToolCategory.AGENT,
        "wait_agent": ToolCategory.AGENT,
        "send_message": ToolCategory.AGENT,
        "followup_task": ToolCategory.AGENT,
        "list_agents": ToolCategory.AGENT,
        "interrupt_agent": ToolCategory.AGENT,
    }

    AGY_STEPS: Dict[str, ToolCategory] = {
        "RUN_COMMAND": ToolCategory.SHELL,
        "VIEW_FILE": ToolCategory.SEARCH,
        "GREP_SEARCH": ToolCategory.SEARCH,
        "LIST_DIRECTORY": ToolCategory.SEARCH,
        "FIND": ToolCategory.SEARCH,
        "CODE_ACTION": ToolCategory.EDIT,
        "WRITE_TO_FILE": ToolCategory.EDIT,
        "READ_URL_CONTENT": ToolCategory.WEB,
        "SEARCH_WEB": ToolCategory.WEB,
        "BROWSER_SUBAGENT": ToolCategory.AGENT,
        "run_command": ToolCategory.SHELL,
        "view_file": ToolCategory.SEARCH,
        "grep_search": ToolCategory.SEARCH,
        "list_dir": ToolCategory.SEARCH,
        "find_by_name": ToolCategory.SEARCH,
        "replace_file_content": ToolCategory.EDIT,
        "write_to_file": ToolCategory.EDIT,
        "read_url_content": ToolCategory.WEB,
        "search_web": ToolCategory.WEB,
    }

    # MCP tool names are free-form (`mcp__<server>__<tool>`); these substrings
    # are the only signal of what they do.
    MCP_WEB_HINTS: Tuple[str, ...] = ("search", "fetch", "scrape", "crawl", "browser", "web")
    MCP_PREFIX = "mcp__"

    def classify(self, agent: AgentKind, name: str) -> ToolCategory:
        if agent is AgentKind.CLAUDE:
            tCategory = self.CLAUDE_TOOLS.get(name)
            if tCategory is not None:
                return tCategory
            if name.startswith(self.MCP_PREFIX):
                return self._classifyMcp(name)
            return ToolCategory.OTHER
        if agent is AgentKind.CODEX:
            return self.CODEX_TOOLS.get(name, ToolCategory.OTHER)
        return self.AGY_STEPS.get(name, ToolCategory.OTHER)

    def _classifyMcp(self, name: str) -> ToolCategory:
        tLower = name.lower()
        for tHint in self.MCP_WEB_HINTS:
            if tHint in tLower:
                return ToolCategory.WEB
        return ToolCategory.OTHER
