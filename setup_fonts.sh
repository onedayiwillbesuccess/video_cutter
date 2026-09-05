#!/bin/bash
# Install professional fonts for The Clip Snipper captions.
# Run as root or with sudo on the server (Debian/Ubuntu).
#
# Arial Black (mscorefonts) needs the EULA accepted via debconf. This script
# pre-seeds the acceptance so the install is non-interactive.
set -e

echo "Updating package lists..."
apt-get update

echo "Installing fonts-liberation and fonts-roboto..."
DEBIAN_FRONTEND=noninteractive apt-get install -y fonts-liberation fonts-roboto

echo "Installing Microsoft TrueType core fonts (Arial, Arial Black, etc.)..."
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get install -y ttf-mscorefonts-installer

echo "Installing ffmpeg (in case it is missing) and the libass subtitle renderer..."
DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg libass9

echo "Refreshing the font cache so FFmpeg/libass can see the new fonts..."
fc-cache -f -v

echo "---- Installed caption-relevant fonts ----"
fc-list | grep -iE "arial|roboto|liberation|dejavu" || true

echo ""
echo "Done. Fonts installed. Restart the backend (pkill -f main.py; then rerun run_backend.sh)"
