# Builds agents-deck into one executable file and installs it for the
# current user. No root, and nothing is written outside $(HOME).
#
#   make             build into build/
#   make install     install the program, icon, app-menu entry and desktop launcher
#   make uninstall   remove what install added (settings are kept)
#   make clean       delete build/

# The executable runs on this interpreter; it must see the system GTK bindings.
PYTHON ?= /usr/bin/python3
PREFIX ?= $(HOME)/.local
BINDIR := $(PREFIX)/bin
APPDIR := $(PREFIX)/share/applications
ICONDIR := $(PREFIX)/share/icons
BUILD := build

# The app's identity lives in AppConstants; read it rather than restate it.
APP_ID := $(shell $(PYTHON) -c 'from agents_deck.constants.app_constants import AppConstants; print(AppConstants.APP_ID)')
APP_NAME := $(shell $(PYTHON) -c 'from agents_deck.constants.app_constants import AppConstants; print(AppConstants.APP_NAME)')
# xdg-user-dir prints $(HOME) itself when no desktop folder is configured.
DESKTOP_DIR := $(shell xdg-user-dir DESKTOP 2>/dev/null)

SOURCES := $(shell find agents_deck -name '*.py')
EXECUTABLE := $(BUILD)/$(APP_NAME)
DESKTOP_ENTRY := $(BUILD)/$(APP_ID).desktop
ICONS_STAMP := $(BUILD)/icons.stamp

.PHONY: all install uninstall clean

all: $(EXECUTABLE) $(ICONS_STAMP) $(DESKTOP_ENTRY)

# A zipapp: the package plus its own __main__.py, behind a shebang line.
$(EXECUTABLE): $(SOURCES)
	rm -rf $(BUILD)/zipapp
	mkdir -p $(BUILD)/zipapp
	cp -r agents_deck $(BUILD)/zipapp/
	find $(BUILD)/zipapp -name __pycache__ -prune -exec rm -rf {} +
	cp agents_deck/__main__.py $(BUILD)/zipapp/__main__.py
	$(PYTHON) -m zipapp $(BUILD)/zipapp --python=$(PYTHON) --compress --output=$@

$(ICONS_STAMP): tools/render_app_icon.py $(SOURCES)
	rm -rf $(BUILD)/icons
	$(PYTHON) -m tools.render_app_icon $(BUILD)/icons
	touch $@

$(DESKTOP_ENTRY): data/desktop-entry.in
	mkdir -p $(BUILD)
	sed -e 's|@APP_ID@|$(APP_ID)|g' -e 's|@APP_NAME@|$(APP_NAME)|g' -e 's|@BINDIR@|$(BINDIR)|g' $< > $@
	if command -v desktop-file-validate >/dev/null; then desktop-file-validate $@; fi

install: all
	install -Dm755 $(EXECUTABLE) $(BINDIR)/$(APP_NAME)
	mkdir -p $(ICONDIR)
	cp -r $(BUILD)/icons/hicolor $(ICONDIR)/
# A newer folder time makes GTK distrust any icon cache that predates the new icon.
	touch $(ICONDIR)/hicolor
	install -Dm644 $(DESKTOP_ENTRY) $(APPDIR)/$(APP_ID).desktop
# The desktop icons extension runs a launcher only when it is executable and trusted.
	if [ -d "$(DESKTOP_DIR)" ] && [ "$(DESKTOP_DIR)" != "$(HOME)" ]; then \
		install -m755 $(DESKTOP_ENTRY) "$(DESKTOP_DIR)/$(APP_NAME).desktop"; \
		gio set "$(DESKTOP_DIR)/$(APP_NAME).desktop" metadata::trusted true \
			|| echo "Could not mark the desktop launcher trusted: right-click it and choose Allow Launching."; \
	fi

uninstall:
	rm -f $(BINDIR)/$(APP_NAME) $(APPDIR)/$(APP_ID).desktop
	rm -f $(ICONDIR)/hicolor/*/apps/$(APP_ID).png
	if [ -d "$(DESKTOP_DIR)" ] && [ "$(DESKTOP_DIR)" != "$(HOME)" ]; then rm -f "$(DESKTOP_DIR)/$(APP_NAME).desktop"; fi

clean:
	rm -rf $(BUILD)
