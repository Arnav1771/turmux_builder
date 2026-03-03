"""
gemini_client.py — Wraps the Gemini API to turn NLP prompts into web app blueprints.

DESIGN PHILOSOPHY (v3 — Web-App Only):
  The old approach tried to serialize MULTIPLE files inside a JSON blob, which
  meant any unescaped quote in generated code would break the entire payload.

  New approach: Gemini outputs ONE self-contained index.html (all CSS + JS + HTML
  inlined), plus a minimal README and Dockerfile. This is tiny, reliable, and
  always works for web/SaaS apps.
"""

import time
import json
import re
from google import genai
from google.genai import types
from config import config

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite front-end engineer specializing in building beautiful, 
functional, single-page web applications with pure HTML, CSS, and JavaScript.

Your ONLY job: receive a plain-English description and return a JSON object.

OUTPUT FORMAT (strict JSON, no markdown, no explanation):
{
  "repo_name": "kebab-case-app-name",
  "description": "One-line description",
  "tech_stack": ["HTML", "CSS", "JavaScript"],
  "html": "<FULL self-contained index.html content here>",
  "readme": "Short README.md in markdown",
  "how_to_run": "Open index.html in a browser."
}

RULES FOR THE HTML:
1. Everything in ONE index.html file. Inline all CSS in <style> and all JS in <script>.
2. Use Google Fonts (via CDN link tag) for beautiful typography.
3. Build a FULLY FUNCTIONAL, visually stunning app. No placeholders. No TODO.
4. Use modern design: dark theme OR light theme with gradient accents, smooth animations,
   hover effects, clean cards. Make it look like a premium product.
5. Include responsive design (mobile-friendly).
6. If the app needs an AI/API feature (translation, generation etc.), use the Gemini API
   directly from JS with fetch(). Use placeholder const GEMINI_API_KEY = "YOUR_KEY_HERE";
   that the user can fill in.
7. Keep your HTML CONCISE — use CSS and JS efficiently. Avoid repeating the same styles.

repo_name must be lowercase with hyphens only. No spaces.
"""


class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def generate_app(self, user_prompt: str) -> dict:
        """
        Send a natural language prompt and return a structured web app blueprint.
        Uses a single index.html approach to eliminate multi-file JSON complexity.
        """
        print(f"[Gemini] 🚀 Generating web app for: {user_prompt[:80]}...")

        full_prompt = (
            f"Build this web app: {user_prompt}\n\n"
            "Return ONLY valid JSON. The 'html' field must be a complete, working index.html "
            "with all CSS and JS inlined. Do NOT use markdown code fences."
        )

        last_err = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.5,
                        max_output_tokens=32000,  # Smaller limit = less chance of truncation
                        response_mime_type="application/json",
                    ),
                )
                break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "quota" in err_str or "resource" in err_str or "429" in err_str:
                    wait = 30 * (2 ** attempt)
                    print(f"[Gemini] Rate limit hit (attempt {attempt+1}/3). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        else:
            raise last_err  # type: ignore

        raw_text = response.text.strip()

        # Strip any markdown code fences (should not happen with mime type, but just in case)
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE)
        raw_text = raw_text.strip()

        # Parse the JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            snippet = raw_text[-200:]
            raise ValueError(
                f"❌ Gemini returned invalid JSON: {e}\n"
                f"End of response: ...{snippet}\n\n"
                "Try rephrasing your prompt to be more concise."
            )

        if not isinstance(data, dict):
            raise ValueError(
                f"❌ Unexpected response format from Gemini (got {type(data).__name__}, expected object). "
                "Please try again."
            )

        # Validate
        if not data.get("html"):
            raise ValueError("❌ Gemini did not generate the HTML for your app. Please try again.")

        if not data.get("repo_name"):
            data["repo_name"] = "my-web-app"

        # Build the files list from the single-html approach
        # This stays compatible with the rest of the pipeline (github_client, pipeline.py)
        data["files"] = [
            {"path": "index.html", "content": data["html"]},
            {"path": "README.md",  "content": data.get("readme", f"# {data['repo_name']}\n\n{data.get('description', '')}")},
        ]

        # Inject token usage stats
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            data["tokens_used"] = response.usage_metadata.candidates_token_count
            data["tokens_prompt"] = response.usage_metadata.prompt_token_count
            print(f"[Gemini] 📊 Tokens: {data['tokens_used']} out / {data['tokens_prompt']} in")

        how_to_run = data.get("how_to_run", "Open index.html in your browser.")
        data["how_to_run"] = how_to_run

        print(f"[Gemini] ✅ Generated '{data['repo_name']}' — {len(data['files'])} files")
        return data
