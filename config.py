"""
config.py — Central config/env loader for the AppBuilder system.
Reads all secrets from .env file in the project root.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically find and load .env from the appbuilder directory
_env_path = Path(__file__).parent / ".env"
print(f"[Config] Loading .env from: {_env_path}", flush=True)
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
    print("[Config] ✅ .env file found.", flush=True)
else:
    print("[Config] ⚠️  .env file NOT found! Using system environment variables.", flush=True)


class Config:
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # GitHub
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_USERNAME: str = os.getenv("GITHUB_USERNAME", "")

    # Discord
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")

    @classmethod
    def validate(cls):
        """Raise an error if critical secrets are missing."""
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if not cls.GITHUB_USERNAME:
            missing.append("GITHUB_USERNAME")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file at: {_env_path}"
            )


config = Config()
