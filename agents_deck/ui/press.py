import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Press:
    """A primary-button press still held: what it landed on and where.

    mTarget is a pane id, GEAR or GRIP. Window coordinates are kept for the
    reorder drag; root coordinates for the resize grip, which moves the
    window under the pointer while it is held.
    """

    GEAR = "gear"
    GRIP = "grip"

    mTarget: str
    mX: float
    mY: float
    mRootX: float
    mRootY: float
    mStartScale: int

    def isPane(self) -> bool:
        return self.mTarget not in (self.GEAR, self.GRIP)

    def movedBeyond(self, x: float, y: float, thresholdPx: int) -> bool:
        return math.hypot(x - self.mX, y - self.mY) > thresholdPx
