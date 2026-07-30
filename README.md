# Passmate

Combined GNU Pass password manager and TOTP authenticator for GNOME Shell.

Browse your password store and copy TOTP codes from a single panel indicator with tabbed navigation.

![GNOME Shell 46-52](https://img.shields.io/badge/GNOME_Shell-46--52-blue)
![License](https://img.shields.io/badge/License-Apache_2.0-green)

## Features

- **Tabbed UI** with segmented control — switch between Passwords and TOTP
- **Password browser** — navigate your `~/.password-store` directory tree, click to copy
- **TOTP codes** — async generation via `oathtool`, 30-second auto-refresh, click to copy
- **Fuzzy search** with Levenshtein distance matching and 300ms debounce
- **Fully async** — no UI blocking, loading spinners while data fetches
- **Clipboard auto-clear** — configurable timeout (default 45 seconds)
- **Keyboard shortcut** — `Super+W` to open (configurable)
- **Preferences UI** — default tab, clipboard timeout, TOTP entry name, store path

## Supersedes

This extension replaces and combines two earlier projects, which are now archived:

- **[authy-gnupass-totp](https://github.com/dmzoneill/authy-gnupass-totp)** — TOTP code viewer (archived)
- **[pass-gnome-extension](https://github.com/dmzoneill/pass-gnome-extension)** — Password store browser (archived)

## Requirements

- GNOME Shell 46+
- [GNU Pass](https://www.passwordstore.org/) (`pass`)
- [oathtool](https://www.nongnu.org/oath-toolkit/) (for TOTP generation)
- TOTP secrets stored in a pass entry (default `totp/all`) as `otpauth://` URIs

## Install

```bash
git clone https://github.com/dmzoneill/passmate.git
cd passmate
make install
```

Then restart GNOME Shell:
- **X11:** `Alt+F2`, type `r`, Enter
- **Wayland:** Log out and log back in

Enable via GNOME Extensions app or:
```bash
gnome-extensions enable passmate@dmzoneill.com
```

## Development

```bash
make dev          # Symlink + launch devkit session for testing
make dev-no-ext   # Launch devkit without extensions (baseline)
make install      # Copy to ~/.local/share/gnome-shell/extensions/
make uninstall    # Remove extension
make schemas      # Compile GSettings schemas
make lint         # Run eslint
make clean        # Remove compiled schemas
```

## Configuration

Open preferences via the gear icon in the extension popup, or:

```bash
gnome-extensions prefs passmate@dmzoneill.com
```

| Setting | Default | Description |
|---------|---------|-------------|
| Default tab | Passwords | Which tab opens first |
| Clipboard timeout | 45s | Auto-clear clipboard (0 = disabled) |
| TOTP pass entry | `totp/all` | Pass entry containing otpauth:// URIs |
| Password store path | *(empty)* | Custom path (falls back to `$PASSWORD_STORE_DIR` or `~/.password-store`) |
| Keybinding | `Super+W` | Keyboard shortcut to open menu |

## TOTP Entry Format

Store your TOTP secrets in a GNU Pass entry (default `totp/all`):

```
otpauth://totp/GitHub:username?secret=BASE32SECRET&digits=6
otpauth://totp/Google:user@gmail.com?secret=BASE32SECRET&digits=6
otpauth://totp/AWS:account-id?secret=BASE32SECRET&digits=8
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
