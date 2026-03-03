"""
groq_client.py — Two-pass code generation engine using Groq.

Groq is MUCH faster than Gemini (typically 5-10x) and uses the OpenAI-compatible API.

ARCHITECTURE (Two-Pass):
  Pass 1 (Plan):     Groq returns a small JSON manifest listing the files to create.
  Pass 2 (Generate): For each file, Groq generates raw plain-text content.
  Result:            Full multi-file apps (Flask, Docker, docs, etc.) with zero JSON issues.

Available models:
  - llama-3.3-70b-versatile   — Best quality, smartest (default)
  - llama-3.1-8b-instant      — Fastest, great for simple apps
  - mixtral-8x7b-32768        — Huge 32k context window
  - gemma2-9b-it              — Google's Gemma via Groq
"""

import time
import json
import re
from groq import Groq
from config import config

# ── System Prompts ─────────────────────────────────────────────────────────────

PLAN_PROMPT = """You are an expert software architect specializing in full-stack web and SaaS applications.

Your job is to receive a plain-English app description and return a JSON PLAN — a list of files to generate.

OUTPUT FORMAT (strict JSON object, no markdown):
{
  "repo_name": "kebab-case-app-name",
  "description": "One-line description of the app",
  "tech_stack": ["Python", "Flask", "HTML", "CSS", "JavaScript"],
  "files": [
    {"path": "app.py", "description": "Main Flask application with all routes"},
    {"path": "templates/index.html", "description": "Main HTML page with inline CSS and JS"},
    {"path": "requirements.txt", "description": "Python dependencies"},
    {"path": "Dockerfile", "description": "Docker container config"},
    {"path": ".gitignore", "description": "Git ignore rules"},
    {"path": "README.md", "description": "Project overview and setup guide"},
    {"path": "TECHNICAL_DOCS.md", "description": "API, architecture, and code documentation"},
    {"path": "HOW_TO_RUN.md", "description": "Step-by-step instructions to run locally and with Docker"}
  ],
  "how_to_run": "Brief steps: clone repo, install deps, run app"
}

RULES:
1. Support any tech stack: Flask, FastAPI, Node/Express, pure HTML/JS, etc.
2. Always include Dockerfile.
3. Always include README.md, TECHNICAL_DOCS.md, HOW_TO_RUN.md.
4. repo_name: lowercase, hyphens only.
5. Do NOT include any code in this response. Only the manifest.
"""

FILE_PROMPT_TEMPLATE = """You are an expert {tech} developer.

Generate the COMPLETE content for this file: {file_path}
Description: {file_description}

This file is part of: {app_description}
Tech stack: {tech_stack}

Rules:
- Output ONLY the raw file content. No explanations, no markdown fences, no preamble.
- Make it complete and production-ready. No placeholders, no TODO.
- For HTML: use Google Fonts CDN, modern dark/light theme, gradient accents, smooth animations, mobile-responsive.
- For Python/backend: proper logging, environment variables for secrets.
- For Dockerfiles: best security practices.
"""


class GroqClient:
    _override_model: str | None = None  # Set by /model Discord command at runtime

    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model_name = "llama-3.3-70b-versatile"  # Best quality default

    @property
    def active_model(self) -> str:
        return GroqClient._override_model or self.model_name

    def _call(self, prompt: str, system: str, json_mode: bool = False, max_tokens: int = 8192) -> str:
        """Internal helper to call Groq with retry logic."""
        last_err = None
        for attempt in range(3):
            try:
                kwargs = dict(
                    model=self.active_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.4,
                    max_tokens=max_tokens,
                )
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip(), response
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "rate" in err_str or "429" in err_str:
                    wait = 15 * (2 ** attempt)
                    print(f"[Groq] Rate limit (attempt {attempt+1}/3). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        raise last_err  # type: ignore

    def generate_app(self, user_prompt: str) -> dict:
        """
        Two-pass generation:
          Pass 1: Get a JSON manifest (file list + metadata).
          Pass 2: Generate each file's content as raw plain text.
        """
        # ── Pass 1: Plan ──────────────────────────────────────────────────────
        print(f"[Groq] 📋 Pass 1: Planning app structure with {self.active_model}...")
        plan_text, plan_response = self._call(
            prompt=f"Plan this application: {user_prompt}",
            system=PLAN_PROMPT,
            json_mode=True,
            max_tokens=2048,
        )

        # Strip fences just in case
        plan_text = re.sub(r"^```(?:json)?\s*", "", plan_text, flags=re.MULTILINE)
        plan_text = re.sub(r"\s*```$", "", plan_text, flags=re.MULTILINE).strip()

        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Failed to parse plan from Groq: {e}\nRaw: {plan_text[:500]}")

        if not isinstance(plan, dict) or "files" not in plan:
            raise ValueError(f"❌ Groq returned an unexpected plan format: {plan_text[:300]}")

        repo_name = plan.get("repo_name", "my-app")
        description = plan.get("description", user_prompt[:100])
        tech_stack = plan.get("tech_stack", ["HTML", "CSS", "JavaScript"])
        how_to_run = plan.get("how_to_run", "See HOW_TO_RUN.md")
        file_manifest = plan.get("files", [])
        tech_str = ", ".join(tech_stack)
        primary_tech = tech_stack[0] if tech_stack else "web"

        print(f"[Groq] ✅ Plan: {len(file_manifest)} files for '{repo_name}' ({tech_str})")

        # ── Pass 2: Generate each file ────────────────────────────────────────
        generated_files = []

        for i, file_entry in enumerate(file_manifest):
            file_path = file_entry.get("path", f"file_{i}.txt")
            file_desc = file_entry.get("description", f"File {i}")

            print(f"[Groq] 📝 ({i+1}/{len(file_manifest)}): {file_path}")

            file_prompt = FILE_PROMPT_TEMPLATE.format(
                tech=primary_tech,
                file_path=file_path,
                file_description=file_desc,
                app_description=f"{repo_name}: {description}",
                tech_stack=tech_str,
            )

            is_doc = file_path.endswith(".md") or file_path.endswith(".txt")
            max_tok = 2048 if is_doc else 8000

            try:
                content, _ = self._call(
                    prompt=file_prompt,
                    system=f"You are an expert {primary_tech} developer. Output ONLY raw file content with no markdown fences.",
                    json_mode=False,
                    max_tokens=max_tok,
                )
                # Strip any accidental markdown fences Groq might add
                content = re.sub(r"^```[\w]*\n?", "", content, flags=re.MULTILINE)
                content = re.sub(r"\n?```$", "", content, flags=re.MULTILINE).strip()

                generated_files.append({"path": file_path, "content": content})
                print(f"[Groq]    ✅ {file_path} ({len(content)} chars)")
            except Exception as e:
                print(f"[Groq]    ⚠️ Failed to generate {file_path}: {e}")
                generated_files.append({
                    "path": file_path,
                    "content": f"# Error generating this file\n# {e}\n",
                })

        # Token usage from plan call
        tokens_used = None
        if hasattr(plan_response, "usage") and plan_response.usage:
            tokens_used = plan_response.usage.completion_tokens
            total = plan_response.usage.total_tokens
            print(f"[Groq] 📊 Plan tokens: {tokens_used} out / {total} total")

        print(f"[Groq] 🎉 Done! {len(generated_files)} files for '{repo_name}'")

        return {
            "repo_name": repo_name,
            "description": description,
            "tech_stack": tech_stack,
            "files": generated_files,
            "readme": next((f["content"] for f in generated_files if f["path"] == "README.md"), ""),
            "technical_docs": next((f["content"] for f in generated_files if f["path"] == "TECHNICAL_DOCS.md"), ""),
            "how_to_run": how_to_run,
            "tokens_used": tokens_used,
        }
