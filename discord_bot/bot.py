"""
bot.py — Discord bot interface for AppBuilder.

Usage:
  In your Discord server, use the slash command:
    /build description: make me a todo app with React and Node.js

The bot will:
  1. Call Gemini to generate the full-stack app
  2. Push it to a private GitHub repo
  3. Reply with the repo URL + how-to-run instructions

SETUP:
  1. Go to https://discord.com/developers/applications
  2. Select your app → Bot → Copy Token
  3. Paste token into .env as DISCORD_BOT_TOKEN=...
  4. Invite bot with scopes: bot + applications.commands
     Permissions: Send Messages, Use Slash Commands, Embed Links
"""

import sys
import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# Fix path so imports work when running from discord_bot/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from core.pipeline import run_pipeline


# ── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True  # CRITICAL: Required for !sync command to work
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    print(f"[Discord] ✅ Logged in as {bot.user} (ID: {bot.user.id})", flush=True)
    print("[Discord] ⚙️ Syncing slash commands (global)...", flush=True)
    try:
        synced = await tree.sync()
        print(f"[Discord] 🚀 Synced {len(synced)} slash commands globally.", flush=True)
    except Exception as e:
        print(f"[Discord] ❌ Sync failed: {e}", flush=True)
    print("[Discord] Bot is ready! If commands don't show up, try typing !sync in your server.", flush=True)


@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Admin command to force a sync to the current server (much faster than global)."""
    print(f"[Discord] ⚙️ Manual sync triggered by {ctx.author}", flush=True)
    await ctx.send("⚙️ Syncing commands to this server...")
    try:
        # Sync to the current guild for instant results
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Synced {len(synced)} commands to this server! Try /build now.")
        print(f"[Discord] ✅ Guild sync complete.", flush=True)
    except Exception as e:
        print(f"[Discord] ❌ Manual sync failed: {e}", flush=True)
        await ctx.send(f"❌ Sync failed: {e}")


# ── /build command ────────────────────────────────────────────────────────────

@tree.command(
    name="build",
    description="Describe an app in plain English and I'll build + push it to GitHub!"
)
@app_commands.describe(description="Plain-English description of the app you want built")
async def build_command(interaction: discord.Interaction, description: str):
    """
    Main slash command: /build description:<NLP prompt>
    """
    # Acknowledge immediately (generation takes time)
    await interaction.response.defer(thinking=True)
    
    # Build a nice "working on it" embed
    working_embed = discord.Embed(
        title="🔨 Turmux Vibe — Building your app...",
        description=(
            f"**Prompt:** {description[:300]}\n\n"
            "⏳ **Step 1/2:** Planning your app architecture with Gemini AI...\n"
            "Then generating each file one by one.\n\n"
            "⏱️ This takes **2–3 minutes** for complex apps. Hang tight!"
        ),
        color=0x4285F4,
    )
    working_embed.set_footer(text="Powered by Gemini 2.5 Flash + GitHub")
    
    await interaction.followup.send(embed=working_embed)

    # Run the pipeline in a thread (blocking call)
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_pipeline, description
        )

        # Success embed
        tech = ", ".join(result.get("tech_stack", []) or ["Auto-detected"])
        how_to_run = result.get("how_to_run", "See HOW_TO_RUN.md in the repo.")
        # Trim how_to_run to fit Discord's 4096-char description limit
        if len(how_to_run) > 1000:
            how_to_run = how_to_run[:997] + "..."

        live_url = result.get("live_url")
        embed_title = "✅ App Generated, Deployed & Live! 🌐" if live_url else "✅ App Generated & Pushed to GitHub!"
        success_embed = discord.Embed(
            title=embed_title,
            color=0x00C851,
        )
        success_embed.add_field(
            name="📦 Repository",
            value=f"[{result['repo_name']}]({result['repo_url']}) *(private)*",
            inline=False,
        )
        if live_url:
            success_embed.add_field(
                name="🌐 Live URL",
                value=f"[{live_url}]({live_url})",
                inline=False,
            )
        success_embed.add_field(
            name="📝 Description",
            value=result.get("description", description[:200]),
            inline=False,
        )
        success_embed.add_field(
            name="🛠 Tech Stack",
            value=tech,
            inline=False,
        )
        success_embed.add_field(
            name="📁 Files Generated",
            value=f"{result['file_count']} files",
            inline=True,
        )
        
        tokens_used = result.get("tokens_used")
        if tokens_used:
            success_embed.add_field(
                name="📊 Tokens Used",
                value=f"{tokens_used:,} / 65,536",
                inline=True,
            )
            
        success_embed.add_field(
            name="🔒 Visibility",
            value="Private",
            inline=True,
        )
        success_embed.add_field(
            name="▶️ How to Run",
            value=f"```\n{how_to_run}\n```",
            inline=False,
        )
        success_embed.set_footer(text="🤖 Turmux Vibe | Gemini + GitHub")

        await interaction.followup.send(embed=success_embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Build Failed",
            description=f"```\n{str(e)[:1500]}\n```",
            color=0xFF4444,
        )
        error_embed.set_footer(text="Check your .env keys and try again")
        await interaction.followup.send(embed=error_embed)
        raise


# ── /status command ───────────────────────────────────────────────────────────

@tree.command(name="status", description="Check if the Turmux Vibe bot is online and all keys are configured")
async def status_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🟢 Turmux Vibe — Status", color=0x00C851)
    
    embed.add_field(name="🤖 Gemini API Key", value="✅ Set" if config.GEMINI_API_KEY else "❌ Missing", inline=True)
    embed.add_field(name="🐙 GitHub Token", value="✅ Set" if config.GITHUB_TOKEN else "❌ Missing", inline=True)
    embed.add_field(name="👤 GitHub User", value=f"`{config.GITHUB_USERNAME}`" if config.GITHUB_USERNAME else "❌ Not set", inline=True)
    embed.add_field(name="🚀 Vercel Token", value="✅ Set" if config.VERCEL_TOKEN else "⚠️ Not set (auto-deploy disabled)", inline=False)
    embed.add_field(name="🧠 Active Model", value=f"`{_active_model}`", inline=True)
    embed.set_footer(text="Use /build to generate your app! | /model to switch AI model")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Shared model state ────────────────────────────────────────────────────────
# Models the user can choose from. Stored as a module-level variable so /build picks it up.

AVAILABLE_MODELS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash — Fastest, best for most apps (default)",
    "gemini-2.0-flash": "Gemini 2.0 Flash — Reliable, excellent quality",
    "gemini-1.5-pro":   "Gemini 1.5 Pro — Most capable, slower (best for complex apps)",
    "gemini-1.5-flash": "Gemini 1.5 Flash — Older fast model",
}
_active_model: str = "gemini-2.5-flash"


# ── /model command ─────────────────────────────────────────────────────────────

class ModelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=model_id,
                description=desc[:100],
                default=(model_id == _active_model)
            )
            for model_id, desc in AVAILABLE_MODELS.items()
        ]
        super().__init__(placeholder="Choose a Gemini model...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global _active_model
        _active_model = self.values[0]
        # Patch the GeminiClient class globally
        from core.gemini_client import GeminiClient
        GeminiClient._override_model = _active_model
        await interaction.response.send_message(
            f"✅ Active model switched to `{_active_model}`\nAll future `/build` commands will use this model.",
            ephemeral=True
        )


class ModelView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ModelSelect())


@tree.command(name="model", description="Switch the Gemini AI model used for code generation")
async def model_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧠 Select Gemini Model",
        description=f"Currently active: `{_active_model}`\nPick a model below to use for all future `/build` commands.",
        color=0x4285F4,
    )
    for model_id, desc in AVAILABLE_MODELS.items():
        embed.add_field(name=model_id, value=desc, inline=False)
    await interaction.response.send_message(embed=embed, view=ModelView(), ephemeral=True)


# ── /apiinfo command ───────────────────────────────────────────────────────────

@tree.command(name="apiinfo", description="Check Gemini API details, active model, and rate limit info")
async def apiinfo_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    import requests as req

    embed = discord.Embed(title="📊 API Info & Quota", color=0x4285F4)
    embed.add_field(name="🧠 Active Model", value=f"`{_active_model}`", inline=False)

    # Check Gemini models list via REST
    try:
        r = req.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": config.GEMINI_API_KEY},
            timeout=10,
        )
        if r.status_code == 200:
            models = r.json().get("models", [])
            flash_models = [m["name"].split("/")[-1] for m in models if "flash" in m["name"] or "pro" in m["name"]]
            embed.add_field(
                name="✅ Gemini API",
                value=f"Connected • {len(models)} models available",
                inline=True,
            )
            embed.add_field(
                name="🔥 Available For You",
                value="\n".join(f"• `{m}`" for m in flash_models[:8]) or "None found",
                inline=False,
            )
        else:
            embed.add_field(name="❌ Gemini API", value=f"Error {r.status_code}: {r.text[:100]}", inline=True)
    except Exception as e:
        embed.add_field(name="❌ Gemini API", value=f"Connection failed: {e}", inline=True)

    # Check Vercel account info
    if config.VERCEL_TOKEN:
        try:
            rv = req.get(
                "https://api.vercel.com/v2/user",
                headers={"Authorization": f"Bearer {config.VERCEL_TOKEN}"},
                timeout=10,
            )
            if rv.status_code == 200:
                user_data = rv.json().get("user", {})
                username = user_data.get("username") or user_data.get("email", "Unknown")
                embed.add_field(name="🚀 Vercel", value=f"✅ Connected as `{username}`", inline=True)
            else:
                embed.add_field(name="🚀 Vercel", value=f"❌ Error {rv.status_code}", inline=True)
        except Exception as e:
            embed.add_field(name="🚀 Vercel", value=f"❌ {e}", inline=True)
    else:
        embed.add_field(name="🚀 Vercel", value="⚠️ Token not set", inline=True)

    embed.add_field(
        name="📋 Gemini Rate Limits (Free Tier)",
        value=(
            "• **gemini-2.5-flash**: 10 RPM / 500 RPD / 1M TPM\n"
            "• **gemini-1.5-pro**: 2 RPM / 50 RPD / 32K TPM\n"
            "• **gemini-1.5-flash**: 15 RPM / 1500 RPD / 1M TPM\n"
            "• RPM = Requests/min, RPD = Requests/day, TPM = Tokens/min"
        ),
        inline=False,
    )
    embed.set_footer(text="Use /model to switch models | /keys to validate all keys")
    await interaction.followup.send(embed=embed, ephemeral=True)


# ── /keys command ──────────────────────────────────────────────────────────────

@tree.command(name="keys", description="Live-validate all your API keys (Gemini, GitHub, Vercel)")
async def keys_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    import requests as req

    embed = discord.Embed(title="🔑 API Keys — Live Check", color=0x4285F4)

    # ── Check Gemini ──
    try:
        r = req.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": config.GEMINI_API_KEY},
            timeout=10,
        )
        if r.status_code == 200:
            count = len(r.json().get("models", []))
            embed.add_field(name="🤖 Gemini API", value=f"✅ Valid — {count} models accessible", inline=False)
        else:
            embed.add_field(name="🤖 Gemini API", value=f"❌ Invalid ({r.status_code})", inline=False)
    except Exception as e:
        embed.add_field(name="🤖 Gemini API", value=f"❌ Error: {e}", inline=False)

    # ── Check GitHub ──
    try:
        rg = req.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {config.GITHUB_TOKEN}"},
            timeout=10,
        )
        if rg.status_code == 200:
            gh_user = rg.json()
            scopes = rg.headers.get("X-OAuth-Scopes", "unknown")
            embed.add_field(
                name="🐙 GitHub Token",
                value=f"✅ Valid — Logged in as `{gh_user['login']}`\nScopes: `{scopes}`",
                inline=False,
            )
        else:
            embed.add_field(name="🐙 GitHub Token", value=f"❌ Invalid ({rg.status_code})", inline=False)
    except Exception as e:
        embed.add_field(name="🐙 GitHub Token", value=f"❌ Error: {e}", inline=False)

    # ── Check Vercel ──
    if config.VERCEL_TOKEN:
        try:
            rv = req.get(
                "https://api.vercel.com/v2/user",
                headers={"Authorization": f"Bearer {config.VERCEL_TOKEN}"},
                timeout=10,
            )
            if rv.status_code == 200:
                user_data = rv.json().get("user", {})
                username = user_data.get("username") or user_data.get("email", "Connected")
                embed.add_field(name="🚀 Vercel Token", value=f"✅ Valid — Account: `{username}`", inline=False)
            else:
                embed.add_field(name="🚀 Vercel Token", value=f"❌ Invalid ({rv.status_code}): {rv.text[:100]}", inline=False)
        except Exception as e:
            embed.add_field(name="🚀 Vercel Token", value=f"❌ Error: {e}", inline=False)
    else:
        embed.add_field(name="🚀 Vercel Token", value="⚠️ Not set in .env — auto-deploy disabled", inline=False)

    embed.set_footer(text="All checks done! | Use /apiinfo for rate limit details")
    await interaction.followup.send(embed=embed, ephemeral=True)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = config.DISCORD_BOT_TOKEN
    if not token or token == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("\n❌ ERROR: DISCORD_BOT_TOKEN is not set in .env!", flush=True)
        print("   Go to: https://discord.com/developers/applications", flush=True)
        print("   → Your App → Bot → Reset Token → Copy it", flush=True)
        print("   → Paste it in appbuilder/.env as DISCORD_BOT_TOKEN=...", flush=True)
        sys.exit(1)
    
    print("[Discord] Starting Turmux Vibe bot...", flush=True)
    bot.run(token)
