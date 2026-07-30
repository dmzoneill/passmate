import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {
    execAsync,
    copyToClipboardWithTimeout,
    logDebug,
} from './utils.js';

import {
    createSpinner,
    createTotpRow,
    createTotpHeader,
    createScrollWrapper,
} from './ui.js';

export class TotpTab {
    constructor(contentBox, settings, closeFn) {
        this._outerBox = contentBox;
        this._settings = settings;
        this._closeFn = closeFn;
        this._timerId = null;
        this._lastPeriod = -1;
        this._countdownLabel = null;
        this._entries = null;
        this._codeLabels = [];
        this._cancellable = null;
        this._active = false;
        this._scrollContentBox = null;
    }

    activate() {
        this._active = true;
        this._cancellable = new Gio.Cancellable();
        this._lastPeriod = Math.floor(Date.now() / 1000 / 30);
        this._loadAndRender();
    }

    deactivate() {
        this._active = false;
        this._stopTimer();
        if (this._cancellable) {
            this._cancellable.cancel();
            this._cancellable = null;
        }
    }

    destroy() {
        this.deactivate();
        this._entries = null;
        this._codeLabels = [];
    }

    async _loadAndRender() {
        this._outerBox.destroy_all_children();

        const spinnerBox = createSpinner('Loading TOTP codes...');
        this._outerBox.add_child(spinnerBox);

        try {
            await this._fetchEntries();
        } catch (e) {
            logDebug(`TOTP fetch failed: ${e}`);
            if (!this._active) return;
            this._outerBox.destroy_all_children();
            this._outerBox.add_child(new St.Label({
                text: 'Failed to load TOTP entries',
                style_class: 'passmate-empty-label',
            }));
            return;
        }

        if (!this._active) return;

        this._buildUI();
        await this._fetchCodes();

        if (!this._active) return;

        this._startTimer();
    }

    async _fetchEntries() {
        const passEntry = this._settings.get_string('totp-pass-entry');
        const output = await execAsync(['pass', 'show', passEntry], null, this._cancellable);

        const lines = output.trim().split('\n').filter(l => l.includes('otpauth://'));
        lines.sort((a, b) => a.localeCompare(b));

        this._entries = lines.map(line => {
            const nameMatch = line.match(/otpauth:\/\/totp\/([^?]+)/);
            const secretMatch = line.match(/secret=([^&\s]+)/);
            const digitsMatch = line.match(/digits=([^&\s]+)/);

            const entryName = nameMatch ? decodeURIComponent(nameMatch[1]) : '';
            const secret = secretMatch ? secretMatch[1] : '';
            const digits = digitsMatch ? digitsMatch[1] : '6';

            let service, username;
            if (entryName.includes(':')) {
                const parts = entryName.split(':');
                service = parts[0];
                username = parts.slice(1).join(':');
            } else if (entryName.includes('/')) {
                const parts = entryName.split('/');
                service = parts[0];
                username = parts.slice(1).join('/');
            } else {
                service = '-';
                username = entryName;
            }

            return {
                service: service.trim(),
                username: username.trim(),
                secret,
                digits,
                current: '------',
            };
        });
    }

    async _fetchCodes() {
        if (!this._entries || this._entries.length === 0)
            return;

        const promises = this._entries.map((entry, index) => {
            if (!entry.secret)
                return Promise.resolve();

            return execAsync(
                ['oathtool', '-s', '30s', '-d', entry.digits, '-b', '--totp', entry.secret],
                null,
                this._cancellable
            ).then(output => {
                const code = output.trim().split('\n')[0] || '------';
                entry.current = code;
                if (this._active && this._codeLabels[index])
                    this._codeLabels[index].set_text(code);
            }).catch(() => {
                entry.current = '------';
            });
        });

        await Promise.allSettled(promises);
    }

    _buildUI() {
        this._outerBox.destroy_all_children();
        this._codeLabels = [];

        const epoch = Math.floor(Date.now() / 1000);
        const remainder = 30 - (epoch % 30);

        this._countdownLabel = new St.Label({
            text: `Next refresh: ${remainder}s`,
            style_class: 'passmate-totp-countdown',
            x_expand: true,
            x_align: Clutter.ActorAlign.CENTER,
        });
        this._outerBox.add_child(this._countdownLabel);

        const headerItem = createTotpHeader();
        this._outerBox.add_child(headerItem);

        this._scrollContentBox = new St.BoxLayout({
            vertical: true,
            style_class: 'passmate-scrollbox',
        });

        if (!this._entries || this._entries.length === 0) {
            this._scrollContentBox.add_child(new St.Label({
                text: 'No TOTP entries found',
                style_class: 'passmate-empty-label',
            }));
        } else {
            for (const entry of this._entries) {
                const {item, codeLabel} = createTotpRow(entry, (code) => {
                    this._copyCode(code);
                });
                this._codeLabels.push(codeLabel);
                this._scrollContentBox.add_child(item);
            }
        }

        const scrollWrapper = createScrollWrapper(this._scrollContentBox);
        this._outerBox.add_child(scrollWrapper);
    }

    _copyCode(code) {
        const timeout = this._settings.get_int('clipboard-timeout');
        copyToClipboardWithTimeout(code, timeout);
        Main.notify('Passmate', 'TOTP code copied to clipboard.');
        this._closeFn();
    }

    _startTimer() {
        this._stopTimer();
        this._timerId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
            if (!this._active)
                return GLib.SOURCE_REMOVE;

            const epoch = Math.floor(Date.now() / 1000);
            const remainder = 30 - (epoch % 30);
            const period = Math.floor(epoch / 30);

            if (this._countdownLabel)
                this._countdownLabel.set_text(`Next refresh: ${remainder}s`);

            if (period !== this._lastPeriod) {
                this._lastPeriod = period;
                this._refreshCodes();
            }

            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopTimer() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
    }

    async _refreshCodes() {
        if (this._cancellable)
            this._cancellable.cancel();

        this._cancellable = new Gio.Cancellable();
        await this._fetchCodes();
    }
}
