import json
import os
import stat
import tempfile
import unittest

from agents_deck.settings.settings import Settings
from agents_deck.settings.settings_store import SettingsStore
from agents_deck.settings.shelf_mode import ShelfMode
from agents_deck.settings.theme_choice import ThemeChoice

PANE_A = "a" * 32
PANE_B = "b" * 32


class SettingsStoreTest(unittest.TestCase):
    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mPath = os.path.join(self.mDir.name, "agents-deck", "settings.json")
        self.mStore = SettingsStore(self.mPath)

    def tearDown(self):
        self.mDir.cleanup()

    def writeRaw(self, raw):
        os.makedirs(os.path.dirname(self.mPath), exist_ok=True)
        with open(self.mPath, "w", encoding="utf-8") as tFile:
            tFile.write(raw if isinstance(raw, str) else json.dumps(raw))

    def testMissingFileGivesDefaultsWithoutANote(self):
        self.assertEqual(self.mStore.load(), (Settings.defaults(), None))

    def testRoundTripIsPrivate(self):
        tSettings = Settings(mColumns=3, mRows=2, mScale=5, mShelfMode=ShelfMode.ALWAYS, mShowNames=True, mTheme=ThemeChoice.DARK, mOrder=(PANE_A, PANE_B), mPosition=(10, -20), mFirstRunDone=True)
        self.mStore.save(tSettings)
        self.assertEqual(self.mStore.load(), (tSettings, None))
        self.assertEqual(stat.S_IMODE(os.stat(self.mPath).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(self.mPath)).st_mode), 0o700)
        self.assertEqual(os.listdir(os.path.dirname(self.mPath)), ["settings.json"])

    def testFailedSaveLeavesNoTemporaryFile(self):
        self.mStore.save(Settings.defaults())
        tBroken = Settings(mColumns=3, mRows=2, mScale=5, mShelfMode=ShelfMode.ALWAYS, mShowNames=True, mTheme=ThemeChoice.DARK, mOrder=(object(),), mPosition=None, mFirstRunDone=True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            self.mStore.save(tBroken)
        self.assertEqual(os.listdir(os.path.dirname(self.mPath)), ["settings.json"])
        self.assertEqual(self.mStore.load(), (Settings.defaults(), None))

    def testPositionOutsideTheScreenCoordinateRangeIsDropped(self):
        self.writeRaw({"position": [99999999999, 0]})
        self.assertIsNone(self.mStore.load()[0].mPosition)
        self.writeRaw({"position": [32767, -32768]})
        self.assertEqual(self.mStore.load()[0].mPosition, (32767, -32768))

    def testCorruptFileFallsBackWithANote(self):
        self.writeRaw("{not json")
        tSettings, tNote = self.mStore.load()
        self.assertEqual(tSettings, Settings.defaults())
        self.assertIsNotNone(tNote)

    def testEachBadFieldFallsBackAlone(self):
        self.writeRaw({"columns": 99, "rows": "two", "scale": True, "shelf": "sometimes", "theme": "dark", "showNames": 1, "position": [1, 2, 3]})
        tSettings, tNote = self.mStore.load()
        self.assertIsNone(tNote)
        self.assertEqual(tSettings.mColumns, 8)
        self.assertEqual(tSettings.mRows, Settings.defaults().mRows)
        self.assertEqual(tSettings.mScale, Settings.defaults().mScale)
        self.assertEqual(tSettings.mShelfMode, ShelfMode.HOVER)
        self.assertEqual(tSettings.mTheme, ThemeChoice.DARK)
        self.assertFalse(tSettings.mShowNames)
        self.assertIsNone(tSettings.mPosition)

    def testOrderKeepsOnlyUniquePaneIdsUpToTheCap(self):
        tMany = ["%032x" % tIndex for tIndex in range(100)]
        self.writeRaw({"order": [PANE_A, "../etc", PANE_A, 7, PANE_B] + tMany})
        tOrder = self.mStore.load()[0].mOrder
        self.assertEqual(tOrder[:2], (PANE_A, PANE_B))
        self.assertEqual(len(tOrder), 64)
