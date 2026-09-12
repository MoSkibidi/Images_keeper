#!/usr/bin/env bash
# Double-clickable wrapper around install_mac.sh, so you don't need to
# open Terminal or type anything - just double-click this file in Finder.
cd "$(dirname "$0")"
bash install_mac.sh
status=$?
echo
if [ $status -eq 0 ]; then
    echo "All done - you can close this window."
else
    echo "Something went wrong (see above) - you can close this window."
fi
read -n 1 -s -r -p "Press any key to close..."
echo
