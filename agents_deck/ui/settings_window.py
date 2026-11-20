import dataclasses
from typing import Callable, List, Tuple

from gi.repository import Gdk, Gtk

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.settings.settings import Settings
from agents_deck.settings.shelf_mode import ShelfMode
from agents_deck.settings.theme_choice import ThemeChoice


class SettingsWindow(Gtk.Window):
    """Preferences that apply as they change. Closing hides the window.

    The window keeps no copy of the settings: each change is applied to
    what `settingsSource` returns at that moment, so a change made elsewhere
    meanwhile (a resize by the grip, a moved deck) is never overwritten.
    update() mirrors such changes into the widgets without echoing them back
    through onChange. UI thread only.
    """

    WIDTH_PX = 420
    BORDER_PX = 18
    ROW_SPACING_PX = 10
    COLUMN_SPACING_PX = 24
    SHELF_CHOICES: Tuple[Tuple[ShelfMode, str], ...] = ((ShelfMode.HOVER, "On hover"), (ShelfMode.ALWAYS, "Always"))
    THEME_CHOICES: Tuple[Tuple[ThemeChoice, str], ...] = ((ThemeChoice.SYSTEM, "System"), (ThemeChoice.LIGHT, "Light"), (ThemeChoice.DARK, "Dark"))

    mSettingsSource: Callable[[], Settings]
    mOnChange: Callable[[Settings], None]
    mUpdating: bool
    mColumns: Gtk.SpinButton
    mRows: Gtk.SpinButton
    mScale: Gtk.SpinButton
    mShelf: Gtk.ComboBoxText
    mShowNames: Gtk.Switch
    mTheme: Gtk.ComboBoxText

    def __init__(self, settingsSource: Callable[[], Settings], onChange: Callable[[Settings], None], onResetOrder: Callable[[], None], onQuit: Callable[[], None]):
        super().__init__(title="agents-deck settings")
        self.mSettingsSource = settingsSource
        self.mOnChange = onChange
        self.mUpdating = False
        self.set_default_size(self.WIDTH_PX, -1)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._onDelete)
        self.connect("key-press-event", self._onKey)

        tGrid = Gtk.Grid(row_spacing=self.ROW_SPACING_PX, column_spacing=self.COLUMN_SPACING_PX, border_width=self.BORDER_PX)
        self.mColumns = self._spin(LayoutConstants.MIN_GRID, LayoutConstants.MAX_GRID)
        self.mRows = self._spin(LayoutConstants.MIN_GRID, LayoutConstants.MAX_GRID)
        self.mScale = self._spin(LayoutConstants.MIN_SCALE, LayoutConstants.MAX_SCALE)
        self.mShelf = self._combo([tLabel for _, tLabel in self.SHELF_CHOICES])
        self.mShowNames = Gtk.Switch(halign=Gtk.Align.END)
        self.mShowNames.connect("notify::active", self._onWidgetChanged)
        self.mTheme = self._combo([tLabel for _, tLabel in self.THEME_CHOICES])
        tRows: List[Tuple[str, Gtk.Widget]] = [
            ("Columns", self.mColumns),
            ("Rows", self.mRows),
            ("Size", self.mScale),
            ("Shelf", self.mShelf),
            ("Show names", self.mShowNames),
            ("Theme", self.mTheme),
        ]
        for tIndex, (tLabel, tWidget) in enumerate(tRows):
            tGrid.attach(Gtk.Label(label=tLabel, halign=Gtk.Align.START, hexpand=True), 0, tIndex, 1, 1)
            tGrid.attach(tWidget, 1, tIndex, 1, 1)
        tButtons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=self.ROW_SPACING_PX, margin_top=self.ROW_SPACING_PX)
        tReset = Gtk.Button(label="Reset order")
        tReset.connect("clicked", self._onButton, onResetOrder)
        tQuit = Gtk.Button(label="Quit agents-deck")
        tQuit.connect("clicked", self._onButton, onQuit)
        tButtons.pack_start(tReset, False, False, 0)
        tButtons.pack_end(tQuit, False, False, 0)
        tGrid.attach(tButtons, 0, len(tRows), 2, 1)
        self.add(tGrid)
        self.update(settingsSource())

    def update(self, settings: Settings):
        self.mUpdating = True
        self.mColumns.set_value(settings.mColumns)
        self.mRows.set_value(settings.mRows)
        self.mScale.set_value(settings.mScale)
        self.mShelf.set_active([tMode for tMode, _ in self.SHELF_CHOICES].index(settings.mShelfMode))
        self.mShowNames.set_active(settings.mShowNames)
        self.mTheme.set_active([tTheme for tTheme, _ in self.THEME_CHOICES].index(settings.mTheme))
        self.mUpdating = False

    def _spin(self, low: int, high: int) -> Gtk.SpinButton:
        tSpin = Gtk.SpinButton.new_with_range(low, high, 1)
        tSpin.set_halign(Gtk.Align.END)
        tSpin.connect("value-changed", self._onWidgetChanged)
        return tSpin

    def _combo(self, labels: List[str]) -> Gtk.ComboBoxText:
        tCombo = Gtk.ComboBoxText(halign=Gtk.Align.END)
        for tLabel in labels:
            tCombo.append_text(tLabel)
        tCombo.connect("changed", self._onWidgetChanged)
        return tCombo

    def _onWidgetChanged(self, *ignored):
        if self.mUpdating:
            return
        tShelf = max(self.mShelf.get_active(), 0)
        tTheme = max(self.mTheme.get_active(), 0)
        self.mOnChange(dataclasses.replace(
            self.mSettingsSource(),
            mColumns=self.mColumns.get_value_as_int(),
            mRows=self.mRows.get_value_as_int(),
            mScale=self.mScale.get_value_as_int(),
            mShelfMode=self.SHELF_CHOICES[tShelf][0],
            mShowNames=self.mShowNames.get_active(),
            mTheme=self.THEME_CHOICES[tTheme][0],
        ))

    @staticmethod
    def _onButton(button, action: Callable[[], None]):
        action()

    def _onDelete(self, *ignored) -> bool:
        self.hide()
        return True

    def _onKey(self, widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False
