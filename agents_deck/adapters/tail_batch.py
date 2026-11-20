from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TailBatch:
    """Complete lines read by one LineTail.readNew call.

    mWasReset: the file was (re)attached on this call, so derived state must be
    rebuilt; mPrefix then holds the lines before the attach point that contain
    one of the tail's needles, all read from the same file generation as mLines.
    """

    mWasReset: bool
    mPrefix: Tuple[bytes, ...]
    mLines: Tuple[bytes, ...]
