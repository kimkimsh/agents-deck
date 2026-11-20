from typing import Dict, List, Sequence, Set, Tuple

from agents_deck.constants.layout_constants import LayoutConstants


class TileOrder:
    """The user's tile order, keyed by pane id.

    Panes are never dropped because they are gone right now (a Warp restart
    keeps pane ids); the remembered list is capped instead, forgetting the
    absent panes seen least recently first. A live pane is never forgotten,
    so with more live panes than the cap the list holds just those. UI
    thread only.
    """

    mOrder: List[str]
    mLastSeen: Dict[str, float]

    def __init__(self, order: Sequence[str]):
        self.mOrder = list(order)
        self.mLastSeen = {}

    def arrange(self, livePanes: Sequence[str], now: float) -> List[str]:
        """Live panes in display order; panes not seen before go last."""
        for tPane in livePanes:
            self.mLastSeen[tPane] = now
            if tPane not in self.mOrder:
                self.mOrder.append(tPane)
        tLive = set(livePanes)
        self._cap(tLive)
        return [tPane for tPane in self.mOrder if tPane in tLive]

    def move(self, pane: str, targetIndex: int, displayed: Sequence[str]):
        """Moves `pane` to `targetIndex` among the displayed panes."""
        tDisplayed = [tPane for tPane in displayed if tPane != pane]
        tDisplayed.insert(min(max(targetIndex, 0), len(tDisplayed)), pane)
        tShown = set(tDisplayed)
        self.mOrder = tDisplayed + [tPane for tPane in self.mOrder if tPane not in tShown]

    def reset(self):
        self.mOrder = []
        self.mLastSeen = {}

    def order(self) -> Tuple[str, ...]:
        return tuple(self.mOrder)

    def _cap(self, live: Set[str]):
        tExcess = len(self.mOrder) - LayoutConstants.ORDER_CAP
        if tExcess <= 0:
            return
        tAbsent = sorted((tPane for tPane in self.mOrder if tPane not in live), key=self._lastSeen)
        tForgotten = set(tAbsent[:tExcess])
        self.mOrder = [tPane for tPane in self.mOrder if tPane not in tForgotten]
        for tPane in tForgotten:
            self.mLastSeen.pop(tPane, None)

    def _lastSeen(self, pane: str) -> float:
        return self.mLastSeen.get(pane, 0.0)
