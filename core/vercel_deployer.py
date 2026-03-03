"""
vercel_deployer.py — Deploys a generated app to Vercel via the Vercel API.

Supports:
  - Static sites (index.html, CSS, JS)
  - Flask/Python apps via Vercel serverless (auto-detects based on tech stack)

Docs: https://vercel.com/docs/rest-api
"""

import os
import json
import hashlib
import time
import requests
from config import config


VERCEL_API = "https://api.vercel.com"


class VercelDeployer:
    def __init__(self):
        self.token = getattr(config, "VERCEL_TOKEN", None) or os.getenv("VERCEL_TOKEN")
        if not self.token:
            raise ValueError(
                "❌ VERCEL_TOKEN not set in .env. "
                "Get yours at: https://vercel.com/account/tokens"
            )
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _is_flask_app(self, files: list) -> bool:
        """Check if this is a Flask/Python backend app."""
        paths = [f["path"] for f in files]
        return any(p in paths for p in ["app.py", "main.py", "server.py"])

    def _build_vercel_json(self, files: list) -> dict | None:
        """Generate vercel.json config for Python/Flask apps."""
        if not self._is_flask_app(files):
            return None

        # Find the main python file
        paths = [f["path"] for f in files]
        main_file = next(
            (p.replace(".py", "") for p in ["app.py", "main.py", "server.py"] if p in paths),
            "app"
        )

        return {
            "builds": [{"src": f"{main_file}.py", "use": "@vercel/python"}],
            "routes": [{"src": "/(.*)", "dest": f"{main_file}.py"}]
        }

    def deploy(self, repo_name: str, files: list, tech_stack: list) -> str:
        """
        Deploy the app to Vercel and return the live URL.

        Args:
            repo_name: Kebab-case name for the project
            files: List of dicts with 'path' and 'content'
            tech_stack: List of technologies

        Returns:
            str: Live deployment URL
        """
        print(f"[Vercel] 🚀 Deploying '{repo_name}' to Vercel...")

        # Build the file list for the Vercel API
        vercel_files = []

        # Add vercel.json if needed for Flask apps
        vercel_config = self._build_vercel_json(files)
        if vercel_config:
            vercel_files.append({
                "file": "vercel.json",
                "data": json.dumps(vercel_config, indent=2)
            })
            print(f"[Vercel]    📄 Added vercel.json for Python/Flask deployment")

        for f in files:
            path = f.get("path", "").strip()
            content = f.get("content", "")
            if not path or not content:
                continue
            vercel_files.append({
                "file": path,
                "data": content,
            })

        if not vercel_files:
            raise ValueError("No files to deploy to Vercel.")

        # Create deployment
        payload = {
            "name": repo_name,
            "files": vercel_files,
            "projectSettings": {
                "framework": None,  # Let Vercel auto-detect
            },
            "target": "production",
        }

        resp = requests.post(
            f"{VERCEL_API}/v13/deployments",
            headers=self.headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code not in (200, 201):
            raise ValueError(
                f"❌ Vercel API returned {resp.status_code}: {resp.text[:500]}"
            )

        deployment = resp.json()
        deploy_id = deployment.get("id")
        deploy_url = deployment.get("url")

        if not deploy_id:
            raise ValueError(f"❌ Vercel deployment failed: {deployment}")

        print(f"[Vercel]    Deployment ID: {deploy_id}")
        print(f"[Vercel]    URL: https://{deploy_url}")

        # Wait for deployment to be ready
        live_url = self._wait_for_ready(deploy_id, deploy_url)
        print(f"[Vercel] ✅ Live at: {live_url}")
        return live_url

    def _wait_for_ready(self, deploy_id: str, deploy_url: str, max_wait: int = 120) -> str:
        """Poll until the deployment is ready or timeout."""
        start = time.time()
        while time.time() - start < max_wait:
            resp = requests.get(
                f"{VERCEL_API}/v13/deployments/{deploy_id}",
                headers=self.headers,
                timeout=15,
            )
            if resp.status_code == 200:
                state = resp.json().get("readyState", "")
                if state == "READY":
                    return f"https://{deploy_url}"
                elif state in ("ERROR", "CANCELED"):
                    raise ValueError(f"❌ Vercel deployment {state}: {resp.json()}")
                print(f"[Vercel]    Status: {state}... waiting")
            time.sleep(5)

        # Return the URL anyway even if we timed out polling
        return f"https://{deploy_url}"
