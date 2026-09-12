#!/usr/bin/env bash
# Removes the "Label Previewer.app" bundle created by install_mac.sh.
# Your source folder and datasets are untouched.
#
#   bash uninstall_mac.sh

BUNDLE="$HOME/Applications/Label Previewer.app"

if [ -d "$BUNDLE" ]; then
    rm -rf "$BUNDLE"
    echo "Removed: $BUNDLE"
else
    echo "Not installed at: $BUNDLE"
fi
