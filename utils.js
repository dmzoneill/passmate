import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');
Gio._promisify(Gio.File.prototype, 'enumerate_children_async');

let _clipboardTimeoutId = null;

export function getPasswordStorePath(settings) {
    const custom = settings.get_string('password-store-path');
    if (custom)
        return custom;
    const envDir = GLib.getenv('PASSWORD_STORE_DIR');
    if (envDir)
        return envDir;
    return `${GLib.get_home_dir()}/.password-store`;
}

export async function execAsync(argv, input = null, cancellable = null) {
    let cancelId = 0;
    let flags = Gio.SubprocessFlags.STDOUT_PIPE |
                Gio.SubprocessFlags.STDERR_PIPE;

    if (input !== null)
        flags |= Gio.SubprocessFlags.STDIN_PIPE;

    const proc = new Gio.Subprocess({argv, flags});
    proc.init(cancellable);

    if (cancellable instanceof Gio.Cancellable)
        cancelId = cancellable.connect(() => proc.force_exit());

    try {
        const [stdout, stderr] = await proc.communicate_utf8_async(input, null);
        const status = proc.get_exit_status();

        if (status !== 0) {
            throw new Gio.IOErrorEnum({
                code: Gio.IOErrorEnum.FAILED,
                message: stderr ? stderr.trim() : `Command '${argv}' failed with exit code ${status}`,
            });
        }

        return stdout.trim();
    } finally {
        if (cancelId > 0)
            cancellable.disconnect(cancelId);
    }
}

export async function enumeratePasswordStoreEntriesAsync(directory, settings) {
    const storePath = getPasswordStorePath(settings);
    const path = `${storePath}/${directory}`;
    const file = Gio.File.new_for_path(path);

    let enumerator;
    try {
        enumerator = await file.enumerate_children_async(
            'standard::name,standard::type',
            Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_DEFAULT,
            null
        );
    } catch (e) {
        logDebug(`Failed to read directory: ${e}`);
        return [];
    }

    const entries = [];
    for await (const info of enumerator) {
        const name = info.get_name();
        if (!name.startsWith('.')) {
            entries.push({
                name,
                isDir: info.get_file_type() === Gio.FileType.DIRECTORY,
            });
        }
    }

    entries.sort((a, b) => {
        if (a.isDir && !b.isDir) return -1;
        if (b.isDir && !a.isDir) return 1;
        return a.name.localeCompare(b.name);
    });

    return entries;
}

export function resolveParentDir(path) {
    const parts = path.split('/').filter(Boolean);
    return parts.length > 0 ? `${parts.slice(0, -1).join('/')}/` : '/';
}

export function formatEntryLabel(name, isDir) {
    return isDir ? `${name}/` : name.replace(/\.gpg$/, '');
}

export function sanitizePassRoute(route) {
    return route.replace(/^\//, '').replace(/\.gpg$/, '');
}

export function isEntryMatch(label, query, threshold = 3) {
    const labelLower = label.toLowerCase();
    const queryLower = query.toLowerCase();
    return (
        labelLower.includes(queryLower) ||
        levenshteinDistance(labelLower, queryLower) <= threshold
    );
}

export function filterMatchingEntries(entries, query) {
    return entries.filter(item => {
        const label = formatEntryLabel(item.name, item.isDir);
        return !query || isEntryMatch(label, query);
    });
}

export function levenshteinDistance(a, b) {
    if (a.length === 0) return b.length;
    if (b.length === 0) return a.length;

    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1,
                    matrix[i][j - 1] + 1,
                    matrix[i - 1][j] + 1
                );
            }
        }
    }

    return matrix[b.length][a.length];
}

export function copyToClipboardWithTimeout(text, timeoutSeconds) {
    if (_clipboardTimeoutId) {
        GLib.source_remove(_clipboardTimeoutId);
        _clipboardTimeoutId = null;
    }

    St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);

    if (timeoutSeconds > 0) {
        _clipboardTimeoutId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            timeoutSeconds,
            () => {
                St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, '');
                _clipboardTimeoutId = null;
                return GLib.SOURCE_REMOVE;
            }
        );
    }
}

export function cancelClipboardTimeout() {
    if (_clipboardTimeoutId) {
        GLib.source_remove(_clipboardTimeoutId);
        _clipboardTimeoutId = null;
    }
}

export function debounce(fn, delayMs) {
    let timerId = null;
    const debounced = function (...args) {
        if (timerId !== null)
            GLib.source_remove(timerId);

        timerId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delayMs, () => {
            timerId = null;
            fn.apply(this, args);
            return GLib.SOURCE_REMOVE;
        });
    };
    debounced.cancel = () => {
        if (timerId !== null) {
            GLib.source_remove(timerId);
            timerId = null;
        }
    };
    return debounced;
}

export function logDebug(message) {
    console.log(`[passmate] ${message}`);
}
