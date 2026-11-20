from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle in window pixels."""

    mX: int
    mY: int
    mWidth: int
    mHeight: int

    def contains(self, x: float, y: float) -> bool:
        return self.mX <= x < self.mX + self.mWidth and self.mY <= y < self.mY + self.mHeight

    def centerX(self) -> float:
        return self.mX + self.mWidth / 2.0

    def centerY(self) -> float:
        return self.mY + self.mHeight / 2.0
