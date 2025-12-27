#!/bin/bash
# Quick-RMBG installation script
# Installs the Dolphin context menu integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Quick-RMBG Installer ==="
echo

# Check if rembg is available
if ! command -v rembg &> /dev/null; then
    echo "ERROR: rembg not found in PATH"
    echo "Install it first with: pip install rembg[cli]"
    exit 1
fi

echo "Found rembg at: $(which rembg)"

# Check for uv or pipx
if command -v uv &> /dev/null; then
    INSTALLER="uv"
    echo "Using uv for installation..."
elif command -v pipx &> /dev/null; then
    INSTALLER="pipx"
    echo "Using pipx for installation..."
else
    echo "Neither uv nor pipx found. Please install one of them:"
    echo "  uv:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  pipx: python3 -m pip install --user pipx"
    exit 1
fi

# Install the package
echo
echo "Installing quick-rmbg CLI wrapper..."
if [ "$INSTALLER" = "uv" ]; then
    uv tool install "$PROJECT_DIR" --force
elif [ "$INSTALLER" = "pipx" ]; then
    pipx install "$PROJECT_DIR" --force
fi

# Install Dolphin service menu
echo
echo "Installing Dolphin context menu..."
SERVICEMENU_DIR="$HOME/.local/share/kio/servicemenus"
mkdir -p "$SERVICEMENU_DIR"
cp "$PROJECT_DIR/dolphin/quick-rmbg.desktop" "$SERVICEMENU_DIR/"

# Update KDE service cache
if command -v kbuildsycoca6 &> /dev/null; then
    echo "Rebuilding KDE service cache..."
    kbuildsycoca6 2>/dev/null || true
elif command -v kbuildsycoca5 &> /dev/null; then
    kbuildsycoca5 2>/dev/null || true
fi

echo
echo "=== Installation Complete ==="
echo
echo "Quick-RMBG is now available:"
echo "  - Right-click any image in Dolphin → 'Quick RMBG'"
echo "  - Right-click any image in Dolphin → 'Quick RMBG (Two-Pass)'"
echo "  - CLI: quick-rmbg <image>"
echo "  - CLI: quick-rmbg --two-pass <image>"
echo
echo "Optional config: ~/.config/quick-rmbg/config.json"
