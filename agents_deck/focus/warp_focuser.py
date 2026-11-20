import logging

from gi.repository import Gio, GLib

from agents_deck.constants.app_constants import AppConstants
from agents_deck.constants.warp_constants import WarpConstants


class WarpFocuser:
    """Brings a Warp pane forward through warp://session/<pane uuid>.

    The launch is asynchronous: Warp's desktop entry has no D-Bus activation,
    so every call starts a short-lived warp-terminal process that hands the
    URI to the running instance. A successful launch does not prove the pane
    was found. UI thread only.
    """

    mLogger: logging.Logger

    def __init__(self):
        self.mLogger = logging.getLogger(AppConstants.LOGGER_NAME)

    def focus(self, paneUuid: str) -> bool:
        """False when the id is not a Warp pane id; nothing is launched then."""
        if not WarpConstants.PANE_UUID_PATTERN.fullmatch(paneUuid):
            return False
        Gio.AppInfo.launch_default_for_uri_async(WarpConstants.SESSION_URI_FORMAT % paneUuid, None, None, self._onLaunched, None)
        return True

    def _onLaunched(self, source, result, userData):
        try:
            Gio.AppInfo.launch_default_for_uri_finish(result)
        except GLib.Error as tError:
            self.mLogger.warning("Warp focus request failed: %s", tError.message)
