#!/usr/bin/env bash
# Label Previewer installer (Linux)
#
# Installs whatever's missing (Tkinter + Pillow, via your distro's package
# manager when possible) and adds a "Label Previewer" entry to your
# application menu, with the custom icon. Run from this folder:
#   bash install.sh

set -uo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Label Previewer installer (Linux) =="
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it with your distro's package manager" >&2
    echo "(e.g. sudo apt install python3) then re-run this script." >&2
    exit 1
fi

# Figure out which package manager (if any) we can use to install system
# packages automatically. Falls back to just telling the user what to run.
PKG_INSTALL=""
TK_PKG=""
PIL_PKG=""
if command -v apt-get >/dev/null 2>&1; then
    PKG_INSTALL="sudo apt-get install -y"
    TK_PKG="python3-tk"; PIL_PKG="python3-pil"
elif command -v dnf >/dev/null 2>&1; then
    PKG_INSTALL="sudo dnf install -y"
    TK_PKG="python3-tkinter"; PIL_PKG="python3-pillow"
elif command -v pacman >/dev/null 2>&1; then
    PKG_INSTALL="sudo pacman -S --noconfirm"
    TK_PKG="tk"; PIL_PKG="python-pillow"
elif command -v zypper >/dev/null 2>&1; then
    PKG_INSTALL="sudo zypper install -y"
    TK_PKG="python3-tk"; PIL_PKG="python3-Pillow"
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter not found."
    if [ -n "$PKG_INSTALL" ]; then
        echo "Installing $TK_PKG (you may be asked for your password)..."
        $PKG_INSTALL "$TK_PKG"
    else
        echo "Install it with your distro's package manager, e.g.:" >&2
        echo "  sudo apt install python3-tk" >&2
        exit 1
    fi
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        echo "Tkinter still isn't importable - see the messages above." >&2
        exit 1
    fi
fi

if ! python3 -c "import PIL" >/dev/null 2>&1; then
    echo "Pillow not found."
    installed_via_system_pkg=0
    if [ -n "$PKG_INSTALL" ]; then
        echo "Installing $PIL_PKG (you may be asked for your password)..."
        if $PKG_INSTALL "$PIL_PKG"; then
            installed_via_system_pkg=1
        fi
    fi
    if [ "$installed_via_system_pkg" -eq 0 ] || ! python3 -c "import PIL" >/dev/null 2>&1; then
        echo "Installing it for the current user with pip instead..."
        err_file="$(mktemp)"
        if ! python3 -m pip install --user pillow 2>"$err_file"; then
            if grep -q "externally-managed-environment" "$err_file"; then
                echo "This Python is externally managed; retrying with --break-system-packages..."
                python3 -m pip install --user --break-system-packages pillow
            else
                cat "$err_file" >&2
                rm -f "$err_file"
                exit 1
            fi
        fi
        rm -f "$err_file"
    fi
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
echo
echo "Done! Installed launcher: $DESKTOP_FILE"
echo "Look for 'Label Previewer' in your application menu."
