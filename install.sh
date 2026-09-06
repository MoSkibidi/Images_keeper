#!/usr/bin/env bash
# Label Previewer installer (Linux)
#
# Checks dependencies and installs a desktop launcher (so the app shows up
# in your application menu with the custom icon). Run from this folder:
#   bash install.sh

set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it first (e.g. sudo apt install python3)." >&2
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "tkinter not found. Install it, e.g.:"
    echo "  sudo apt install python3-tk"
    exit 1
fi

if ! python3 -c "import PIL" >/dev/null 2>&1; then
    echo "Pillow not found, installing it for the current user..."
    python3 -m pip install --user pillow
fi

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/label-previewer.desktop"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Label Previewer
Comment=Preview and sort labelled image/annotation pairs
Exec=python3 "$APP_DIR/label_previewer.py"
Icon=$APP_DIR/icon.png
Terminal=false
Categories=Graphics;Utility;
EOF

chmod +x "$DESKTOP_FILE"
echo "Installed launcher: $DESKTOP_FILE"
echo "Look for 'Label Previewer' in your application menu."
