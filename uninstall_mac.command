#!/usr/bin/env bash
# Double-clickable wrapper around uninstall_mac.sh.
cd "$(dirname "$0")"
bash uninstall_mac.sh
echo
read -n 1 -s -r -p "Press any key to close..."
echo
