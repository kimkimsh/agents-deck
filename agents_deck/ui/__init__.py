import gi

# Every module that touches GTK lives in this package, so pinning the
# typelib versions here runs before any of them imports gi.repository.
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
