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

        success_embed = discord.Embed(
            title="✅ App Generated & Pushed to GitHub!",
            color=0x00C851,
        )
        success_embed.add_field(
            name="📦 Repository",
            value=f"[{result['repo_name']}]({result['repo_url']}) *(private)*",
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

@tree.command(name="status", description="Check if the AppBuilder bot is online and configured")
async def status_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🟢 Turmux Vibe Status", color=0x00C851)
    embed.add_field(name="Gemini API", value="✅ Configured" if config.GEMINI_API_KEY else "❌ Missing", inline=True)
    embed.add_field(name="GitHub Token", value="✅ Configured" if config.GITHUB_TOKEN else "❌ Missing", inline=True)
    embed.add_field(name="GitHub User", value=config.GITHUB_USERNAME or "❌ Not set", inline=True)
    embed.set_footer(text="Use /build to generate your app!")
    await interaction.response.send_message(embed=embed)


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
