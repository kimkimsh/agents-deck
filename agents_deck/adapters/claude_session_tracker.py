import glob
import os
from typing import Optional

from agents_deck.adapters.claude_transcript_state import ClaudeTranscriptState
from agents_deck.adapters.json_record import JsonRecord
from agents_deck.adapters.line_tail import LineTail
from agents_deck.constants.claude_constants import ClaudeConstants
from agents_deck.constants.path_constants import PathConstants
from agents_deck.constants.tail_constants import TailConstants


class ClaudeSessionTracker:
    """Follows the transcript of one Claude Code process.

    Background tasks can be launched long before the tail window, so on
    attach the earlier part of the file is scanned for task launch and
    completion records only. The session id can change during the process
    lifetime (/clear starts a new session); a change discards everything
    derived from the old one. Owned by the collector thread.
    """

    mProjectsDir: str
    mSessionId: Optional[str]
    mTranscriptPath: Optional[str]
    mTail: Optional[LineTail]
    mState: ClaudeTranscriptState

    def __init__(self, projectsDir: str):
        self.mProjectsDir = projectsDir
        self.mSessionId = None
        self.mTranscriptPath = None
        self.mTail = None
        self.mState = ClaudeTranscriptState()

    def update(self, sessionId: str) -> bool:
        """Reads new transcript records; False when the transcript is not readable."""
        if sessionId != self.mSessionId:
            self.mSessionId = sessionId
            self.mTranscriptPath = None
            self.mTail = None
            self.mState.reset()
        tTail = self.mTail
        if tTail is None:
            self.mTranscriptPath = self._findTranscript(sessionId)
            if self.mTranscriptPath is None:
                return False
            tTail = LineTail(self.mTranscriptPath, TailConstants.INITIAL_WINDOW_BYTES, TailConstants.MAX_READ_BYTES_PER_POLL, ClaudeConstants.BACKGROUND_NEEDLES)
            self.mTail = tTail
        tBatch = tTail.readNew()
        if tBatch is None:
            return False
        if tBatch.mWasReset:
            self.mState.reset()
            for tRecord in JsonRecord.parseAll(tBatch.mPrefix):
                self.mState.apply(tRecord)
            self.mState.endPrefix()
        for tRecord in JsonRecord.parseAll(tBatch.mLines):
            self.mState.apply(tRecord)
        return True

    def state(self) -> ClaudeTranscriptState:
        return self.mState

    def _findTranscript(self, sessionId: str) -> Optional[str]:
        tMatches = glob.glob(os.path.join(glob.escape(self.mProjectsDir), "*", glob.escape(sessionId) + PathConstants.CLAUDE_TRANSCRIPT_SUFFIX))
        if not tMatches:
            return None
        return max(tMatches, key=self._mtimeOrZero)

    @staticmethod
    def _mtimeOrZero(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0
