from typing import Dict, List, Optional, Sequence, Set, Tuple

from agents_deck.adapters.codex_link import CodexLink
from agents_deck.adapters.codex_tui import CodexTui
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.model.link_confidence import LinkConfidence


class CodexLinkResolver:
    """Guesses which thread each Codex TUI is showing, one marker change at a time.

    Signal: the first time a TUI process learns of a thread it writes the
    empty file `~/.codex/tui-thread-reference-capabilities/<thread>`; only the
    mtime carries information. That happens on start, `resume` and in-app
    `/new`, but also for threads a dynamic tool starts without the TUI
    showing them, and never again for a thread the process already wrote
    (so an in-app switch back to an earlier thread leaves no trace). The
    newest marker credited to a TUI is therefore a guess, never proof: a link
    is INFERRED at best.

    A marker change is credited, when first seen, to the one TUI that was
    alive at its mtime. Among several, a TUI inside its own start-up window
    that has not yet taken a marker takes it (a fresh TUI writes its first
    marker within seconds; the others keep their links); otherwise the thread's folder may single one
    out; otherwise every candidate becomes unknown until its next change.
    Each decision is made once and kept, so a TUI that exits and is forgotten
    later cannot hand its old markers to a survivor.

    Before the app started, TUIs that have since exited are invisible, so an
    old marker is trusted only inside a TUI's own start-up window, or by
    folder. Owned by the collector thread.
    """

    mSeen: Dict[str, float]
    mLinks: Dict[Tuple[int, int], CodexLink]
    mStarted: Set[Tuple[int, int]]

    def __init__(self):
        self.mSeen = {}
        self.mLinks = {}
        self.mStarted = set()

    def update(
        self,
        tuis: Sequence[CodexTui],
        markers: Sequence[Tuple[str, float]],
        threadCwds: Dict[str, str],
        appStartTime: float,
    ) -> Dict[Tuple[int, int], CodexLink]:
        tNew = [tMarker for tMarker in markers if self.mSeen.get(tMarker[0]) != tMarker[1]]
        self.mSeen = dict(markers)
        for tThreadId, tWhen in sorted(tNew, key=self._markerTime):
            self._decide(tuis, tThreadId, tWhen, threadCwds.get(tThreadId), tWhen < appStartTime)
        tLive = {self._key(tTui) for tTui in tuis}
        self.mLinks = {tKey: tLink for tKey, tLink in self.mLinks.items() if tKey in tLive}
        self.mStarted &= tLive
        return {tKey: self.mLinks.get(tKey, self.unknown()) for tKey in tLive}

    @staticmethod
    def unknown() -> CodexLink:
        return CodexLink(mThreadId=None, mConfidence=LinkConfidence.UNKNOWN)

    def _decide(self, tuis: Sequence[CodexTui], threadId: str, when: float, threadCwd: Optional[str], preStart: bool):
        tCandidates = self._candidates(tuis, when, preStart)
        if not tCandidates:
            return
        tStarting = [tTui for tTui in tCandidates if self._key(tTui) not in self.mStarted and self._inStartupWindow(tTui, when)]
        if len(tStarting) == 1:
            self.mStarted.add(self._key(tStarting[0]))
            self._credit(tStarting[0], threadId)
            return
        tByCwd = [tTui for tTui in tCandidates if threadCwd is not None and tTui.mCwd == threadCwd]
        if len(tByCwd) == 1:
            self._credit(tByCwd[0], threadId)
            return
        if len(tCandidates) == 1 and not preStart:
            self._credit(tCandidates[0], threadId)
            return
        if len(tCandidates) > 1:
            for tTui in tCandidates:
                self.mLinks[self._key(tTui)] = self.unknown()

    def _credit(self, tui: CodexTui, threadId: str):
        self.mLinks[self._key(tui)] = CodexLink(mThreadId=threadId, mConfidence=LinkConfidence.INFERRED)

    @staticmethod
    def _inStartupWindow(tui: CodexTui, when: float) -> bool:
        return when <= tui.mStartTime + TimingConstants.CODEX_ATTACH_WINDOW_SECONDS

    @staticmethod
    def _candidates(tuis: Sequence[CodexTui], when: float, preStart: bool) -> List[CodexTui]:
        tResult = []
        for tTui in tuis:
            if when < tTui.mStartTime - TimingConstants.CODEX_LINK_SLACK_SECONDS:
                continue
            if preStart:
                if not tTui.mAliveAtAppStart:
                    continue
            elif tTui.mEndTime is not None and when > tTui.mEndTime:
                continue
            tResult.append(tTui)
        return tResult

    @staticmethod
    def _key(tui: CodexTui) -> Tuple[int, int]:
        return (tui.mPid, tui.mStartTicks)

    @staticmethod
    def _markerTime(marker: Tuple[str, float]) -> float:
        return marker[1]
