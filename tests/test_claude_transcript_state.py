import unittest

from agents_deck.adapters.claude_transcript_state import ClaudeTranscriptState
from agents_deck.model.background_kind import BackgroundKind


def toolUse(toolId: str, name: str, description: str) -> dict:
    return {"type": "assistant", "message": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": toolId, "name": name, "input": {"description": description}}]}}


def toolResult(toolId: str, result: dict) -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": toolId}]}, "toolUseResult": result}


def notification(taskId: str, status: str) -> dict:
    return {"type": "queue-operation", "operation": "enqueue", "content": "<task-notification><task-id>%s</task-id><status>%s</status></task-notification>" % (taskId, status)}


class ClaudeTranscriptStateTest(unittest.TestCase):
    def setUp(self):
        self.mState = ClaudeTranscriptState()

    def launchShell(self, taskId: str):
        self.mState.apply(toolUse("tu-" + taskId, "Bash", "Run the full suite"))
        self.mState.apply(toolResult("tu-" + taskId, {"backgroundTaskId": taskId}))

    def testBackgroundShellOpensWithoutItsDescription(self):
        self.launchShell("b1")
        tTask = self.mState.mBackground["b1"]
        self.assertEqual(tTask.mKind, BackgroundKind.SHELL)
        self.assertIsNone(tTask.mProcessName)
        self.assertNotIn("Run the full suite", repr(vars(self.mState)))
        self.assertIsNone(self.mState.openToolName())

    def testTerminalNotificationClosesTask(self):
        self.launchShell("b1")
        self.mState.apply(notification("b1", "running"))
        self.assertIn("b1", self.mState.mBackground)
        self.mState.apply(notification("b1", "completed"))
        self.assertNotIn("b1", self.mState.mBackground)

    def testTaskStopResultClosesTask(self):
        self.launchShell("b1")
        self.mState.apply(toolUse("tu-stop", "TaskStop", ""))
        self.mState.apply(toolResult("tu-stop", {"task_id": "b1", "task_type": "local_bash", "command": "x", "message": "stopped"}))
        self.assertNotIn("b1", self.mState.mBackground)

    def testTaskShapedResultOfAnotherToolDoesNotCloseTask(self):
        self.launchShell("b1")
        self.mState.apply(toolUse("tu-out", "TaskOutput", ""))
        self.mState.apply(toolResult("tu-out", {"task_id": "b1", "task_type": "local_bash", "status": "running"}))
        self.assertIn("b1", self.mState.mBackground)

    def testClosedTaskDoesNotReopenOnReplay(self):
        self.launchShell("b1")
        self.mState.apply(notification("b1", "killed"))
        self.launchShell("b1")
        self.assertNotIn("b1", self.mState.mBackground)

    def testAsyncAgentLaunchOpensAgentTask(self):
        self.mState.apply(toolUse("tu-a", "Agent", "Review the diff"))
        self.mState.apply(toolResult("tu-a", {"isAsync": True, "status": "async_launched", "agentId": "b42", "description": "Review the diff"}))
        self.assertEqual(self.mState.mBackground["b42"].mKind, BackgroundKind.AGENT)
        self.assertNotIn("Review the diff", repr(vars(self.mState)))

    def testOpenToolIsTheNewestUnanswered(self):
        self.mState.apply(toolUse("tu-1", "Read", ""))
        self.assertEqual(self.mState.openToolName(), "Read")
        self.mState.apply(toolResult("tu-1", {}))
        self.assertIsNone(self.mState.openToolName())

    def testNewPromptClearsCallsAnInterruptLeftOpen(self):
        self.mState.apply(toolUse("tu-1", "Bash", ""))
        self.mState.apply({"type": "user", "message": {"content": "next question"}})
        self.assertIsNone(self.mState.openToolName())

    def testEndPrefixKeepsBackgroundButDropsForeground(self):
        self.launchShell("b1")
        self.mState.apply(toolUse("tu-2", "Edit", ""))
        self.mState.endPrefix()
        self.assertIn("b1", self.mState.mBackground)
        self.assertIsNone(self.mState.openToolName())

    def testSidechainRecordsAreIgnored(self):
        tRecord = toolUse("tu-s", "Bash", "")
        tRecord["isSidechain"] = True
        self.mState.apply(tRecord)
        self.assertIsNone(self.mState.openToolName())
