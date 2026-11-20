import os
from typing import BinaryIO, List, Optional, Sequence, Tuple

from agents_deck.adapters.tail_batch import TailBatch


class LineTail:
    """Incremental reader of one append-only, newline-framed file.

    On attach, reading starts at the beginning of the record that holds the
    point `initialWindowBytes` before the end. The earlier lines that contain
    one of `prefixNeedles` come back once, in the same batch, so the owner can
    rebuild state without parsing every line before the window. Only
    newline-terminated lines are returned; a line the writer is still
    appending comes back whole on a later call.

    One call reads at most `maxReadBytes`. A record longer than that is
    skipped through its newline, over as many calls as it takes, so a single
    huge record cannot stall the file; the owner's state recovers at the next
    record that carries it. Each call works from one open descriptor, so the
    attach point, the prefix and the new lines all belong to one file
    generation, and the cursor moves only after the whole read succeeded. A
    shrink or an inode change means the file was replaced: the next call
    attaches again and reports mWasReset.

    Owned by the collector thread; not thread-safe.
    """

    SCAN_BLOCK_BYTES = 1024 * 1024
    LINE_BREAK = b"\n"

    mPath: str
    mInitialWindowBytes: int
    mMaxReadBytes: int
    mPrefixNeedles: Tuple[bytes, ...]
    mOffset: int
    mInode: Optional[int]
    mDiscarding: bool

    def __init__(self, path: str, initialWindowBytes: int, maxReadBytes: int, prefixNeedles: Sequence[bytes]):
        self.mPath = path
        self.mInitialWindowBytes = initialWindowBytes
        self.mMaxReadBytes = maxReadBytes
        self.mPrefixNeedles = tuple(prefixNeedles)
        self.mOffset = 0
        self.mInode = None
        self.mDiscarding = False

    def readNew(self) -> Optional[TailBatch]:
        """Lines appended since the last call; None when the file cannot be read."""
        try:
            with open(self.mPath, "rb") as tFile:
                return self._read(tFile)
        except OSError:
            return None

    def _read(self, file: BinaryIO) -> TailBatch:
        tStat = os.fstat(file.fileno())
        tReset = self.mInode is None or tStat.st_ino != self.mInode or tStat.st_size < self.mOffset
        tOffset = self.mOffset
        tDiscarding = self.mDiscarding
        tPrefix: Tuple[bytes, ...] = ()
        if tReset:
            tOffset = self._attachPoint(file, tStat.st_size)
            tDiscarding = False
            tPrefix = tuple(self._scanPrefix(file, tOffset))
        tLines, tOffset, tDiscarding = self._readLines(file, tOffset, tStat.st_size, tDiscarding)
        self.mInode = tStat.st_ino
        self.mOffset = tOffset
        self.mDiscarding = tDiscarding
        return TailBatch(mWasReset=tReset, mPrefix=tPrefix, mLines=tLines)

    def _readLines(self, file: BinaryIO, offset: int, size: int, discarding: bool) -> Tuple[Tuple[bytes, ...], int, bool]:
        """(complete lines, new offset, still discarding) for one bounded read."""
        if size <= offset:
            return (), offset, discarding
        file.seek(offset)
        tChunk = file.read(min(self.mMaxReadBytes, size - offset))
        tStart = 0
        if discarding:
            tBreak = tChunk.find(self.LINE_BREAK)
            if tBreak < 0:
                return (), offset + len(tChunk), True
            tStart = tBreak + 1
        tEnd = tChunk.rfind(self.LINE_BREAK)
        if tEnd < tStart:
            if tStart == 0 and len(tChunk) == self.mMaxReadBytes:
                return (), offset + len(tChunk), True
            return (), offset + tStart, False
        return tuple(tChunk[tStart:tEnd].split(self.LINE_BREAK)), offset + tEnd + 1, False

    def _attachPoint(self, file: BinaryIO, size: int) -> int:
        if size <= self.mInitialWindowBytes:
            return 0
        tProbe = size - self.mInitialWindowBytes
        tForward = self._nextLineStart(file, tProbe)
        if tForward is not None:
            return tForward
        # The record spanning the probe is still being written: start at its
        # beginning so it is read whole once finished.
        return self._lineStartBefore(file, tProbe)

    def _nextLineStart(self, file: BinaryIO, probe: int) -> Optional[int]:
        tPosition = probe - 1
        file.seek(tPosition)
        while True:
            tBlock = file.read(self.SCAN_BLOCK_BYTES)
            if not tBlock:
                return None
            tBreak = tBlock.find(self.LINE_BREAK)
            if tBreak >= 0:
                return tPosition + tBreak + 1
            tPosition += len(tBlock)

    def _lineStartBefore(self, file: BinaryIO, probe: int) -> int:
        tEnd = probe
        while tEnd > 0:
            tStart = max(0, tEnd - self.SCAN_BLOCK_BYTES)
            file.seek(tStart)
            tBlock = file.read(tEnd - tStart)
            tBreak = tBlock.rfind(self.LINE_BREAK)
            if tBreak >= 0:
                return tStart + tBreak + 1
            tEnd = tStart
        return 0

    def _scanPrefix(self, file: BinaryIO, end: int) -> List[bytes]:
        """Lines before `end` containing a needle; lines over maxReadBytes are skipped."""
        if not self.mPrefixNeedles or end == 0:
            return []
        file.seek(0)
        tResult: List[bytes] = []
        tRemaining = end
        tCarry = b""
        tSkipping = False
        while tRemaining > 0:
            tBlock = file.read(min(self.SCAN_BLOCK_BYTES, tRemaining))
            if not tBlock:
                break
            tRemaining -= len(tBlock)
            tParts = (tCarry + tBlock).split(self.LINE_BREAK)
            tCarry = tParts.pop()
            if tSkipping:
                if not tParts:
                    tCarry = b""
                    continue
                tParts = tParts[1:]
                tSkipping = False
            for tLine in tParts:
                if any(tNeedle in tLine for tNeedle in self.mPrefixNeedles):
                    tResult.append(tLine)
            if len(tCarry) > self.mMaxReadBytes:
                tCarry = b""
                tSkipping = True
        return tResult
