#!/bin/bash
# By Diego Cardenas "The Samedog" under GNU GENERAL PUBLIC LICENSE Version 2, June 1991
# (www.gnu.org/licenses/old-licenses/gpl-2.0.html) e-mail: the.samedog[]gmail.com.
# https://github.com/samedog
##########################################################################################
#
# THIS SCRIPT IS A SET OF HORRIBLE HACKS, IT MIGHT WORK, MIGHT OPEN A VORTEX 
# AND SEND YOU TO A COMPLETELY DIFFERENT UNIVERSE, OR MIGHT DO SHIT, WHO KNOWS?.
#
##########################################################################################
# Version: 1.0
################################## Code begins here #######################################


#icon, name and terminal (true/false) are options
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file_path> [icon_path] [name] [terminal]"
    exit 1
fi


FILE_PATH="$(realpath "$1")"
ICON_PATH="$(realpath "${2:-}")"
CUSTOM_NAME="${3:-$(basename "$FILE_PATH")}"
TERMINAL="${4:-false}"


DESKTOP_FILE="/usr/share/applications/$CUSTOM_NAME.desktop"


if [[ "$FILE_PATH" == *.sh ]]; then
    sudo chmod +x "$FILE_PATH"
    echo "[Desktop Entry]" | sudo tee "$DESKTOP_FILE" > /dev/null
    echo "Version=1.0" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Type=Application" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Name=$CUSTOM_NAME" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Exec=bash \"$FILE_PATH\"" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Terminal=True" | sudo tee -a "$DESKTOP_FILE" > /dev/null #terminal always true for terminal apps, duh
else
    # Create the .desktop file for a non-script file
    echo "[Desktop Entry]" | sudo tee "$DESKTOP_FILE" > /dev/null
    echo "Version=1.0" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Type=Application" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Name=$CUSTOM_NAME" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Exec=xdg-open \"$FILE_PATH\"" | sudo tee -a "$DESKTOP_FILE" > /dev/null
    echo "Terminal=false" | sudo tee -a "$DESKTOP_FILE" > /dev/null
fi

if [ -n "$ICON_PATH" ]; then
    echo "Icon=$ICON_PATH" | sudo tee -a "$DESKTOP_FILE" > /dev/null
fi


sudo chmod +x "$DESKTOP_FILE"
echo "Created system-wide desktop shortcut: $DESKTOP_FILE"

