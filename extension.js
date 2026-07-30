import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {PassmateIndicator} from './indicator.js';
import {cancelClipboardTimeout} from './utils.js';

export default class PassmateExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._indicator = new PassmateIndicator(
            this._settings,
            () => this.openPreferences()
        );
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        cancelClipboardTimeout();
        this._indicator?.destroy();
        this._indicator = null;
        this._settings = null;
    }
}
