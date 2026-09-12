#!/usr/bin/env bash
# Label Previewer installer (macOS)
#
# Builds a real double-clickable "Label Previewer.app" in ~/Applications
# (no sudo needed), automatically installing whatever it needs along the
# way (Tkinter via Homebrew, Pillow via pip). Re-run any time to update it.
#
#   bash install_mac.sh
#
# Or just double-click install_mac.command in Finder - no Terminal typing
# required.

set -uo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Label Previewer installer (macOS) =="
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found."
    if command -v brew >/dev/null 2>&1; then
        echo "Installing Python via Homebrew..."
        brew install python
    else
        echo "Install Python 3 first, then re-run this script:" >&2
        echo "  - Homebrew (https://brew.sh): brew install python" >&2
        echo "  - or the official installer: https://www.python.org/downloads/macos/" >&2
        exit 1
    fi
fi
PYTHON_BIN="$(command -v python3)"

if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter not found for $PYTHON_BIN."
    if command -v brew >/dev/null 2>&1; then
        PYVER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
        echo "Installing it via Homebrew (python-tk@$PYVER)..."
        if ! brew install "python-tk@$PYVER"; then
            echo "That exact formula wasn't available, trying the generic one..."
            brew install python-tk
        fi
    else
        echo "Homebrew isn't installed, so this can't be done automatically. Either:" >&2
        echo "  - install Homebrew (https://brew.sh) and re-run this script, or" >&2
        echo "  - reinstall Python from https://www.python.org/downloads/macos/" >&2
        echo "    (its installer bundles Tkinter already)." >&2
        exit 1
    fi
    if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
        echo "Tkinter still isn't importable - see the messages above." >&2
        exit 1
    fi
fi

if ! "$PYTHON_BIN" -c "import PIL" >/dev/null 2>&1; then
    echo "Pillow not found, installing it for the current user..."
    err_file="$(mktemp)"
    if ! "$PYTHON_BIN" -m pip install --user pillow 2>"$err_file"; then
        if grep -q "externally-managed-environment" "$err_file"; then
            echo "This Python is externally managed (Homebrew); retrying with --break-system-packages..."
            "$PYTHON_BIN" -m pip install --user --break-system-packages pillow
        else
            cat "$err_file" >&2
            rm -f "$err_file"
            exit 1
        fi
    fi
    rm -f "$err_file"
fi

APPS_DIR="$HOME/Applications"
BUNDLE="$APPS_DIR/Label Previewer.app"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"

cp "$APP_DIR/icon.icns" "$BUNDLE/Contents/Resources/icon.icns"

cat > "$BUNDLE/Contents/MacOS/LabelPreviewer" <<LAUNCHER
#!/usr/bin/env bash
exec "$PYTHON_BIN" "$APP_DIR/label_previewer.py"
LAUNCHER
chmod +x "$BUNDLE/Contents/MacOS/LabelPreviewer"

cat > "$BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Label Previewer</string>
    <key>CFBundleDisplayName</key>
    <string>Label Previewer</string>
    <key>CFBundleIdentifier</key>
    <string>com.labelpreviewer.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>LabelPreviewer</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

echo
echo "Done! Installed: $BUNDLE"
echo "Find it in ~/Applications - double-click it, or drag it to your Dock"
echo "or into /Applications."
