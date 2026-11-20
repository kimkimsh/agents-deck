import dataclasses
import math
import time
from typing import Callable, Dict, List, Optional, Tuple

import cairo
from gi.repository import Gdk, GLib, Gtk

from agents_deck.constants.animation_constants import AnimationConstants
from agents_deck.constants.app_constants import AppConstants
from agents_deck.constants.easing_constants import EasingConstants
from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.discovery.process_table import ProcessTable
from agents_deck.focus.warp_focuser import WarpFocuser
from agents_deck.model.session_state import SessionState
from agents_deck.model.snapshot import Snapshot
from agents_deck.settings.settings import Settings
from agents_deck.settings.shelf_mode import ShelfMode
from agents_deck.settings.theme_choice import ThemeChoice
from agents_deck.settings.tile_order import TileOrder
from agents_deck.ui.cubic_bezier import CubicBezier
from agents_deck.ui.deck_painter import DeckPainter
from agents_deck.ui.grid_layout import GridLayout
from agents_deck.ui.press import Press
from agents_deck.ui.rect import Rect
from agents_deck.ui.sprite_animator import SpriteAnimator
from agents_deck.ui.sprite_frame import SpriteFrame
from agents_deck.ui.system_appearance import SystemAppearance
from agents_deck.ui.tile_view import TileView
from agents_deck.ui.tooltip_content import TooltipContent
from agents_deck.ui.tooltip_text import TooltipText
from agents_deck.ui.tooltip_window import TooltipWindow
from agents_deck.ui.tween import Tween


class OverlayWindow(Gtk.Window):
    """The deck: a borderless, always-on-top window that never takes focus.

    At rest only the tiles accept the pointer; everything else clicks
    through to the window below. While the shelf is shown the whole plate
    accepts it, so the plate can be dragged to move the deck and the gear
    and grip can be reached.

    Frames are recomputed on a FRAME_TICK_MS timeout and the window is
    redrawn only when one changes; eases (hover lift, shelf fade, drop
    return, shake) run on the frame clock only while one is moving.

    UI thread only.
    """

    GHOST = "ghost"
    PRIMARY_BUTTON = 1
    SCREEN_MARGIN_PX = 24

    mSettings: Settings
    mOnSettingsChanged: Callable[[Settings], None]
    mOnOpenSettings: Callable[[], None]
    mSettingsNote: Optional[str]
    mAppearance: SystemAppearance
    mPainter: DeckPainter
    mAnimator: SpriteAnimator
    mFocuser: WarpFocuser
    mProber: ProcessTable
    mTooltip: TooltipWindow
    mTooltipContent: TooltipContent
    mOrder: TileOrder
    mSnapshot: Optional[Snapshot]
    mSessions: Dict[str, SessionState]
    mDisplayed: List[str]
    mLayout: GridLayout
    mStale: bool
    mEaseOut: CubicBezier
    mEaseInOut: CubicBezier
    mShelf: Tween
    mLifts: Dict[str, Tween]
    mShakes: Dict[str, float]
    mReturn: Optional[Tuple[str, float, float, float]]
    mPointerInside: bool
    mHover: Optional[str]
    mPress: Optional[Press]
    mDragPane: Optional[str]
    mDragPoint: Tuple[float, float]
    mDragOffset: Tuple[float, float]
    mFirstRunUntil: float
    mFrameSignature: Tuple
    mEaseTick: Optional[int]
    mShelfHideTimer: Optional[int]
    mTooltipTimer: Optional[int]
    mTooltipTarget: Optional[str]
    mTooltipHiddenAt: float
    mFrameTimer: Optional[int]
    mPosition: Tuple[int, int]
    mUserPlaced: bool

    def __init__(self, settings: Settings, settingsNote: Optional[str], painter: DeckPainter, onSettingsChanged: Callable[[Settings], None], onOpenSettings: Callable[[], None]):
        super().__init__(type=Gtk.WindowType.TOPLEVEL, title=AppConstants.APP_NAME)
        self.mSettings = settings
        self.mOnSettingsChanged = onSettingsChanged
        self.mOnOpenSettings = onOpenSettings
        self.mSettingsNote = settingsNote
        self.mAppearance = SystemAppearance(self.queue_draw)
        self.mPainter = painter
        self.mAnimator = SpriteAnimator()
        self.mFocuser = WarpFocuser()
        self.mProber = ProcessTable(ProcessConstants.PROC_ROOT)
        self.mTooltip = TooltipWindow()
        self.mTooltipContent = TooltipContent()
        self.mOrder = TileOrder(settings.mOrder)
        self.mSnapshot = None
        self.mSessions = {}
        self.mDisplayed = []
        self.mStale = False
        self.mEaseOut = CubicBezier(*EasingConstants.EASE_OUT)
        self.mEaseInOut = CubicBezier(*EasingConstants.EASE_IN_OUT)
        self.mShelf = Tween(0.0, self.mEaseOut)
        self.mLifts = {}
        self.mShakes = {}
        self.mReturn = None
        self.mPointerInside = False
        self.mHover = None
        self.mPress = None
        self.mDragPane = None
        self.mDragPoint = (0.0, 0.0)
        self.mDragOffset = (0.0, 0.0)
        self.mFirstRunUntil = 0.0 if settings.mFirstRunDone else time.monotonic() + AnimationConstants.FIRST_RUN_SHELF_MS / TimingConstants.MS_PER_SECOND
        self.mFrameSignature = ()
        self.mEaseTick = None
        self.mShelfHideTimer = None
        self.mTooltipTimer = None
        self.mTooltipTarget = None
        self.mTooltipHiddenAt = 0.0
        self.mLayout = self._newLayout()
        self.mPosition = (0, 0)
        self.mUserPlaced = settings.mPosition is not None

        tVisual = self.get_screen().get_rgba_visual()
        if tVisual is not None:
            self.set_visual(tVisual)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )
        self.connect("draw", self._onDraw)
        self.connect("button-press-event", self._onPress)
        self.connect("button-release-event", self._onRelease)
        self.connect("motion-notify-event", self._onMotion)
        self.connect("enter-notify-event", self._onEnter)
        self.connect("leave-notify-event", self._onLeave)
        self.connect("key-press-event", self._onKey)
        self.connect("configure-event", self._onConfigure)
        self.connect("realize", self._onRealize)
        self.connect("grab-broken-event", self._onGrabBroken)
        self.connect("unmap", self._onUnmap)
        self.connect("destroy", self._onDestroy)
        self._resizeTo(self.mLayout)
        self._placeInitially()
        self._updateShelf()
        self.mFrameTimer = GLib.timeout_add(AnimationConstants.FRAME_TICK_MS, self._onFrameTick)

    # Inputs from the application.

    def applySnapshot(self, snapshot: Snapshot):
        self.mSnapshot = snapshot
        self.mSessions = {tSession.mPaneUuid: tSession for tSession in snapshot.mSessions}
        self.mLifts = {tPane: tLift for tPane, tLift in self.mLifts.items() if tPane in self.mSessions}
        self.mShakes = {tPane: tStart for tPane, tStart in self.mShakes.items() if tPane in self.mSessions}
        tDisplayed = self.mOrder.arrange([tSession.mPaneUuid for tSession in snapshot.mSessions], time.time())
        if tDisplayed != self.mDisplayed:
            self.mDisplayed = tDisplayed
            if self.mOrder.order() != self.mSettings.mOrder:
                self._changeSettings(dataclasses.replace(self.mSettings, mOrder=self.mOrder.order()))
            self._relayout(anchorToNearestEdge=True)
        self._refreshTooltip()
        self.queue_draw()

    def applySettings(self, settings: Settings):
        tOld = self.mSettings
        self.mSettings = settings
        if (settings.mColumns, settings.mRows, settings.mScale, settings.mShowNames) != (tOld.mColumns, tOld.mRows, tOld.mScale, tOld.mShowNames):
            self._relayout(anchorToNearestEdge=True)
        self._updateShelf()
        self.queue_draw()

    def resetOrder(self):
        self.mOrder.reset()
        self.mDisplayed = self.mOrder.arrange(list(self.mSessions), time.time())
        self._changeSettings(dataclasses.replace(self.mSettings, mOrder=self.mOrder.order()))
        self._relayout(anchorToNearestEdge=True)

    def settings(self) -> Settings:
        return self.mSettings

    def setStale(self, stale: bool):
        if stale != self.mStale:
            self.mStale = stale
            self._refreshTooltip()
            self.queue_draw()

    # Geometry.

    def _newLayout(self) -> GridLayout:
        return GridLayout(self.mSettings.mColumns, self.mSettings.mRows, self.mSettings.mScale, max(len(self.mDisplayed), 1), self.mSettings.mShowNames)

    def _relayout(self, anchorToNearestEdge: bool):
        tOld = self.mLayout
        tNew = self._newLayout()
        self.mLayout = tNew
        if (tOld.width(), tOld.height()) != (tNew.width(), tNew.height()):
            tX, tY = self.mPosition
            tArea = self._workarea(tX + tOld.width() // 2, tY + tOld.height() // 2)
            if anchorToNearestEdge and tArea is not None:
                if tX + tOld.width() / 2.0 > tArea.x + tArea.width / 2.0:
                    tX += tOld.width() - tNew.width()
                if tY + tOld.height() / 2.0 > tArea.y + tArea.height / 2.0:
                    tY += tOld.height() - tNew.height()
            self._resizeTo(tNew)
            self._moveTo(tX, tY)
        self._updateInputRegion()
        self.queue_draw()

    def _resizeTo(self, layout: GridLayout):
        self.set_size_request(layout.width(), layout.height())
        self.resize(layout.width(), layout.height())

    def _placeInitially(self):
        tPosition = self.mSettings.mPosition
        if tPosition is not None:
            self._moveTo(tPosition[0], tPosition[1])
            return
        tDisplay = Gdk.Display.get_default()
        tMonitor = tDisplay.get_primary_monitor() or tDisplay.get_monitor(0) if tDisplay is not None else None
        if tMonitor is None:
            return
        tArea = tMonitor.get_workarea()
        self._moveTo(tArea.x + (tArea.width - self.mLayout.width()) // 2, tArea.y + tArea.height - self.mLayout.height() - self.SCREEN_MARGIN_PX)

    def _moveTo(self, x: int, y: int):
        """Moves the deck inside the work area of the monitor it lands on; a
        deck larger than that area keeps its top-left corner, where the
        settings gear is, on screen."""
        tArea = self._workarea(x + self.mLayout.width() // 2, y + self.mLayout.height() // 2)
        if tArea is not None:
            x = max(min(x, tArea.x + tArea.width - self.mLayout.width()), tArea.x)
            y = max(min(y, tArea.y + tArea.height - self.mLayout.height()), tArea.y)
        self.mPosition = (x, y)
        self.move(x, y)

    @staticmethod
    def _workarea(x: int, y: int) -> Optional[Gdk.Rectangle]:
        tDisplay = Gdk.Display.get_default()
        if tDisplay is None:
            return None
        tMonitor = tDisplay.get_monitor_at_point(x, y)
        return tMonitor.get_workarea() if tMonitor is not None else None

    def _updateInputRegion(self):
        if self._shelfWanted() or self.mShelf.value(time.monotonic()) > 0.0:
            tRects = [self.mLayout.plateRect()]
        else:
            tRects = self.mLayout.tileRects()
        self.input_shape_combine_region(cairo.Region([cairo.RectangleInt(tRect.mX, tRect.mY, tRect.mWidth, tRect.mHeight) for tRect in tRects]))

    # Shelf.

    def _shelfWanted(self) -> bool:
        return (
            self.mSettings.mShelfMode is ShelfMode.ALWAYS
            or self.mPointerInside
            or self.mPress is not None
            or time.monotonic() < self.mFirstRunUntil
        )

    def _updateShelf(self):
        tNow = time.monotonic()
        if self._shelfWanted():
            self.mShelf.retarget(1.0, AnimationConstants.SHELF_FADE_IN_MS, tNow)
        else:
            self.mShelf.retarget(0.0, AnimationConstants.SHELF_FADE_OUT_MS, tNow)
        self._updateInputRegion()
        self._startEasing()

    def _onShelfHideTimer(self) -> bool:
        self.mShelfHideTimer = None
        self.mPointerInside = False
        self._updateShelf()
        return GLib.SOURCE_REMOVE

    # Frames and easing.

    def _onFrameTick(self) -> bool:
        tSignature = tuple(self._tileViews())
        if tSignature != self.mFrameSignature:
            self.mFrameSignature = tSignature
            self.queue_draw()
        if self.mFirstRunUntil and time.monotonic() >= self.mFirstRunUntil:
            self.mFirstRunUntil = 0.0
            self._changeSettings(dataclasses.replace(self.mSettings, mFirstRunDone=True))
            self._updateShelf()
        return GLib.SOURCE_CONTINUE

    def _startEasing(self):
        if self.mEaseTick is None:
            self.mEaseTick = self.add_tick_callback(self._onEaseTick)

    def _onEaseTick(self, widget, clock) -> bool:
        tNow = time.monotonic()
        self.queue_draw()
        tMoving = not self.mShelf.done(tNow) or any(not tLift.done(tNow) for tLift in self.mLifts.values())
        tMoving = tMoving or bool(self.mShakes) or self.mReturn is not None or self.mDragPane is not None
        for tPane, tStart in list(self.mShakes.items()):
            if (tNow - tStart) * TimingConstants.MS_PER_SECOND >= AnimationConstants.SHAKE_MS:
                del self.mShakes[tPane]
        if self.mReturn is not None and (tNow - self.mReturn[3]) * TimingConstants.MS_PER_SECOND >= AnimationConstants.DROP_RETURN_MS:
            self.mReturn = None
        if self.mShelf.done(tNow) and self.mShelf.target() == 0.0:
            self._updateInputRegion()
        if tMoving:
            return GLib.SOURCE_CONTINUE
        self.mEaseTick = None
        return GLib.SOURCE_REMOVE

    def _tileViews(self) -> List[TileView]:
        tNowWall = time.time()
        tNow = time.monotonic()
        tReduced = self.mAppearance.reducedMotion()
        tScale = self.mLayout.mScale
        tViews: List[TileView] = []
        tDragged: Optional[TileView] = None
        if not self.mDisplayed:
            tSpecies, tFrame = SpriteAnimator.ghost()
            tRect = self.mLayout.tileRect(0)
            return [TileView(tRect.mX, tRect.mY, SpriteFrame(tSpecies, tFrame, (), LayoutConstants.GHOST_OPACITY), LayoutConstants.GHOST_OPACITY, None, None)]
        for tIndex, tPane in enumerate(self._previewOrder()):
            tSession = self.mSessions.get(tPane)
            if tSession is None:
                continue
            tRect = self.mLayout.tileRect(tIndex)
            tFrame = self.mAnimator.frame(tSession, tNowWall, tReduced)
            tX = float(tRect.mX)
            tY = float(tRect.mY) - round(self._lift(tPane, tNow) * tScale)
            tX += self._shakeOffset(tPane, tNow)
            if self.mReturn is not None and self.mReturn[0] == tPane:
                tProgress = self.mEaseInOut.at((tNow - self.mReturn[3]) * TimingConstants.MS_PER_SECOND / AnimationConstants.DROP_RETURN_MS)
                tX = self.mReturn[1] + (tX - self.mReturn[1]) * tProgress
                tY = self.mReturn[2] + (tY - self.mReturn[2]) * tProgress
            tOpacity = tFrame.mOpacity * (LayoutConstants.STALE_OPACITY if self.mStale else 1.0)
            tObservation = tSession.mObservation
            tBadge = len(tObservation.mBackground) if tObservation.mBackgroundKnown and tObservation.mBackground else None
            tName = tSession.mTitle if self.mSettings.mShowNames else None
            if tPane == self.mDragPane:
                tDragged = TileView(round(self.mDragPoint[0] - self.mDragOffset[0]), round(self.mDragPoint[1] - self.mDragOffset[1]), tFrame, tOpacity, tBadge, tName)
                continue
            tViews.append(TileView(round(tX), round(tY), tFrame, tOpacity, tBadge, tName))
        if tDragged is not None:
            tViews.append(tDragged)
        return tViews

    def _previewOrder(self) -> List[str]:
        if self.mDragPane is None:
            return self.mDisplayed
        tSlot = self.mLayout.slotNearest(self.mDragPoint[0], self.mDragPoint[1])
        tPreview = [tPane for tPane in self.mDisplayed if tPane != self.mDragPane]
        tPreview.insert(min(tSlot, len(tPreview)), self.mDragPane)
        return tPreview

    def _lift(self, pane: str, now: float) -> float:
        tTween = self.mLifts.get(pane)
        return tTween.value(now) if tTween is not None else 0.0

    def _shakeOffset(self, pane: str, now: float) -> float:
        tStart = self.mShakes.get(pane)
        if tStart is None:
            return 0.0
        tProgress = min((now - tStart) * TimingConstants.MS_PER_SECOND / AnimationConstants.SHAKE_MS, 1.0)
        return round(AnimationConstants.SHAKE_AMPLITUDE_PX * math.sin(tProgress * AnimationConstants.SHAKE_CYCLES * 2.0 * math.pi) * (1.0 - tProgress))

    def _dark(self) -> bool:
        if self.mSettings.mTheme is ThemeChoice.SYSTEM:
            return self.mAppearance.prefersDark()
        return self.mSettings.mTheme is ThemeChoice.DARK

    def _onRealize(self, widget):
        self._updateInputRegion()

    def _onDraw(self, widget, context: cairo.Context) -> bool:
        tShelf = self.mShelf.value(time.monotonic())
        self.mPainter.paint(context, self.mLayout, self._tileViews(), tShelf, self._dark())
        return True

    # Pointer.

    def _targetAt(self, x: float, y: float) -> Optional[str]:
        """The pane, GHOST, "gear" or "grip" under the pointer, or None."""
        tShelfShown = self.mShelf.value(time.monotonic()) > 0.0 or self._shelfWanted()
        if tShelfShown and self.mLayout.gearRect().contains(x, y):
            return Press.GEAR
        if tShelfShown and self.mLayout.gripRect().contains(x, y):
            return Press.GRIP
        tIndex = self.mLayout.tileAt(x, y)
        if tIndex is None:
            return None
        if not self.mDisplayed:
            return self.GHOST
        return self.mDisplayed[tIndex] if tIndex < len(self.mDisplayed) else None

    def _onEnter(self, widget, event) -> bool:
        if event.mode != Gdk.CrossingMode.NORMAL:
            return False
        if self.mShelfHideTimer is not None:
            GLib.source_remove(self.mShelfHideTimer)
            self.mShelfHideTimer = None
        self.mPointerInside = True
        self._updateShelf()
        return False

    def _onLeave(self, widget, event) -> bool:
        if event.mode != Gdk.CrossingMode.NORMAL or event.detail == Gdk.NotifyType.INFERIOR or self.mPress is not None:
            return False
        self._setHover(None)
        if self.mShelfHideTimer is None:
            self.mShelfHideTimer = GLib.timeout_add(AnimationConstants.SHELF_HIDE_DELAY_MS, self._onShelfHideTimer)
        return False

    def _onMotion(self, widget, event) -> bool:
        tPress = self.mPress
        if tPress is None:
            self._setHover(self._targetAt(event.x, event.y))
            return False
        if tPress.mTarget == Press.GRIP:
            self._resizeByGrip(tPress, event.x_root, event.y_root)
            return True
        # The pressed pane can end between the press and the drag threshold.
        tPaneShown = tPress.isPane() and tPress.mTarget in self.mDisplayed
        if self.mDragPane is None and tPaneShown and tPress.movedBeyond(event.x, event.y, LayoutConstants.DRAG_THRESHOLD_PX):
            tRect = self.mLayout.tileRect(self.mDisplayed.index(tPress.mTarget))
            self.mDragPane = tPress.mTarget
            self.mDragOffset = (tPress.mX - tRect.mX, tPress.mY - tRect.mY)
            # Only a tile drag can be cancelled, so only it takes the
            # keyboard; otherwise Esc belongs to the focused terminal. A
            # failed seat grab releases the pointer too, so it is retaken.
            if not self._grab(event, Gdk.SeatCapabilities.ALL):
                self._grab(event, Gdk.SeatCapabilities.ALL_POINTING)
            self._hideTooltip()
            self._startEasing()
        if self.mDragPane is not None:
            self.mDragPoint = (event.x, event.y)
            self.queue_draw()
        return True

    def _onPress(self, widget, event) -> bool:
        if event.button != self.PRIMARY_BUTTON or event.type != Gdk.EventType.BUTTON_PRESS:
            return False
        self._hideTooltip()
        tTarget = self._targetAt(event.x, event.y)
        if tTarget is None or tTarget == self.GHOST:
            if self.mLayout.plateRect().contains(event.x, event.y):
                self.mUserPlaced = True
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        self.mPress = Press(tTarget, event.x, event.y, event.x_root, event.y_root, self.mSettings.mScale)
        if tTarget != Press.GEAR:
            # The implicit grab of the press already routes motion here; the
            # explicit one also covers the pointer crossing other windows.
            self._grab(event, Gdk.SeatCapabilities.ALL_POINTING)
        return True

    def _onRelease(self, widget, event) -> bool:
        tPress = self.mPress
        if tPress is None or event.button != self.PRIMARY_BUTTON:
            return False
        self._endPress()
        if tPress.mTarget == Press.GEAR:
            if self.mLayout.gearRect().contains(event.x, event.y):
                self.mOnOpenSettings()
        elif tPress.mTarget == Press.GRIP:
            self.mUserPlaced = True
            self._changeSettings(dataclasses.replace(self.mSettings, mPosition=self.mPosition))
        elif self.mDragPane is not None:
            self._drop(event.x, event.y)
        else:
            self._activate(tPress.mTarget)
        self._afterPress()
        return True

    def _onKey(self, widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape and self.mPress is not None:
            self._cancelPress()
            return True
        return False

    def _onGrabBroken(self, widget, event) -> bool:
        # Another client took the pointer (a WM shortcut, a screen lock); no
        # release will arrive for this press.
        if self.mPress is not None:
            self._cancelPress()
        return False

    def _onUnmap(self, widget):
        if self.mPress is not None:
            self._cancelPress()

    def _onDestroy(self, widget):
        for tTimer in (self.mFrameTimer, self.mShelfHideTimer, self.mTooltipTimer):
            if tTimer is not None:
                GLib.source_remove(tTimer)
        self.mFrameTimer = None
        self.mShelfHideTimer = None
        self.mTooltipTimer = None
        self.mAppearance.detach()
        self.mTooltip.destroy()

    def _cancelPress(self):
        self._endPress()
        self._cancelDrag()
        self._afterPress()

    def _endPress(self):
        self.mPress = None
        self.get_display().get_default_seat().ungrab()

    def _afterPress(self):
        # Crossing events were ignored while the press lasted, so whether the
        # pointer is still over the deck is asked of the pointer itself.
        tWindow = self.get_window()
        tPointer = self.get_display().get_default_seat().get_pointer()
        if tWindow is not None and tPointer is not None:
            _, tX, tY, _ = tWindow.get_device_position(tPointer)
            if not self.mLayout.plateRect().contains(tX, tY):
                self._setHover(None)
                self.mPointerInside = False
        self._updateShelf()

    def _onConfigure(self, widget, event) -> bool:
        tPosition = (event.x, event.y)
        self.mPosition = tPosition
        # The default placement is not saved, so the deck follows a changed
        # monitor layout until the user puts it somewhere.
        if self.mPress is None and self.mUserPlaced and tPosition != self.mSettings.mPosition:
            self._changeSettings(dataclasses.replace(self.mSettings, mPosition=tPosition))
        return False

    def _grab(self, event, capabilities: Gdk.SeatCapabilities) -> bool:
        tStatus = self.get_display().get_default_seat().grab(event.window, capabilities, True, None, event, None, None)
        return tStatus == Gdk.GrabStatus.SUCCESS

    def _drop(self, x: float, y: float):
        tPane = self.mDragPane
        if tPane is None:
            return
        if not self.mLayout.plateRect().contains(x, y):
            self._cancelDrag()
            return
        tSlot = self.mLayout.slotNearest(x, y)
        self.mOrder.move(tPane, tSlot, self.mDisplayed)
        self.mDisplayed = self.mOrder.arrange(list(self.mSessions), time.time())
        self.mDragPane = None
        self._changeSettings(dataclasses.replace(self.mSettings, mOrder=self.mOrder.order()))
        self.queue_draw()

    def _cancelDrag(self):
        tPane = self.mDragPane
        if tPane is None:
            return
        self.mReturn = (tPane, self.mDragPoint[0] - self.mDragOffset[0], self.mDragPoint[1] - self.mDragOffset[1], time.monotonic())
        self.mDragPane = None
        self._startEasing()

    def _resizeByGrip(self, press: Press, rootX: float, rootY: float):
        tDelta = ((rootX - press.mRootX) + (rootY - press.mRootY)) / 2.0
        tScale = press.mStartScale + int(round(tDelta / LayoutConstants.SCALE_STEP_PX))
        tScale = min(max(tScale, LayoutConstants.MIN_SCALE), LayoutConstants.MAX_SCALE)
        if tScale != self.mSettings.mScale:
            self._changeSettings(dataclasses.replace(self.mSettings, mScale=tScale))
            self._relayout(anchorToNearestEdge=False)
            self._moveTo(self.mPosition[0], self.mPosition[1])

    def _activate(self, target: str):
        if target == self.GHOST:
            return
        tSession = self.mSessions.get(target)
        if tSession is None:
            return
        if not self.mProber.isRunning(tSession.mPid, tSession.mStartTicks) or not self.mFocuser.focus(target):
            self.mShakes[target] = time.monotonic()
            self._startEasing()
            self._showTooltip(target, self.mTooltipContent.forEnded(tSession))

    def _setHover(self, target: Optional[str]):
        if target == self.mHover:
            return
        tNow = time.monotonic()
        for tPane in (self.mHover, target):
            if tPane is None or tPane not in self.mSessions:
                continue
            tLift = self.mLifts.setdefault(tPane, Tween(0.0, self.mEaseOut))
            tLift.retarget(1.0 if tPane == target else 0.0, AnimationConstants.HOVER_LIFT_MS, tNow)
        self.mHover = target
        self._startEasing()
        self._scheduleTooltip(target)

    # Tooltip.

    def _scheduleTooltip(self, target: Optional[str]):
        if self.mTooltipTimer is not None:
            GLib.source_remove(self.mTooltipTimer)
            self.mTooltipTimer = None
        tWarm = self.mTooltip.get_visible() or (time.monotonic() - self.mTooltipHiddenAt) * TimingConstants.MS_PER_SECOND < AnimationConstants.TOOLTIP_WARM_MS
        self._hideTooltip()
        if target is None:
            return
        if tWarm:
            self._showTooltipFor(target)
        else:
            self.mTooltipTimer = GLib.timeout_add(AnimationConstants.TOOLTIP_DELAY_MS, self._onTooltipTimer, target)

    def _onTooltipTimer(self, target: str) -> bool:
        self.mTooltipTimer = None
        if target == self.mHover and self.mPress is None:
            self._showTooltipFor(target)
        return GLib.SOURCE_REMOVE

    def _showTooltipFor(self, target: str):
        tText = self._tooltipText(target)
        if tText is not None:
            self._showTooltip(target, tText)

    def _tooltipText(self, target: str) -> Optional[TooltipText]:
        if target == Press.GEAR:
            return self.mTooltipContent.forGear(self.mSettingsNote)
        if target == Press.GRIP:
            return self.mTooltipContent.forGrip()
        if target == self.GHOST:
            return self.mTooltipContent.forGhost(self.mSnapshot is None or self.mSnapshot.mWarpRunning, self.mSettingsNote)
        tSession = self.mSessions.get(target)
        return self.mTooltipContent.forSession(tSession, time.time(), self.mStale) if tSession is not None else None

    def _showTooltip(self, target: str, text: TooltipText):
        tRect = self._targetRect(target)
        if tRect is None:
            return
        self.mTooltipTarget = target
        tX, tY = self.mPosition
        self.mTooltip.showFor(text, Rect(tX + tRect.mX, tY + tRect.mY, tRect.mWidth, tRect.mHeight), self._dark())

    def _targetRect(self, target: str) -> Optional[Rect]:
        if target == Press.GEAR:
            return self.mLayout.gearRect()
        if target == Press.GRIP:
            return self.mLayout.gripRect()
        if target == self.GHOST:
            return self.mLayout.tileRect(0)
        if target in self.mDisplayed:
            return self.mLayout.tileRect(self.mDisplayed.index(target))
        return None

    def _refreshTooltip(self):
        if self.mTooltip.get_visible() and self.mTooltipTarget is not None:
            tText = self._tooltipText(self.mTooltipTarget)
            if tText is None:
                self._hideTooltip()
            else:
                self._showTooltip(self.mTooltipTarget, tText)

    def _hideTooltip(self):
        if self.mTooltip.get_visible():
            self.mTooltip.hide()
            self.mTooltipHiddenAt = time.monotonic()
        self.mTooltipTarget = None

    def _changeSettings(self, settings: Settings):
        self.mSettings = settings
        self.mOnSettingsChanged(settings)
