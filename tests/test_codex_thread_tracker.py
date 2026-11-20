import json
import os
import tempfile
import unittest

from agents_deck.adapters.codex_thread_tracker import CodexThreadTracker
from agents_deck.constants.tail_constants import TailConstants


class CodexThreadTrackerTest(unittest.TestCase):
    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mPath = os.path.join(self.mDir.name, "rollout.jsonl")

    def tearDown(self):
        self.mDir.cleanup()

    def write(self, records):
        with open(self.mPath, "a", encoding="utf-8") as tFile:
            for tRecord in records:
                tFile.write(json.dumps(tRecord, separators=(",", ":")) + "\n")

    def testCallOpenedBeforeTheAttachWindowStaysOpen(self):
        self.write([
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "response_item", "payload": {"type": "function_call", "call_id": "c1", "name": "exec_command"}},
        ])
        tFiller = {"type": "event_msg", "payload": {"type": "token_count", "pad": "x" * 1024}}
        self.write([tFiller] * (TailConstants.INITIAL_WINDOW_BYTES // 1024 + 16))
        tTracker = CodexThreadTracker(self.mPath)
        self.assertTrue(tTracker.update())
        self.assertTrue(tTracker.state().mTurnActive)
        self.assertEqual(tTracker.state().openCallName(), "exec_command")


if __name__ == "__main__":
    unittest.main()
