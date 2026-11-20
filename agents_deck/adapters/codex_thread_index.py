import glob
import os
import sqlite3
import time
from typing import Collection, Dict, Iterable, List, Optional, Set, Tuple

from agents_deck.constants.codex_constants import CodexConstants
from agents_deck.constants.timing_constants import TimingConstants


class CodexThreadIndex:
    """Read-only lookups into Codex's on-disk thread state.

    - attach markers: (thread id, mtime) from the TUI marker directory;
    - thread rows from state_5.sqlite: cwd and rollout path, selected by id
      only (title and first-message columns are never read);
    - rollout path fallback by file name, because a thread has no row until
      its first turn is persisted.

    Rows are cached once found, since a thread's cwd and rollout path do not
    change, and dropped once the thread's marker is no longer in the poll's
    time range. Owned by the collector thread.
    """

    mMarkerDir: str
    mSessionsDir: str
    mStateDbPath: str
    mCwds: Dict[str, str]
    mRollouts: Dict[str, str]
    mSubagentThreads: Set[str]

    def __init__(self, markerDir: str, sessionsDir: str, stateDbPath: str):
        self.mMarkerDir = markerDir
        self.mSessionsDir = sessionsDir
        self.mStateDbPath = stateDbPath
        self.mCwds = {}
        self.mRollouts = {}
        self.mSubagentThreads = set()

    def markersSince(self, since: float) -> List[Tuple[str, float]]:
        try:
            tNames = os.listdir(self.mMarkerDir)
        except OSError:
            return []
        tResult = []
        for tName in tNames:
            if not CodexConstants.THREAD_ID_PATTERN.fullmatch(tName):
                continue
            try:
                tMtime = os.stat(os.path.join(self.mMarkerDir, tName)).st_mtime
            except OSError:
                continue
            if tMtime >= since:
                tResult.append((tName, tMtime))
        return tResult

    def retain(self, threadIds: Collection[str]):
        """Forgets every cached thread not in `threadIds`."""
        self.mCwds = {tId: tCwd for tId, tCwd in self.mCwds.items() if tId in threadIds}
        self.mRollouts = {tId: tPath for tId, tPath in self.mRollouts.items() if tId in threadIds}
        self.mSubagentThreads &= set(threadIds)

    def isSubagent(self, threadId: str) -> bool:
        return threadId in self.mSubagentThreads

    def hasRow(self, threadId: str) -> bool:
        return threadId in self.mCwds

    def refreshRows(self, threadIds: Iterable[str]):
        tMissing = [tId for tId in threadIds if tId not in self.mCwds]
        if not tMissing:
            return
        try:
            tConnection = sqlite3.connect("file:%s?mode=ro" % self.mStateDbPath, uri=True, timeout=CodexConstants.SQLITE_TIMEOUT_SECONDS)
        except sqlite3.Error:
            return
        try:
            tPlaceholders = ",".join("?" for _ in tMissing)
            tRows = tConnection.execute(
                "SELECT id, cwd, rollout_path, source FROM threads WHERE id IN (%s)" % tPlaceholders, tMissing
            ).fetchall()
        except sqlite3.Error:
            return
        finally:
            tConnection.close()
        for tId, tCwd, tRolloutPath, tSource in tRows:
            if isinstance(tSource, str) and tSource.startswith(CodexConstants.SUBAGENT_SOURCE_PREFIX):
                self.mSubagentThreads.add(tId)
            if isinstance(tCwd, str):
                self.mCwds[tId] = os.path.realpath(tCwd)
            if isinstance(tRolloutPath, str) and tRolloutPath:
                self.mRollouts[tId] = tRolloutPath

    def cwds(self) -> Dict[str, str]:
        return self.mCwds

    def rolloutPath(self, threadId: str) -> Optional[str]:
        tKnown = self.mRollouts.get(threadId)
        if tKnown is not None:
            return tKnown
        tFound = self._globRollout(threadId)
        if tFound is not None:
            self.mRollouts[threadId] = tFound
        return tFound

    def _globRollout(self, threadId: str) -> Optional[str]:
        tCreated = self.threadCreatedAt(threadId)
        if tCreated is None:
            return None
        # Rollouts sit under the local date the thread started on; check the
        # neighbouring days for time-zone edges.
        for tOffsetDays in (0, -1, 1):
            tDay = time.strftime(CodexConstants.ROLLOUT_DATE_DIR_FORMAT, time.localtime(tCreated + tOffsetDays * CodexConstants.SECONDS_PER_DAY))
            tPattern = os.path.join(glob.escape(os.path.join(self.mSessionsDir, tDay)), CodexConstants.ROLLOUT_FILE_GLOB % glob.escape(threadId))
            tMatches = glob.glob(tPattern)
            if tMatches:
                return tMatches[0]
        return None

    @staticmethod
    def threadCreatedAt(threadId: str) -> Optional[float]:
        tHex = threadId.replace("-", "")[: CodexConstants.UUID7_TIME_HEX_CHARS]
        try:
            return int(tHex, 16) / TimingConstants.MS_PER_SECOND
        except ValueError:
            return None
