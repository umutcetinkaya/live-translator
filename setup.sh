#!/bin/bash
# Live Translator — Quick Setup
set -e

echo "=== Live Translator Setup ==="
echo ""

# Virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Usage:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "Or use make:"
echo "  make run"
echo ""
echo "Build macOS app:"
echo "  make build"
echo ""
echo "Download TTS voice models (optional, ~580MB):"
echo "  make models"
echo ""
echo "First run permissions:"
echo "  1. Screen Recording  (System Settings > Privacy & Security)"
echo "  2. Speech Recognition (auto-prompted)"
echo ""
