"""
pipeline.py — The master pipeline. Wires together AppGenerator + GitHubPusher + VercelDeployer.
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
    Full pipeline: NLP prompt → GitHub private repo → Vercel live URL.
    
    Args:
        prompt: Plain-English app description
        
    Returns:
        dict with keys: repo_url, live_url, repo_name, description, how_to_run, tech_stack
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
    repo_url, repo_obj = pusher.push(bundle)

    # Step 3: Deploy to Vercel (optional — only if VERCEL_TOKEN is set)
    live_url = None
    vercel_token = getattr(config, "VERCEL_TOKEN", None) or os.getenv("VERCEL_TOKEN")
    if vercel_token:
        try:
            from core.vercel_deployer import VercelDeployer
            deployer = VercelDeployer()
            # Pass raw dicts for Vercel (path + content)
            raw_files = [{"path": f.path, "content": f.content} for f in bundle.files]
            live_url = deployer.deploy(bundle.repo_name, raw_files, bundle.tech_stack)
            # Update GitHub repo description + homepage with the live URL
            pusher.update_description(repo_obj, live_url)
        except Exception as e:
            print(f"[Vercel] ⚠️ Deployment failed (non-fatal): {e}")
    else:
        print("[Vercel] ℹ️ VERCEL_TOKEN not set — skipping auto-deploy. Add it to .env to enable.")

    result = {
        "repo_url": repo_url,
        "live_url": live_url,
        "repo_name": bundle.repo_name,
        "description": bundle.description,
        "how_to_run": bundle.how_to_run,
        "tech_stack": bundle.tech_stack,
        "file_count": len(bundle.files),
        "tokens_used": bundle.__dict__.get("tokens_used"),
    }

    print(f"\n{'='*60}")
    print(f"  ✅ DONE! Your private repo is live:")
    print(f"  GitHub: {repo_url}")
    if live_url:
        print(f"  Vercel: {live_url}")
    print(f"{'='*60}\n")

    return result
