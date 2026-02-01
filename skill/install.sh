#!/bin/bash
# Equilibrium Guard Installer
# ===========================
# Installs the skill to your OpenClaw workspace

set -e

# Detect OpenClaw workspace
if [ -d "$HOME/.openclaw/workspace/skills" ]; then
    SKILLS_DIR="$HOME/.openclaw/workspace/skills"
elif [ -d "$HOME/.clawdbot/workspace/skills" ]; then
    SKILLS_DIR="$HOME/.clawdbot/workspace/skills"
else
    echo "Error: Could not find OpenClaw/Clawdbot workspace"
    echo "Expected: ~/.openclaw/workspace/skills or ~/.clawdbot/workspace/skills"
    exit 1
fi

INSTALL_DIR="$SKILLS_DIR/equilibrium-guard"

echo "=================================="
echo "Equilibrium Guard Installer"
echo "=================================="
echo ""
echo "Installing to: $INSTALL_DIR"
echo ""

# Create directory
mkdir -p "$INSTALL_DIR"

# Copy skill files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/SKILL.md" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/guard.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR/"

# Copy dashboard if exists
if [ -d "$SCRIPT_DIR/../dashboard" ]; then
    echo "Copying dashboard..."
    cp -r "$SCRIPT_DIR/../dashboard" "$INSTALL_DIR/"
fi

echo ""
echo "✓ Skill installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Your agent will read SKILL.md on next session"
echo "  2. (Optional) Start the dashboard:"
echo "     cd $INSTALL_DIR/dashboard"
echo "     pip install -r requirements.txt"
echo "     python server.py"
echo "  3. Open http://localhost:8081"
echo ""
echo "=================================="
