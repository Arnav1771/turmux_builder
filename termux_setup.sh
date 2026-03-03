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

# Define script directory early for path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update + upgrade
echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python + Git + Build Tools (Critical for discord.py)
echo "[2/5] Installing Python, Git, Build Tools..."
pkg install -y python git clang make libffi openssl binutils

# Install pip dependencies
echo "[3/5] Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Create .env with Interactive Wizard
echo "[4/5] Configuring environment variables..."
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    read -p "   ⚠️  .env already exists. Overwrite? (y/n): " overwrite
    if [[ ! $overwrite =~ ^[Yy]$ ]]; then
        echo "   Skipping configuration."
    else
        rm "$ENV_FILE"
    fi
fi

if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "--- 🔑 Setup Wizard ---"
    read -p "Enter Gemini API Key: " gemini_key
    read -p "Enter GitHub Token (Classic): " github_token
    read -p "Enter GitHub Username: " github_user
    read -p "Enter Discord Bot Token: " discord_token
    echo ""

    cat <<EOF > "$ENV_FILE"
GEMINI_API_KEY=$gemini_key
GITHUB_TOKEN=$github_token
GITHUB_USERNAME=$github_user
DISCORD_BOT_TOKEN=$discord_token
EOF
    echo "   ✅ .env file generated successfully."
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
