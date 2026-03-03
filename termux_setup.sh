#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  termux_setup.sh — One-shot setup for AppBuilder on Termux
#  Run this ONCE on your phone:
#    bash termux_setup.sh
# ============================================================

set -e
echo ""
echo "======================================"
echo "  🚀 AppBuilder Termux Setup"
echo "======================================"
echo ""

# Update + upgrade
echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python + Git + Build Tools (Critical for discord.py)
echo "[2/5] Installing Python, Git, Build Tools..."
pkg install -y python git clang make libffi openssl binutils

# Install pip dependencies
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Create .env if it doesn't exist
echo "[4/5] Setting up .env..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
    echo ""
    echo "   ⚠️  Created .env file. Please fill in your keys:"
    echo "   nano $ENV_FILE"
    echo ""
else
    echo "   .env already exists, skipping."
fi

# Make CLI executable
echo "[5/5] Making CLI script executable..."
chmod +x "$SCRIPT_DIR/cli/build.py"

echo ""
echo "======================================"
echo "  ✅ Setup complete!"
echo "======================================"
echo ""
echo "  How to use AppBuilder from Termux:"
echo ""
echo "  cd $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "  python cli/build.py \"describe your app here\""
echo ""
echo "  Example:"
echo "  python cli/build.py \"todo app with React and FastAPI\""
echo ""
