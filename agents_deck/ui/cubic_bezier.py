class CubicBezier:
    """A CSS-style timing curve from (0,0) to (1,1) through two control points."""

    NEWTON_STEPS = 8
    BISECT_STEPS = 20
    EPSILON = 1e-6

    mX1: float
    mY1: float
    mX2: float
    mY2: float

    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.mX1 = x1
        self.mY1 = y1
        self.mX2 = x2
        self.mY2 = y2

    def at(self, progress: float) -> float:
        """Eased value for linear progress in [0, 1]."""
        if progress <= 0.0:
            return 0.0
        if progress >= 1.0:
            return 1.0
        return self._coordinate(self._solveT(progress), self.mY1, self.mY2)

    def _solveT(self, x: float) -> float:
        tT = x
        for _ in range(self.NEWTON_STEPS):
            tError = self._coordinate(tT, self.mX1, self.mX2) - x
            if abs(tError) < self.EPSILON:
                return tT
            tSlope = self._slope(tT, self.mX1, self.mX2)
            if abs(tSlope) < self.EPSILON:
                break
            tT -= tError / tSlope
        tLow, tHigh = 0.0, 1.0
        tT = x
        for _ in range(self.BISECT_STEPS):
            if self._coordinate(tT, self.mX1, self.mX2) < x:
                tLow = tT
            else:
                tHigh = tT
            tT = (tLow + tHigh) / 2.0
        return tT

    @staticmethod
    def _coordinate(t: float, first: float, second: float) -> float:
        tInverse = 1.0 - t
        return 3.0 * tInverse * tInverse * t * first + 3.0 * tInverse * t * t * second + t * t * t

    @staticmethod
    def _slope(t: float, first: float, second: float) -> float:
        tInverse = 1.0 - t
        return 3.0 * tInverse * tInverse * first + 6.0 * tInverse * t * (second - first) + 3.0 * t * t * (1.0 - second)
