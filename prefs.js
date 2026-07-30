import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class PassmatePreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Passmate',
            icon_name: 'dialog-password-symbolic',
        });

        const generalGroup = new Adw.PreferencesGroup({
            title: 'General',
        });

        const defaultTabRow = new Adw.ComboRow({
            title: 'Default Tab',
            subtitle: 'Which tab opens by default',
        });
        const tabModel = new Gtk.StringList();
        tabModel.append('Passwords');
        tabModel.append('TOTP');
        defaultTabRow.set_model(tabModel);

        const currentDefault = settings.get_string('default-tab');
        defaultTabRow.set_selected(currentDefault === 'totp' ? 1 : 0);
        defaultTabRow.connect('notify::selected', () => {
            settings.set_string('default-tab',
                defaultTabRow.get_selected() === 1 ? 'totp' : 'passwords');
        });
        generalGroup.add(defaultTabRow);

        const clipboardRow = new Adw.SpinRow({
            title: 'Clipboard Timeout',
            subtitle: 'Seconds before clipboard is cleared (0 = disabled)',
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 300,
                step_increment: 5,
                page_increment: 15,
                value: settings.get_int('clipboard-timeout'),
            }),
        });
        clipboardRow.connect('notify::value', () => {
            settings.set_int('clipboard-timeout', clipboardRow.get_value());
        });
        generalGroup.add(clipboardRow);

        page.add(generalGroup);

        const totpGroup = new Adw.PreferencesGroup({
            title: 'TOTP',
        });

        const totpEntryRow = new Adw.EntryRow({
            title: 'Pass Entry Name',
            text: settings.get_string('totp-pass-entry'),
        });
        totpEntryRow.connect('changed', () => {
            settings.set_string('totp-pass-entry', totpEntryRow.get_text());
        });
        totpGroup.add(totpEntryRow);

        page.add(totpGroup);

        const pathGroup = new Adw.PreferencesGroup({
            title: 'Password Store',
        });

        const storePathRow = new Adw.EntryRow({
            title: 'Custom Path',
            text: settings.get_string('password-store-path'),
        });
        storePathRow.connect('changed', () => {
            settings.set_string('password-store-path', storePathRow.get_text());
        });
        pathGroup.add(storePathRow);

        const pathHint = new Gtk.Label({
            label: 'Leave empty to use ~/.password-store or $PASSWORD_STORE_DIR',
            halign: Gtk.Align.START,
            margin_start: 12,
            margin_top: 4,
        });
        pathHint.add_css_class('dim-label');
        pathHint.add_css_class('caption');
        pathGroup.add(pathHint);

        page.add(pathGroup);

        window.add(page);
    }
}
