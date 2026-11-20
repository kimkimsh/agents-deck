import unittest

from agents_deck.settings.tile_order import TileOrder

A, B, C = "a" * 32, "b" * 32, "c" * 32


class TileOrderTest(unittest.TestCase):
    def testNewPanesGoLastAndGonePanesKeepTheirPlace(self):
        tOrder = TileOrder((B, A))
        self.assertEqual(tOrder.arrange([A, B, C], 1.0), [B, A, C])
        self.assertEqual(tOrder.arrange([A, C], 2.0), [A, C])
        self.assertEqual(tOrder.arrange([A, B, C], 3.0), [B, A, C])

    def testMoveAmongDisplayedPanes(self):
        tOrder = TileOrder((A, B, C))
        tOrder.move(C, 0, [A, B, C])
        self.assertEqual(tOrder.arrange([A, B, C], 1.0), [C, A, B])

    def testCapForgetsTheLeastRecentlySeen(self):
        tPanes = ["%032x" % tIndex for tIndex in range(70)]
        tOrder = TileOrder(())
        for tIndex, tPane in enumerate(tPanes):
            tOrder.arrange([tPane], float(tIndex))
        self.assertEqual(len(tOrder.order()), 64)
        self.assertNotIn(tPanes[0], tOrder.order())
        self.assertIn(tPanes[-1], tOrder.order())

    def testCapNeverHidesALivePane(self):
        tPanes = ["%032x" % tIndex for tIndex in range(65)]
        tOrder = TileOrder(())
        for tPoll in range(3):
            self.assertEqual(tOrder.arrange(tPanes, float(tPoll)), tPanes)

    def testForgottenPanesLeaveNoTimestampBehind(self):
        tOrder = TileOrder(())
        for tIndex in range(200):
            tOrder.arrange(["%032x" % tIndex], float(tIndex))
        self.assertEqual(len(tOrder.order()), 64)
        self.assertEqual(set(tOrder.mLastSeen), set(tOrder.order()))
