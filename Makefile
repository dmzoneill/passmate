UUID = passmate@dmzoneill.com
INSTALL_DIR = $(HOME)/.local/share/gnome-shell/extensions/$(UUID)

.PHONY: all install uninstall schemas reload clean lint help dev dev-no-ext

help:
	@echo "Passmate GNOME Shell Extension"
	@echo ""
	@echo "  make install      - Copy extension to ~/.local/share/gnome-shell/extensions/"
	@echo "  make uninstall    - Remove installed extension"
	@echo "  make schemas      - Compile GSettings schemas"
	@echo "  make dev          - Symlink + launch devkit session with extension enabled"
	@echo "  make dev-no-ext   - Launch devkit session without extensions (baseline)"
	@echo "  make reload       - Restart GNOME Shell (X11 only)"
	@echo "  make lint         - Run eslint on JavaScript files"
	@echo "  make clean        - Remove compiled schemas"
	@echo ""

all: schemas install

schemas:
	glib-compile-schemas schemas/

install: schemas
	mkdir -p $(INSTALL_DIR)/schemas
	cp metadata.json $(INSTALL_DIR)/
	cp extension.js $(INSTALL_DIR)/
	cp indicator.js $(INSTALL_DIR)/
	cp passwordsTab.js $(INSTALL_DIR)/
	cp totpTab.js $(INSTALL_DIR)/
	cp ui.js $(INSTALL_DIR)/
	cp utils.js $(INSTALL_DIR)/
	cp prefs.js $(INSTALL_DIR)/
	cp stylesheet.css $(INSTALL_DIR)/
	cp schemas/*.xml $(INSTALL_DIR)/schemas/
	cp schemas/gschemas.compiled $(INSTALL_DIR)/schemas/

uninstall:
	rm -rf $(INSTALL_DIR)

# Symlink source dir and launch nested GNOME Shell devkit session.
# No need to restart your real GNOME Shell — changes are live in the nested window.
dev: schemas
	@ln -sfn $(CURDIR) $(INSTALL_DIR)
	@echo "Symlinked $(UUID) → $(CURDIR)"
	@rm -f /run/user/$$(id -u)/gnome-shell-disable-extensions
	dbus-run-session -- bash -c '\
		rm -f /run/user/$$(id -u)/gnome-shell-disable-extensions; \
		gsettings set org.gnome.shell enabled-extensions "[\"$(UUID)\"]"; \
		exec gnome-shell --wayland --no-x11 --devkit'

dev-no-ext: schemas
	@echo "Launching devkit without extensions (baseline test)"
	dbus-run-session -- bash -c '\
		gsettings set org.gnome.shell enabled-extensions "[]"; \
		exec gnome-shell --wayland --no-x11 --devkit'

reload:
	@echo "Restarting GNOME Shell..."
	@dbus-send --session --type=method_call \
		--dest=org.gnome.Shell /org/gnome/Shell \
		org.gnome.Shell.Eval string:'global.reexec_self()'
	@echo "Done. If on Wayland, log out and log back in."

lint:
	@command -v eslint >/dev/null 2>&1 && eslint *.js || echo "eslint not found, skipping"

clean:
	rm -f schemas/gschemas.compiled
