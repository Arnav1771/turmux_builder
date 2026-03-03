#!/bin/bash
# ============================================================
#  deploy.sh — Deploy AppBuilder Discord Bot to Fly.io (FREE)
#  Run this from the appbuilder/ directory
#  Works on Windows (Git Bash / WSL) and Termux
# ============================================================

set -e

echo ""
echo "======================================"
echo "  🚀 AppBuilder → Fly.io Deploy"
echo "======================================"
echo ""

# ── Step 1: Check flyctl is installed ────────────────────────
if ! command -v fly &>/dev/null; then
    echo "[1/4] Installing flyctl CLI..."
    # Windows / Mac / Linux universal installer
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
    echo "      ✅ flyctl installed"
else
    echo "[1/4] flyctl already installed ✅"
fi

# ── Step 2: Login ─────────────────────────────────────────────
echo ""
echo "[2/4] Logging into Fly.io..."
echo "      (A browser window will open — sign up free, no credit card needed)"
fly auth login

# ── Step 3: Create app (first time only) ─────────────────────
echo ""
echo "[3/4] Creating Fly.io app (skip if already exists)..."
fly apps create appbuilder-discord-bot --machines 2>/dev/null || echo "      App already exists, skipping."

# Load .env and push secrets to Fly
echo ""
echo "      Pushing secrets to Fly.io (from your .env)..."
if [ -f .env ]; then
    # Export each line from .env as a Fly secret
    while IFS='=' read -r key value; do
        # Skip blank lines and comments
        [[ -z "$key" || "$key" == \#* ]] && continue
        echo "      Setting secret: $key"
        fly secrets set "${key}=${value}" --app appbuilder-discord-bot 2>/dev/null
    done < .env
    echo "      ✅ All secrets uploaded"
else
    echo "      ❌ .env not found! Make sure you run this from the appbuilder/ directory"
    exit 1
fi

# ── Step 4: Deploy ───────────────────────────────────────────
echo ""
echo "[4/4] Deploying to Fly.io..."
fly deploy --app appbuilder-discord-bot

echo ""
echo "======================================"
echo "  ✅ BOT IS LIVE 24/7 ON FLY.IO!"
echo "======================================"
echo ""
echo "  Useful commands:"
echo "  fly logs --app appbuilder-discord-bot    ← see live logs"
echo "  fly status --app appbuilder-discord-bot  ← check status"
echo "  fly ssh console --app appbuilder-discord-bot  ← SSH in"
echo ""
echo "  To update after code changes:"
echo "  fly deploy --app appbuilder-discord-bot"
echo ""
