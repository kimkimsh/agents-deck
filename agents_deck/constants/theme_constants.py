class ThemeConstants:
    """Colours of everything the overlay draws besides the sprites, as RGBA."""

    # Opaque enough that text in the window behind does not read through;
    # GTK 3 cannot blur what is behind a window.
    PLATE_DARK = (28 / 255.0, 27 / 255.0, 34 / 255.0, 0.94)
    PLATE_LIGHT = (246 / 255.0, 245 / 255.0, 250 / 255.0, 0.94)

    TOOLTIP_BACKGROUND_DARK = (28 / 255.0, 27 / 255.0, 34 / 255.0, 0.96)
    TOOLTIP_BACKGROUND_LIGHT = (251 / 255.0, 250 / 255.0, 253 / 255.0, 0.97)
    TOOLTIP_TEXT_DARK = (233 / 255.0, 230 / 255.0, 242 / 255.0, 1.0)
    TOOLTIP_TEXT_LIGHT = (39 / 255.0, 36 / 255.0, 54 / 255.0, 1.0)
    TOOLTIP_MUTED_DARK = (233 / 255.0, 230 / 255.0, 242 / 255.0, 0.68)
    TOOLTIP_MUTED_LIGHT = (39 / 255.0, 36 / 255.0, 54 / 255.0, 0.66)
    TOOLTIP_BORDER_DARK = (1.0, 1.0, 1.0, 0.10)
    TOOLTIP_BORDER_LIGHT = (39 / 255.0, 36 / 255.0, 54 / 255.0, 0.14)

    NAME_TEXT_DARK = (233 / 255.0, 230 / 255.0, 242 / 255.0, 1.0)
    NAME_TEXT_LIGHT = (39 / 255.0, 36 / 255.0, 54 / 255.0, 1.0)
    NAME_HALO_DARK = (20 / 255.0, 19 / 255.0, 26 / 255.0, 0.85)
    NAME_HALO_LIGHT = (251 / 255.0, 250 / 255.0, 253 / 255.0, 0.9)

    GNOME_INTERFACE_SCHEMA = "org.gnome.desktop.interface"
    GNOME_COLOR_SCHEME_KEY = "color-scheme"
    GNOME_PREFER_DARK = "prefer-dark"
    DARK_THEME_SUFFIX = "-dark"
