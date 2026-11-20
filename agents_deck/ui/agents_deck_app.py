import logging
import os
import signal
import sys
import time
from typing import Optional

from gi.repository import Gio, GLib, Gtk

from agents_deck.collector import Collector
from agents_deck.collector_thread import CollectorThread
from agents_deck.constants.animation_constants import AnimationConstants
from agents_deck.constants.app_constants import AppConstants
from agents_deck.constants.path_constants import PathConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.diagnostics.once_logger import OnceLogger
from agents_deck.model.snapshot import Snapshot
from agents_deck.settings.settings import Settings
from agents_deck.settings.settings_store import SettingsStore
from agents_deck.ui.deck_painter import DeckPainter
from agents_deck.ui.overlay_window import OverlayWindow
from agents_deck.ui.settings_window import SettingsWindow
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_atlas import SpriteAtlas
from agents_deck.ui.sprite_palette import SpritePalette


class AgentsDeckApp(Gtk.Application):
    """Single-instance GTK application: one overlay, one collector thread.

    The collector thread only ever reaches the UI through GLib.idle_add, so
    every other member is touched on the UI thread alone. Settings are owned
    by the overlay; this class saves them, debounced, whenever they change.
    """

    mLogger: logging.Logger
    mErrors: OnceLogger
    mStore: Optional[SettingsStore]
    mOverlay: Optional[OverlayWindow]
    mSettingsWindow: Optional[SettingsWindow]
    mCollectorThread: Optional[CollectorThread]
    mLastSnapshotAt: float
    mPendingSave: Optional[Settings]
    mSaveTimer: Optional[int]
    mStaleTimer: Optional[int]

    def __init__(self):
        super().__init__(application_id=AppConstants.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.mLogger = logging.getLogger(AppConstants.LOGGER_NAME)
        self.mErrors = OnceLogger(self.mLogger)
        self.mStore = None
        self.mOverlay = None
        self.mSettingsWindow = None
        self.mCollectorThread = None
        self.mLastSnapshotAt = 0.0
        self.mPendingSave = None
        self.mSaveTimer = None
        self.mStaleTimer = None

    def do_activate(self):
        if self.mOverlay is not None:
            self.mOverlay.present()
            return
        self.mStore = SettingsStore(os.path.join(GLib.get_user_config_dir(), PathConstants.SETTINGS_DIR, PathConstants.SETTINGS_FILE))
        tSettings, tNote = self.mStore.load()
        if tNote:
            self.mLogger.warning("%s", tNote)
        tArt = SpriteArt()
        tPainter = DeckPainter(SpriteAtlas(tArt, SpritePalette()), tArt)
        self.mOverlay = OverlayWindow(tSettings, tNote, tPainter, self._onOverlaySettingsChanged, self._openSettings)
        self.mOverlay.connect("destroy", self._onOverlayDestroyed)
        self.add_window(self.mOverlay)
        self.mOverlay.show_all()

        tStart = time.time()
        self.mLastSnapshotAt = time.monotonic()
        tCollector = Collector.forHome(os.path.expanduser("~"), tStart, self.mErrors)
        self.mCollectorThread = CollectorThread(tCollector, self._publishFromCollector, TimingConstants.POLL_INTERVAL_SECONDS, self.mErrors)
        self.mCollectorThread.start()
        self.mStaleTimer = GLib.timeout_add(int(TimingConstants.POLL_INTERVAL_SECONDS * TimingConstants.MS_PER_SECOND), self._onStaleCheck)
        for tSignal in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, tSignal, self._onQuitSignal)

    def do_shutdown(self):
        if self.mCollectorThread is not None:
            self.mCollectorThread.stop()
        for tTimer in (self.mStaleTimer, self.mSaveTimer):
            if tTimer is not None:
                GLib.source_remove(tTimer)
        self.mStaleTimer = None
        self.mSaveTimer = None
        self._flushSave()
        Gtk.Application.do_shutdown(self)

    # Collector thread.

    def _publishFromCollector(self, snapshot: Snapshot):
        GLib.idle_add(self._applySnapshot, snapshot)

    # UI thread.

    def _applySnapshot(self, snapshot: Snapshot) -> bool:
        self.mLastSnapshotAt = time.monotonic()
        if self.mOverlay is not None:
            self.mOverlay.setStale(False)
            self.mOverlay.applySnapshot(snapshot)
        return GLib.SOURCE_REMOVE

    def _onStaleCheck(self) -> bool:
        tSilence = time.monotonic() - self.mLastSnapshotAt
        if self.mOverlay is not None and tSilence > TimingConstants.STALE_SNAPSHOT_POLLS * TimingConstants.POLL_INTERVAL_SECONDS:
            self.mOverlay.setStale(True)
        return GLib.SOURCE_CONTINUE

    def _onOverlaySettingsChanged(self, settings: Settings):
        if self.mSettingsWindow is not None:
            self.mSettingsWindow.update(settings)
        self._scheduleSave(settings)

    def _onWindowSettingsChanged(self, settings: Settings):
        if self.mOverlay is not None:
            self.mOverlay.applySettings(settings)
        self._scheduleSave(settings)

    def _openSettings(self):
        if self.mOverlay is None:
            return
        if self.mSettingsWindow is None:
            self.mSettingsWindow = SettingsWindow(self.mOverlay.settings, self._onWindowSettingsChanged, self.mOverlay.resetOrder, self.quit)
            self.add_window(self.mSettingsWindow)
        self.mSettingsWindow.update(self.mOverlay.settings())
        self.mSettingsWindow.show_all()
        self.mSettingsWindow.present()

    def _scheduleSave(self, settings: Settings):
        self.mPendingSave = settings
        if self.mSaveTimer is None:
            self.mSaveTimer = GLib.timeout_add(AnimationConstants.SETTINGS_SAVE_DELAY_MS, self._onSaveTimer)

    def _onSaveTimer(self) -> bool:
        self.mSaveTimer = None
        self._flushSave()
        return GLib.SOURCE_REMOVE

    def _flushSave(self):
        tSettings = self.mPendingSave
        if tSettings is None or self.mStore is None:
            return
        self.mPendingSave = None
        try:
            self.mStore.save(tSettings)
        except OSError as tError:
            self.mLogger.warning("Settings not saved: %s", tError)

    def _onOverlayDestroyed(self, widget):
        # The overlay is the app; an open settings window must not keep the
        # collector running with nothing to show.
        self.mOverlay = None
        self.quit()

    def _onQuitSignal(self) -> bool:
        self.quit()
        return GLib.SOURCE_REMOVE


def runApplication() -> int:
    return AgentsDeckApp().run([sys.argv[0]])
