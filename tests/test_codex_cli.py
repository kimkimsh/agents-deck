import unittest

from agents_deck.discovery.codex_cli import CodexCli


class CodexCliTest(unittest.TestCase):
    def testInteractiveForms(self):
        for tArgv in (["codex"], ["codex", "fix the build"], ["codex", "resume", "abc"], ["codex", "-C", "exec"], ["codex", "-c", "k=v", "--model", "m", "hello"], ["codex", "--", "exec"], ["codex", "-i", "a.png", "b.png", "--", "go"], ["codex", "--cd=/x", "fork"]):
            self.assertTrue(CodexCli.isTui(tArgv), tArgv)

    def testOtherModes(self):
        for tArgv in (["codex", "exec", "x"], ["codex", "e", "x"], ["codex", "review"], ["codex", "-c", "k=v", "app-server"], ["codex", "mcp-server"], ["codex", "--version"], ["codex", "-Cdir", "login"], ["codex", "sandbox", "linux"]):
            self.assertFalse(CodexCli.isTui(tArgv), tArgv)


if __name__ == "__main__":
    unittest.main()
