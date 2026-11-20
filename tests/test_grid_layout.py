import unittest

from agents_deck.ui.grid_layout import GridLayout


class GridLayoutTest(unittest.TestCase):
    def testRowsGrowToFitEverySession(self):
        self.assertEqual(GridLayout(4, 1, 3, 9, False).mRows, 3)
        self.assertEqual(GridLayout(4, 2, 3, 1, False).mRows, 2)

    def testTilesDoNotOverlapAndStayInsideThePlate(self):
        for tScale in (2, 3, 6):
            for tNames in (False, True):
                tLayout = GridLayout(3, 2, tScale, 7, tNames)
                tPlate = tLayout.plateRect()
                tRects = tLayout.tileRects()
                for tIndex, tRect in enumerate(tRects):
                    self.assertTrue(tPlate.contains(tRect.mX, tRect.mY) and tPlate.contains(tRect.mX + tRect.mWidth - 1, tRect.mY + tRect.mHeight - 1))
                    self.assertEqual(tLayout.tileAt(tRect.centerX(), tRect.centerY()), tIndex)
                    self.assertEqual(tLayout.slotNearest(tRect.centerX(), tRect.centerY()), tIndex)
                    for tOther in tRects[tIndex + 1:]:
                        tApart = tRect.mX + tRect.mWidth <= tOther.mX or tOther.mX + tOther.mWidth <= tRect.mX or tRect.mY + tRect.mHeight <= tOther.mY or tOther.mY + tOther.mHeight <= tRect.mY
                        self.assertTrue(tApart)

    def testControlsDoNotOverlapTilesOrEachOther(self):
        for tScale in (2, 6):
            tLayout = GridLayout(4, 1, tScale, 4, False)
            tGear = tLayout.gearRect()
            tGrip = tLayout.gripRect()
            self.assertLessEqual(tGear.mY + tGear.mHeight, tGrip.mY)
            tLastTile = tLayout.tileRect(3)
            self.assertLessEqual(tLastTile.mX + tLastTile.mWidth, tGear.mX)

    def testGapsAreNotTiles(self):
        tLayout = GridLayout(2, 1, 3, 2, False)
        tFirst = tLayout.tileRect(0)
        self.assertIsNone(tLayout.tileAt(tFirst.mX + tFirst.mWidth + 1, tFirst.centerY()))
