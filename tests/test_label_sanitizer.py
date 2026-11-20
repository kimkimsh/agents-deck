import unittest

from agents_deck.adapters.label_sanitizer import LabelSanitizer


class LabelSanitizerTest(unittest.TestCase):
    def testCollapsesWhitespaceToOneLine(self):
        self.assertEqual(LabelSanitizer().title("my\n  api\tserver\r\n"), "my api server")

    def testClipsWithEllipsisAtTheLimit(self):
        tTitle = LabelSanitizer().title("x" * 100)
        assert tTitle is not None
        self.assertEqual(len(tTitle), 24)
        self.assertTrue(tTitle.endswith("…"))

    def testEmptyOrNonTextIsNone(self):
        self.assertIsNone(LabelSanitizer().title("   \n "))
        self.assertIsNone(LabelSanitizer().title(None))
        self.assertIsNone(LabelSanitizer().title(["a", "list"]))
        self.assertIsNone(LabelSanitizer().title(7))

    def testProcessNameKeepsOnlyFileNameCharacters(self):
        self.assertEqual(LabelSanitizer().processName("cargo"), "cargo")
        self.assertEqual(LabelSanitizer().processName("node-22.1"), "node-22.1")
        self.assertIsNone(LabelSanitizer().processName("rm -rf ~/x"))
        self.assertIsNone(LabelSanitizer().processName(""))


if __name__ == "__main__":
    unittest.main()
