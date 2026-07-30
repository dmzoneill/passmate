import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const COL_SERVICE = 150;
const COL_ACCOUNT = 200;
const COL_CODE = 100;
const COL_COPY = 40;

export function createIconButton(iconName, styleClass, onClick) {
    const icon = new St.Icon({icon_name: iconName, icon_size: 16});
    const button = new St.Button({child: icon, style_class: styleClass});
    if (onClick)
        button.connect('clicked', onClick);
    return button;
}

export function createSegmentedControl(labels, onSelect) {
    const container = new St.BoxLayout({
        style_class: 'passmate-segment-container',
        x_expand: true,
    });

    for (const label of labels) {
        const button = new St.Button({
            label,
            style_class: 'passmate-segment-button',
            x_expand: true,
        });

        button.connect('clicked', () => {
            container.get_children().forEach(c =>
                c.remove_style_pseudo_class('checked'));
            button.add_style_pseudo_class('checked');
            onSelect(label);
        });

        container.add_child(button);
    }

    container.get_first_child().add_style_pseudo_class('checked');

    const wrapper = new PopupMenu.PopupBaseMenuItem({
        reactive: false,
        can_focus: false,
        style_class: 'popup-menu-item passmate-segment-wrapper',
    });
    wrapper.add_child(container);
    return wrapper;
}

export function createSpinner(message = 'Loading...') {
    const box = new St.BoxLayout({
        style_class: 'passmate-spinner-box',
        x_expand: true,
        x_align: Clutter.ActorAlign.CENTER,
        y_align: Clutter.ActorAlign.CENTER,
    });

    box.add_child(new St.Icon({
        icon_name: 'process-working-symbolic',
        icon_size: 16,
        style_class: 'passmate-spinner-icon',
    }));

    box.add_child(new St.Label({
        text: message,
        style_class: 'passmate-spinner-label',
        y_align: Clutter.ActorAlign.CENTER,
    }));

    return box;
}

export function createHeaderBox(currentDirectory, onUpClicked) {
    const upButton = createIconButton('go-up-symbolic', 'passmate-up-button', onUpClicked);
    upButton.style = 'margin-right: 6px;';

    const currentLabel = new St.Label({
        text: currentDirectory,
        style_class: 'passmate-header-label',
        y_align: Clutter.ActorAlign.CENTER,
    });

    const headerBox = new St.BoxLayout({
        vertical: false,
        style_class: 'passmate-header-box',
    });
    headerBox.add_child(upButton);
    headerBox.add_child(currentLabel);

    const headerItem = new PopupMenu.PopupBaseMenuItem({
        reactive: false,
        can_focus: false,
        style_class: 'popup-menu-item passmate-header-wrapper',
    });
    headerItem.add_child(headerBox);
    return headerItem;
}

export function createScrollWrapper(contentBox) {
    const scrollView = new St.ScrollView({
        overlay_scrollbars: false,
        style_class: 'passmate-scrollview',
        x_expand: true,
        reactive: true,
        can_focus: true,
        track_hover: true,
    });

    scrollView.set_child(contentBox);

    const wrapper = new PopupMenu.PopupBaseMenuItem({
        reactive: false,
        can_focus: false,
        style_class: 'popup-menu-item passmate-scroll-wrapper',
    });
    wrapper.add_child(scrollView);
    return wrapper;
}

export function createEntryRow(label, iconName, onActivate) {
    const row = new St.BoxLayout({
        style_class: 'passmate-menu-item',
        reactive: true,
        can_focus: true,
        track_hover: true,
    });

    row.add_child(new St.Icon({
        icon_name: iconName,
        icon_size: 16,
        style: 'margin-right: 8px;',
        y_align: Clutter.ActorAlign.CENTER,
    }));
    row.add_child(new St.Label({
        text: label,
        x_expand: true,
        y_align: Clutter.ActorAlign.CENTER,
    }));

    if (onActivate) {
        row.connect('button-release-event', () => {
            onActivate();
            return true;
        });
    }

    return row;
}

export function createFooterBox(searchEntry, onSettingsClicked) {
    const footerBox = new St.BoxLayout({
        style_class: 'passmate-footer-box',
        vertical: false,
        x_expand: true,
    });

    const searchEntryBox = new St.BoxLayout({
        style_class: 'passmate-search-entry-box',
        vertical: false,
        x_expand: true,
        clip_to_allocation: true,
    });

    const searchIcon = new St.Icon({
        icon_name: 'edit-find-symbolic',
        icon_size: 16,
        style_class: 'passmate-search-icon',
    });
    searchIcon.style = 'margin-right: 8px;';

    searchEntryBox.add_child(searchIcon);
    searchEntryBox.add_child(searchEntry);

    const settingsButton = new St.Button({
        style_class: 'passmate-button passmate-settings-button',
        child: new St.Icon({
            icon_name: 'preferences-system-windows-symbolic',
            icon_size: 16,
            style_class: 'popup-menu-icon',
        }),
    });
    settingsButton.style = 'margin-left: 8px;';

    if (onSettingsClicked)
        settingsButton.connect('clicked', onSettingsClicked);

    footerBox.add_child(searchEntryBox);
    footerBox.add_child(settingsButton);

    const footerItem = new PopupMenu.PopupBaseMenuItem({
        reactive: false,
        can_focus: false,
        style_class: 'popup-menu-item passmate-footer-wrapper',
    });
    footerItem.add_child(footerBox);
    return footerItem;
}

export function createTotpRow(entry, onCopy) {
    const row = new St.BoxLayout({
        x_expand: true,
        style_class: 'passmate-totp-row',
        reactive: true,
        track_hover: true,
    });

    row.add_child(new St.Label({
        text: entry.service,
        width: COL_SERVICE,
        style_class: 'passmate-totp-cell',
        y_align: Clutter.ActorAlign.CENTER,
    }));

    row.add_child(new St.Label({
        text: entry.username,
        width: COL_ACCOUNT,
        style_class: 'passmate-totp-cell',
        y_align: Clutter.ActorAlign.CENTER,
    }));

    const codeLabel = new St.Label({
        text: entry.current || '------',
        style_class: 'passmate-totp-code',
        width: COL_CODE,
        y_align: Clutter.ActorAlign.CENTER,
    });
    row.add_child(codeLabel);

    const copyBtn = new St.Button({
        style_class: 'passmate-totp-copy-btn',
        width: COL_COPY,
        child: new St.Icon({
            icon_name: 'edit-copy-symbolic',
            icon_size: 14,
        }),
    });
    copyBtn.connect('clicked', () => {
        const code = codeLabel.get_text();
        if (code && code !== '------')
            onCopy(code);
    });
    row.add_child(copyBtn);

    return {item: row, codeLabel};
}

export function createTotpHeader() {
    const headerBox = new St.BoxLayout({
        x_expand: true,
        style_class: 'passmate-totp-header-row',
    });

    const columns = [
        ['Service', COL_SERVICE],
        ['Account', COL_ACCOUNT],
        ['Code', COL_CODE],
        ['', COL_COPY],
    ];

    for (const [label, width] of columns) {
        headerBox.add_child(new St.Label({
            text: label,
            width,
            style_class: 'passmate-totp-header',
        }));
    }

    return headerBox;
}
