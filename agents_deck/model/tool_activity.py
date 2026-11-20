from dataclasses import dataclass

from agents_deck.model.tool_category import ToolCategory


@dataclass(frozen=True)
class ToolActivity:
    mName: str
    mCategory: ToolCategory
