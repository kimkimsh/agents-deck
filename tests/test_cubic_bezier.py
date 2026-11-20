import unittest

from agents_deck.constants.easing_constants import EasingConstants
from agents_deck.ui.cubic_bezier import CubicBezier


class CubicBezierTest(unittest.TestCase):
    def testEndpointsAndMonotonicity(self):
        tCurve = CubicBezier(*EasingConstants.EASE_OUT)
        self.assertEqual(tCurve.at(0.0), 0.0)
        self.assertEqual(tCurve.at(1.0), 1.0)
        tValues = [tCurve.at(tStep / 50.0) for tStep in range(51)]
        self.assertEqual(tValues, sorted(tValues))

    def testEaseOutLeadsLinear(self):
        self.assertGreater(CubicBezier(*EasingConstants.EASE_OUT).at(0.25), 0.6)

    def testLinearCurveIsIdentity(self):
        tLinear = CubicBezier(0.0, 0.0, 1.0, 1.0)
        for tX in (0.1, 0.33, 0.5, 0.9):
            self.assertAlmostEqual(tLinear.at(tX), tX, places=4)
