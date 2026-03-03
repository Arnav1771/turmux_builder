"""
pipeline.py — The master pipeline. Wires together AppGenerator + GitHubPusher.
Both the CLI and Discord bot call this.
"""

import sys
import os

# Make sure parent directory is on the path so imports work from any location
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config, Config
from core.app_generator import AppGenerator
from core.github_pusher import GitHubPusher


def run_pipeline(prompt: str) -> dict:
    """
    Full pipeline: NLP prompt → GitHub private repo.
    
    Args:
        prompt: Plain-English app description
        
    Returns:
        dict with keys: repo_url, repo_name, description, how_to_run, tech_stack
    """
    # Validate secrets first
    Config.validate()

    print(f"\n{'='*60}")
    print(f"  🚀 AppBuilder Pipeline Starting")
    print(f"{'='*60}")
    print(f"  Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    print(f"{'='*60}\n")

    # Step 1: Generate app with Gemini
    generator = AppGenerator()
    bundle = generator.generate(prompt)

    # Step 2: Push to GitHub
    pusher = GitHubPusher()
    repo_url = pusher.push(bundle)

    result = {
        "repo_url": repo_url,
        "repo_name": bundle.repo_name,
        "description": bundle.description,
        "how_to_run": bundle.how_to_run,
        "tech_stack": bundle.tech_stack,
        "file_count": len(bundle.files),
    }

    print(f"\n{'='*60}")
    print(f"  ✅ DONE! Your private repo is live:")
    print(f"  {repo_url}")
    print(f"{'='*60}\n")

    return result
