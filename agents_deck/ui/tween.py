from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.ui.cubic_bezier import CubicBezier


class Tween:
    """One value easing from where it is now to a target. Retargeting starts
    from the current value, so an interrupted ease never jumps."""

    mFrom: float
    mTo: float
    mStart: float
    mDurationSeconds: float
    mCurve: CubicBezier

    def __init__(self, value: float, curve: CubicBezier):
        self.mFrom = value
        self.mTo = value
        self.mStart = 0.0
        self.mDurationSeconds = 0.0
        self.mCurve = curve

    def retarget(self, target: float, durationMs: int, now: float):
        if target == self.mTo:
            return
        self.mFrom = self.value(now)
        self.mTo = target
        self.mStart = now
        self.mDurationSeconds = durationMs / TimingConstants.MS_PER_SECOND

    def value(self, now: float) -> float:
        if self.mDurationSeconds <= 0.0:
            return self.mTo
        tProgress = (now - self.mStart) / self.mDurationSeconds
        return self.mFrom + (self.mTo - self.mFrom) * self.mCurve.at(tProgress)

    def done(self, now: float) -> bool:
        return self.mDurationSeconds <= 0.0 or now - self.mStart >= self.mDurationSeconds

    def target(self) -> float:
        return self.mTo
