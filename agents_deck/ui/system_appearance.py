from typing import Callable, List, Optional, Tuple

from gi.repository import Gio, GObject, Gtk

from agents_deck.constants.theme_constants import ThemeConstants


class SystemAppearance:
    """The desktop's dark-mode and reduce-motion preferences, followed live.

    GNOME keeps the colour scheme in org.gnome.desktop.interface; elsewhere
    the GTK theme name is the only hint. Reduced motion is GTK's
    gtk-enable-animations, which GNOME's "Animations" switch controls.
    UI thread only.
    """

    mOnChanged: Callable[[], None]
    mInterface: Optional[Gio.Settings]
    mGtkSettings: Optional[Gtk.Settings]
    mHandlers: List[Tuple[GObject.Object, int]]

    def __init__(self, onChanged: Callable[[], None]):
        self.mOnChanged = onChanged
        self.mInterface = None
        self.mHandlers = []
        tSource = Gio.SettingsSchemaSource.get_default()
        tSchema = tSource.lookup(ThemeConstants.GNOME_INTERFACE_SCHEMA, True) if tSource is not None else None
        if tSchema is not None and tSchema.has_key(ThemeConstants.GNOME_COLOR_SCHEME_KEY):
            self.mInterface = Gio.Settings.new(ThemeConstants.GNOME_INTERFACE_SCHEMA)
            self.mHandlers.append((self.mInterface, self.mInterface.connect("changed::" + ThemeConstants.GNOME_COLOR_SCHEME_KEY, self._onSettingChanged)))
        self.mGtkSettings = Gtk.Settings.get_default()
        if self.mGtkSettings is not None:
            self.mHandlers.append((self.mGtkSettings, self.mGtkSettings.connect("notify::gtk-enable-animations", self._onSettingChanged)))
            self.mHandlers.append((self.mGtkSettings, self.mGtkSettings.connect("notify::gtk-theme-name", self._onSettingChanged)))

    def detach(self):
        """Stops calling back; Gtk.Settings outlives the window that owns this."""
        for tSource, tHandler in self.mHandlers:
            tSource.disconnect(tHandler)
        self.mHandlers = []

    def prefersDark(self) -> bool:
        if self.mInterface is not None:
            return self.mInterface.get_string(ThemeConstants.GNOME_COLOR_SCHEME_KEY) == ThemeConstants.GNOME_PREFER_DARK
        if self.mGtkSettings is None:
            return False
        tName = self.mGtkSettings.props.gtk_theme_name or ""
        return bool(self.mGtkSettings.props.gtk_application_prefer_dark_theme) or tName.lower().endswith(ThemeConstants.DARK_THEME_SUFFIX)

    def reducedMotion(self) -> bool:
        return self.mGtkSettings is not None and not self.mGtkSettings.props.gtk_enable_animations

    def _onSettingChanged(self, *ignored):
        self.mOnChanged()
