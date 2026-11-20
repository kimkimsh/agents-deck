import json
import os
import tempfile
import unittest
from typing import List

from agents_deck.adapters.json_record import JsonRecord
from agents_deck.adapters.line_tail import LineTail
from agents_deck.adapters.tail_batch import TailBatch


class LineTailTest(unittest.TestCase):
    WINDOW = 64
    MAX_READ = 1024
    SMALL_READ = 64
    NEEDLE = b"backgroundTaskId"

    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mPath = os.path.join(self.mDir.name, "t.jsonl")

    def tearDown(self):
        os.chmod(self.mDir.name, 0o700)
        if os.path.exists(self.mPath):
            os.chmod(self.mPath, 0o600)
        self.mDir.cleanup()

    def append(self, text: str):
        with open(self.mPath, "a", encoding="utf-8") as tFile:
            tFile.write(text)

    def line(self, index: int) -> str:
        return json.dumps({"i": index}) + "\n"

    def tail(self, maxRead: int) -> LineTail:
        return LineTail(self.mPath, self.WINDOW, maxRead, (self.NEEDLE,))

    def read(self, tail: LineTail) -> TailBatch:
        tBatch = tail.readNew()
        assert tBatch is not None
        return tBatch

    def records(self, batch: TailBatch) -> List[dict]:
        return JsonRecord.parseAll(batch.mLines)

    def testMissingFileIsUnreadable(self):
        self.assertIsNone(self.tail(self.MAX_READ).readNew())

    def testPartialLineIsReadWhenFinished(self):
        self.append('{"i": 1}\n{"i": ')
        tTail = self.tail(self.MAX_READ)
        self.assertEqual(self.records(self.read(tTail)), [{"i": 1}])
        self.append('2}\n')
        self.assertEqual(self.records(self.read(tTail)), [{"i": 2}])
        self.assertEqual(self.records(self.read(tTail)), [])

    def testAttachStartsOnALineBoundaryInsideTheWindow(self):
        for tIndex in range(20):
            self.append(self.line(tIndex))
        tBatch = self.read(self.tail(self.MAX_READ))
        tRecords = self.records(tBatch)
        self.assertTrue(tBatch.mWasReset)
        self.assertEqual(tRecords[-1], {"i": 19})
        self.assertNotIn({"i": 0}, tRecords)
        self.assertEqual(len(tRecords), len(tBatch.mLines))

    def testPrefixHoldsOnlyNeedleLinesBeforeTheWindow(self):
        self.append(json.dumps({"kind": "launch", "backgroundTaskId": "b1"}) + "\n")
        for tIndex in range(20):
            self.append(self.line(tIndex))
        tBatch = self.read(self.tail(self.MAX_READ))
        self.assertEqual(JsonRecord.parseAll(tBatch.mPrefix), [{"kind": "launch", "backgroundTaskId": "b1"}])

    def testPrefixComesOnlyWithTheResetBatch(self):
        self.append(json.dumps({"backgroundTaskId": "b1"}) + "\n")
        for tIndex in range(20):
            self.append(self.line(tIndex))
        tTail = self.tail(self.MAX_READ)
        self.read(tTail)
        self.append(self.line(20))
        tBatch = self.read(tTail)
        self.assertFalse(tBatch.mWasReset)
        self.assertEqual(tBatch.mPrefix, ())

    def testAttachInsideAnUnfinishedRecordReadsItWholeLater(self):
        self.append(self.line(1))
        tLong = json.dumps({"i": 2, "pad": "x" * (2 * self.WINDOW)})
        self.append(tLong[: len(tLong) - 4])
        tTail = self.tail(self.MAX_READ)
        self.assertEqual(self.records(self.read(tTail)), [])
        self.append(tLong[len(tLong) - 4:] + "\n")
        self.assertEqual(self.records(self.read(tTail)), [json.loads(tLong)])

    def testRecordLongerThanOneReadIsSkippedAndReadingContinues(self):
        self.append(self.line(1))
        tTail = self.tail(self.SMALL_READ)
        self.assertEqual(self.records(self.read(tTail)), [{"i": 1}])
        self.append(json.dumps({"pad": "x" * (3 * self.SMALL_READ)}) + "\n" + self.line(2))
        tSeen = []
        for _ in range(8):
            tSeen += self.records(self.read(tTail))
        self.assertEqual(tSeen, [{"i": 2}])

    def testReplacedFileResets(self):
        self.append(self.line(1))
        tTail = self.tail(self.MAX_READ)
        self.read(tTail)
        # Replaced by rename: both files exist at once, so the inode differs.
        tNew = self.mPath + ".new"
        with open(tNew, "w", encoding="utf-8") as tFile:
            tFile.write(self.line(2))
        os.replace(tNew, self.mPath)
        tBatch = self.read(tTail)
        self.assertEqual(self.records(tBatch), [{"i": 2}])
        self.assertTrue(tBatch.mWasReset)

    def testResetSurvivesAFailedOpen(self):
        self.append(self.line(1))
        tTail = self.tail(self.MAX_READ)
        self.read(tTail)
        tNew = self.mPath + ".new"
        with open(tNew, "w", encoding="utf-8") as tFile:
            tFile.write(self.line(2))
        os.replace(tNew, self.mPath)
        os.chmod(self.mPath, 0)
        self.assertIsNone(tTail.readNew())
        os.chmod(self.mPath, 0o600)
        tBatch = self.read(tTail)
        self.assertTrue(tBatch.mWasReset)
        self.assertEqual(self.records(tBatch), [{"i": 2}])

    def testTruncatedFileResets(self):
        self.append(self.line(1) + self.line(2))
        tTail = self.tail(self.MAX_READ)
        self.read(tTail)
        with open(self.mPath, "w", encoding="utf-8") as tFile:
            tFile.write(self.line(3))
        tBatch = self.read(tTail)
        self.assertEqual(self.records(tBatch), [{"i": 3}])
        self.assertTrue(tBatch.mWasReset)

    def testMalformedLinesAreSkipped(self):
        self.append('not json\n[1, 2]\n{"i": 5}\n')
        self.assertEqual(self.records(self.read(self.tail(self.MAX_READ))), [{"i": 5}])


if __name__ == "__main__":
    unittest.main()
