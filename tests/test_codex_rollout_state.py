import unittest

from agents_deck.adapters.codex_rollout_state import CodexRolloutState


def event(kind: str, **fields) -> dict:
    tPayload = {"type": kind}
    tPayload.update(fields)
    return {"type": "event_msg", "payload": tPayload}


def response(kind: str, **fields) -> dict:
    tPayload = {"type": kind}
    tPayload.update(fields)
    return {"type": "response_item", "payload": tPayload}


def legacySubagent(threadId: str, kind: str) -> dict:
    return {"type": "event_msg", "payload": {"type": "sub_agent_activity", "agent_thread_id": threadId, "agent_path": "/root/secret-name", "kind": kind}}


class CodexRolloutStateTest(unittest.TestCase):
    def setUp(self):
        self.mState = CodexRolloutState()

    def testTurnWithOneCall(self):
        self.mState.apply(event("task_started"))
        self.assertTrue(self.mState.mTurnActive)
        self.mState.apply(response("function_call", call_id="c1", name="exec_command"))
        self.assertEqual(self.mState.openCallName(), "exec_command")
        self.mState.apply(response("function_call_output", call_id="c1"))
        self.assertIsNone(self.mState.openCallName())
        self.mState.apply(event("task_complete"))
        self.assertFalse(self.mState.mTurnActive)
        self.assertFalse(self.mState.mTurnError)

    def testFailedTurnIsAnError(self):
        self.mState.apply(event("task_started"))
        self.mState.apply(event("task_complete", error="boom"))
        self.assertTrue(self.mState.mTurnError)

    def testAbortClosesTurnAndCalls(self):
        self.mState.apply(event("task_started"))
        self.mState.apply(response("custom_tool_call", call_id="c1", name="apply_patch"))
        self.mState.apply(event("turn_aborted"))
        self.assertFalse(self.mState.mTurnActive)
        self.assertIsNone(self.mState.openCallName())

    def testAbortWithAnErrorIsAnError(self):
        self.mState.apply(event("task_started"))
        self.mState.apply(event("turn_aborted", error="stream closed"))
        self.assertTrue(self.mState.mTurnError)
        self.mState.apply(event("task_started"))
        self.mState.apply(event("turn_aborted", reason="interrupted"))
        self.assertFalse(self.mState.mTurnError)

    def testSubagentLifecycleAcrossBothEventForms(self):
        # Legacy history writes every kind but `completed` as sub_agent_activity.
        self.mState.apply(legacySubagent("s1", "started"))
        self.assertIsNone(self.mState.mSubagents["s1"].mProcessName)
        self.assertNotIn("secret-name", repr(self.mState.mSubagents))
        self.mState.apply(legacySubagent("s1", "interacted"))
        self.assertIn("s1", self.mState.mSubagents)
        self.mState.apply(event("item_completed", item={"type": "SubAgentActivity", "agent_thread_id": "s1", "kind": "completed"}))
        self.assertNotIn("s1", self.mState.mSubagents)

    def testOpenCallsAreQueryableByName(self):
        self.mState.apply(event("task_started"))
        self.mState.apply(response("function_call", call_id="q", name="request_user_input"))
        self.mState.apply(response("function_call", call_id="c", name="exec_command"))
        self.assertTrue(self.mState.hasOpenCall("request_user_input"))
        self.assertEqual(self.mState.openCallName(), "exec_command")

    def testUnknownRecordsAreNotRecognized(self):
        self.mState.apply({"type": "session_meta", "payload": {"type": "x"}})
        self.mState.apply({"type": "event_msg", "payload": "not a dict"})
        self.assertEqual(self.mState.mRecognized, 0)
