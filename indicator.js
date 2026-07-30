import GObject from 'gi://GObject';
import St from 'gi://St';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {createSegmentedControl} from './ui.js';
import {PasswordsTab} from './passwordsTab.js';
import {TotpTab} from './totpTab.js';
import {cancelClipboardTimeout} from './utils.js';

const TAB_PASSWORDS = 'Passwords';
const TAB_TOTP = 'TOTP';

export const PassmateIndicator = GObject.registerClass(
class PassmateIndicator extends PanelMenu.Button {
    _init(settings, openPrefsFn) {
        super._init(0.0, 'Passmate');

        this._settings = settings;
        this._openPrefsFn = openPrefsFn;
        this._activeTab = null;
        this._focusTimeoutId = null;

        const box = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        box.add_child(new St.Icon({
            icon_name: 'dialog-password-symbolic',
            style_class: 'system-status-icon',
        }));
        this.add_child(box);

        this.menu.box.style = 'max-height: 1400px;';

        this._buildLayout();

        this.menu.connect('open-state-changed', (_menu, isOpen) => {
            if (isOpen) {
                this._activateTab(this._activeTab || this._getDefaultTab());
            } else {
                this._deactivateAll();
            }
        });

        Main.wm.addKeybinding(
            'show-menu-keybinding',
            this._settings,
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.ALL,
            () => {
                this.menu.open();
            }
        );
    }

    _getDefaultTab() {
        const defaultTab = this._settings.get_string('default-tab');
        return defaultTab === 'totp' ? TAB_TOTP : TAB_PASSWORDS;
    }

    _buildLayout() {
        const segmentControl = createSegmentedControl(
            [TAB_PASSWORDS, TAB_TOTP],
            (label) => this._onTabSelected(label)
        );
        this.menu.addMenuItem(segmentControl);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const contentItem = new PopupMenu.PopupBaseMenuItem({
            reactive: false,
            can_focus: false,
            style_class: 'popup-menu-item passmate-content-wrapper',
        });

        const contentStack = new St.BoxLayout({
            vertical: false,
            x_expand: true,
            style: 'min-height: 600px;',
        });

        this._passwordsContentBox = new St.BoxLayout({
            vertical: true,
            x_expand: true,
        });

        this._totpContentBox = new St.BoxLayout({
            vertical: true,
            x_expand: true,
        });

        this._totpContentBox.hide();

        contentStack.add_child(this._passwordsContentBox);
        contentStack.add_child(this._totpContentBox);

        contentItem.add_child(contentStack);
        this.menu.addMenuItem(contentItem);

        const closeFn = () => this.menu.close();

        this._passwordsTab = new PasswordsTab(
            this._passwordsContentBox,
            this._settings,
            closeFn,
            this._openPrefsFn
        );

        this._totpTab = new TotpTab(
            this._totpContentBox,
            this._settings,
            closeFn
        );

        const defaultTab = this._getDefaultTab();
        this._activeTab = defaultTab;

        const segmentContainer = segmentControl.get_first_child();
        if (segmentContainer && defaultTab === TAB_TOTP) {
            const children = segmentContainer.get_children();
            children.forEach(c => c.remove_style_pseudo_class('checked'));
            if (children.length > 1)
                children[1].add_style_pseudo_class('checked');

            this._passwordsContentBox.hide();
            this._totpContentBox.show();
        }
    }

    _onTabSelected(label) {
        if (label === this._activeTab)
            return;

        this._deactivateAll();
        this._activeTab = label;
        this._activateTab(label);
    }

    _activateTab(label) {
        this._activeTab = label;

        if (label === TAB_PASSWORDS) {
            this._passwordsContentBox.show();
            this._totpContentBox.hide();
            this._passwordsTab.activate();
        } else {
            this._passwordsContentBox.hide();
            this._totpContentBox.show();
            this._totpTab.activate();
        }
    }

    _deactivateAll() {
        this._passwordsTab.deactivate();
        this._totpTab.deactivate();
    }

    destroy() {
        this._deactivateAll();

        if (this._focusTimeoutId) {
            GLib.source_remove(this._focusTimeoutId);
            this._focusTimeoutId = null;
        }

        this._passwordsTab.destroy();
        this._totpTab.destroy();
        cancelClipboardTimeout();
        Main.wm.removeKeybinding('show-menu-keybinding');

        super.destroy();
    }
});
