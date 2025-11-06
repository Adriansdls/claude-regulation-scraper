#!/bin/bash
# Research Graph Explorer - One-Line Installer
# Usage: curl -sSL https://raw.githubusercontent.com/.../install.sh | bash

set -e

echo "================================================"
echo "Research Graph Explorer - Simple Installer"
echo "================================================"
echo ""

# Check Python version
echo "→ Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION"
echo ""

# Install package
echo "→ Installing Research Graph Explorer..."
echo ""

pip3 install "research-graph-explorer @ git+https://github.com/Adriansdls/claude-regulation-scraper.git"

echo ""
echo "================================================"
echo "🎉 Installation Complete!"
echo "================================================"
echo ""
echo "Quick start:"
echo "  rge --help"
echo "  rge chat knowledge_graph.json"
echo ""
echo "Enjoy! ✨"
