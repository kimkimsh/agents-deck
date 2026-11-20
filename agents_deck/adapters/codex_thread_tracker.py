from agents_deck.adapters.codex_rollout_state import CodexRolloutState
from agents_deck.adapters.json_record import JsonRecord
from agents_deck.adapters.line_tail import LineTail
from agents_deck.constants.codex_constants import CodexConstants
from agents_deck.constants.tail_constants import TailConstants


class CodexThreadTracker:
    """Follows the rollout file of one Codex thread. Owned by the collector thread."""

    mTail: LineTail
    mState: CodexRolloutState
    mRecordsSeen: int

    def __init__(self, rolloutPath: str):
        self.mTail = LineTail(rolloutPath, TailConstants.INITIAL_WINDOW_BYTES, TailConstants.MAX_READ_BYTES_PER_POLL, CodexConstants.STATE_NEEDLES)
        self.mState = CodexRolloutState()
        self.mRecordsSeen = 0

    def update(self) -> bool:
        tBatch = self.mTail.readNew()
        if tBatch is None:
            return False
        if tBatch.mWasReset:
            self.mState.reset()
            self.mRecordsSeen = 0
            for tRecord in JsonRecord.parseAll(tBatch.mPrefix):
                self.mRecordsSeen += 1
                self.mState.apply(tRecord)
        tRecords = JsonRecord.parseAll(tBatch.mLines)
        self.mRecordsSeen += len(tRecords)
        for tRecord in tRecords:
            self.mState.apply(tRecord)
        return True

    def state(self) -> CodexRolloutState:
        return self.mState

    def formatUnrecognized(self) -> bool:
        """Records exist but none had a known shape: the rollout format moved."""
        return self.mRecordsSeen > 0 and self.mState.mRecognized == 0
