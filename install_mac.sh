#!/usr/bin/env bash
# Label Previewer installer (macOS)
#
# Builds a real double-clickable "Label Previewer.app" in ~/Applications
# (no sudo needed) that runs this script's label_previewer.py with the
# custom icon. Re-run any time to update it.
#
#   bash install_mac.sh

set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it first, e.g.:"
    echo "  brew install python"
    echo "(see https://brew.sh if you don't have Homebrew, or use the official"
    echo " installer from https://www.python.org/downloads/macos/)"
    exit 1
fi
PYTHON_BIN="$(command -v python3)"

if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
    echo "tkinter not found for $PYTHON_BIN."
    echo "If you installed Python via Homebrew:  brew install python-tk"
    echo "If you used the python.org installer, tkinter should already be"
    echo "included - try reinstalling from https://www.python.org/downloads/macos/"
    exit 1
fi

if ! "$PYTHON_BIN" -c "import PIL" >/dev/null 2>&1; then
    echo "Pillow not found, installing it for the current user..."
    "$PYTHON_BIN" -m pip install --user pillow
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

echo "Installed: $BUNDLE"
echo "Find it in ~/Applications - double-click it, or drag it to your Dock"
echo "or into /Applications."
