import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {
    enumeratePasswordStoreEntriesAsync,
    formatEntryLabel,
    sanitizePassRoute,
    resolveParentDir,
    filterMatchingEntries,
    copyToClipboardWithTimeout,
    execAsync,
    debounce,
    logDebug,
    getPasswordStorePath,
} from './utils.js';

import {
    createHeaderBox,
    createScrollWrapper,
    createEntryRow,
    createFooterBox,
    createSpinner,
} from './ui.js';

export class PasswordsTab {
    constructor(contentBox, settings, closeFn, openPrefsFn) {
        this._outerBox = contentBox;
        this._settings = settings;
        this._closeFn = closeFn;
        this._openPrefsFn = openPrefsFn;
        this._currentDirectory = '/';
        this._allEntries = [];
        this._contentBox = null;
        this._searchEntry = null;
        this._headerItem = null;
        this._scrollWrapper = null;
        this._footerItem = null;
        this._focusTimeoutId = null;
        this._active = false;

        this._debouncedFilter = debounce((query) => {
            this._filterEntries(query);
        }, 300);
    }

    activate() {
        this._active = true;
        this._drawDirectory();
        this._focusSearch();
    }

    deactivate() {
        this._active = false;
        this._debouncedFilter.cancel();
        if (this._focusTimeoutId) {
            GLib.source_remove(this._focusTimeoutId);
            this._focusTimeoutId = null;
        }
    }

    destroy() {
        this.deactivate();
    }

    _focusSearch() {
        if (this._focusTimeoutId)
            GLib.source_remove(this._focusTimeoutId);

        this._focusTimeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            this._focusTimeoutId = null;
            if (this._searchEntry && this._searchEntry.mapped)
                this._searchEntry.grab_key_focus();
            return GLib.SOURCE_REMOVE;
        });
    }

    async _drawDirectory() {
        this._outerBox.destroy_all_children();

        this._headerItem = createHeaderBox(this._currentDirectory, () => {
            const upDir = resolveParentDir(this._currentDirectory);
            this._changeDir(upDir);
        });
        this._outerBox.add_child(this._headerItem);

        this._contentBox = new St.BoxLayout({
            vertical: true,
            style_class: 'passmate-scrollbox',
        });

        this._scrollWrapper = createScrollWrapper(this._contentBox);
        this._outerBox.add_child(this._scrollWrapper);

        this._contentBox.destroy_all_children();
        this._contentBox.add_child(createSpinner('Loading passwords...'));

        try {
            this._allEntries = await enumeratePasswordStoreEntriesAsync(
                this._currentDirectory, this._settings);
        } catch (e) {
            logDebug(`Directory enum failed: ${e}`);
            this._allEntries = [];
        }

        if (!this._active)
            return;

        this._filterEntries('');
        this._drawFooter();
        this._focusSearch();
    }

    _drawFooter() {
        if (this._footerItem) {
            this._outerBox.remove_child(this._footerItem);
            this._footerItem = null;
        }

        this._searchEntry = new St.Entry({
            style_class: 'passmate-search-entry',
            hint_text: 'Search passwords...',
            can_focus: true,
            x_expand: true,
        });

        this._searchEntry.clutter_text.connect('text-changed', () => {
            const query = this._searchEntry.get_text();
            this._debouncedFilter(query);
        });

        this._footerItem = createFooterBox(this._searchEntry, () => {
            if (this._openPrefsFn) {
                try {
                    this._openPrefsFn();
                } catch (e) {
                    logDebug(`Failed to open settings: ${e}`);
                }
            }
        });

        this._outerBox.add_child(this._footerItem);
    }

    _filterEntries(query) {
        if (!this._contentBox)
            return;

        this._contentBox.destroy_all_children();

        const filtered = filterMatchingEntries(this._allEntries, query);
        for (const item of filtered) {
            const label = formatEntryLabel(item.name, item.isDir);
            const icon = item.isDir ? 'folder-symbolic' : 'changes-prevent-symbolic';

            const row = createEntryRow(label, icon, () => {
                if (item.isDir) {
                    this._changeDir(`${this._currentDirectory}${item.name}/`);
                } else {
                    const cleanRoute = sanitizePassRoute(this._currentDirectory + item.name);
                    this._getPassword(cleanRoute);
                }
            });

            this._contentBox.add_child(row);
        }

        if (filtered.length === 0) {
            this._contentBox.add_child(new St.Label({
                text: 'No matching entries',
                style_class: 'passmate-empty-label',
            }));
        }
    }

    async _changeDir(dir) {
        const storePath = getPasswordStorePath(this._settings);
        const path = `${storePath}/${dir}`;
        const file = Gio.File.new_for_path(path);

        try {
            const info = file.query_info('standard::type',
                Gio.FileQueryInfoFlags.NONE, null);
            if (info.get_file_type() !== Gio.FileType.DIRECTORY) {
                logDebug(`Not a valid directory: ${path}`);
                return;
            }
        } catch (e) {
            logDebug(`Cannot access directory: ${path}`);
            return;
        }

        this._currentDirectory = dir;
        await this._drawDirectory();
    }

    async _getPassword(route) {
        try {
            const output = await execAsync(['pass', 'show', route]);
            const password = output.split('\n')[0].trim();

            const timeout = this._settings.get_int('clipboard-timeout');
            copyToClipboardWithTimeout(password, timeout);

            logDebug(`Password copied: ${route}`);
            Main.notify('Passmate', `Password for "${route}" copied to clipboard.`);
        } catch (e) {
            logDebug(`Failed to get password for ${route}: ${e.message}`);
            Main.notify('Passmate', `Failed to copy password for "${route}".`);
        }

        this._closeFn();
    }
}
