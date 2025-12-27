#!/bin/bash
# Quick-RMBG uninstallation script

set -e

echo "=== Quick-RMBG Uninstaller ==="
echo

# Remove Dolphin service menu
SERVICEMENU_FILE="$HOME/.local/share/kio/servicemenus/quick-rmbg.desktop"
if [ -f "$SERVICEMENU_FILE" ]; then
    echo "Removing Dolphin context menu..."
    rm "$SERVICEMENU_FILE"
fi

# Remove RMBG venv
RMBG_DIR="$HOME/.local/share/quick-rmbg"
if [ -d "$RMBG_DIR" ]; then
    echo "Removing RMBG installation..."
    rm -rf "$RMBG_DIR"
fi

# Remove config
CONFIG_DIR="$HOME/.config/quick-rmbg"
if [ -d "$CONFIG_DIR" ]; then
    echo "Removing configuration..."
    rm -rf "$CONFIG_DIR"
fi

# Uninstall package
echo "Uninstalling quick-rmbg package..."
if command -v pipx &> /dev/null; then
    pipx uninstall quick-rmbg 2>/dev/null || true
fi
if command -v uv &> /dev/null; then
    uv tool uninstall quick-rmbg 2>/dev/null || true
fi

# Update KDE service cache
if command -v kbuildsycoca6 &> /dev/null; then
    kbuildsycoca6 2>/dev/null || true
elif command -v kbuildsycoca5 &> /dev/null; then
    kbuildsycoca5 2>/dev/null || true
fi

echo
echo "=== Uninstallation Complete ==="
