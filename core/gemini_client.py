"""
gemini_client.py — Wraps the Gemini API to turn NLP prompts into structured app blueprints.
"""

import time
import json
import re
import sys
from google import genai
from google.genai import types
from config import config

SYSTEM_PROMPT = """
You are an expert full-stack software engineer and architect. 
Your ONLY job is to receive a plain-English description of an application and return a complete, production-ready codebase for it.

RULES:
1. You MUST respond with valid JSON only. No markdown, no explanation, no preamble.
2. The JSON must match this exact schema:

{
  "repo_name": "kebab-case-repo-name",
  "description": "One-line description of the app",
  "tech_stack": ["list", "of", "technologies"],
  "files": [
    {
      "path": "relative/path/to/file.ext",
      "content": "full file content as a string"
    }
  ],
  "readme": "Full README.md content in markdown",
  "technical_docs": "Full TECHNICAL_DOCS.md content in markdown",
  "how_to_run": "Step-by-step instructions to run the app locally"
}

3. Generate a COMPLETE, working application. Include:
   - All source code files
   - package.json / requirements.txt / go.mod (whichever applies)
   - Dockerfile (always include one)
   - .gitignore
   - README.md (in the 'readme' field)
   - TECHNICAL_DOCS.md (in the 'technical_docs' field)
   - Any config files needed

4. Make real, functional code. Not placeholder code. Not TODO comments.
5. Use modern best practices and patterns for the chosen tech stack.
6. If the user doesn't specify a tech stack, choose the most appropriate one.
7. Include error handling, logging, and environment variable support.
8. repo_name must be all lowercase with hyphens, no spaces or special chars.
"""


class GeminiClient:
    def __init__(self):
        # Using the new genai SDK and gemini-2.5-flash
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def generate_app(self, user_prompt: str) -> dict:
        """
        Send a natural language prompt to Gemini and return a structured app blueprint.
        Retries up to 3 times with exponential backoff on rate limit errors.
        """
        print(f"[Gemini] Sending prompt to Gemini API...")
        
        last_err = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,  # Lower temperature for more consistent JSON
                        max_output_tokens=65536,  # Significantly increased limit
                    ),
                )
                break  # success
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "quota" in err_str or "resource" in err_str or "429" in err_str:
                    wait = 30 * (2 ** attempt)  # 30s, 60s, 120s
                    print(f"[Gemini] Rate limit hit (attempt {attempt+1}/3). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        else:
            raise last_err

        raw_text = response.text.strip()
        
        # Strip markdown code fences if Gemini wraps response in ```json ... ```
        if "```json" in raw_text:
            raw_text = re.sub(r"```json\s*", "", raw_text)
            raw_text = re.sub(r"\s*```", "", raw_text)
        elif "```" in raw_text:
            # Generic fence
            components = raw_text.split("```")
            if len(components) >= 3:
                raw_text = components[1]
                # If the first line of the block is a language name (e.g. 'json'), remove it
                raw_text = re.sub(r"^\w+\n", "", raw_text)

        raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"[Gemini] ⚠️ JSON parse error: {e}. Attempting advanced repair...")
            repaired_text = raw_text
            
            # 1. If it ends inside a string (no trailing quote), add a quote
            if repaired_text.count('"') % 2 != 0:
                # If it ends with an escape char, remove it first so we don't escape our fix
                if repaired_text.endswith('\\'):
                    repaired_text = repaired_text[:-1]
                repaired_text += '"'

            # 2. Add an arbitrary amount of closing brackets/braces
            # Count them up
            open_braces = repaired_text.count('{')
            close_braces = repaired_text.count('}')
            open_brackets = repaired_text.count('[')
            close_brackets = repaired_text.count(']')
            
            # Close whatever is currently open. Since we don't know the exact order,
            # this is a heuristic. We'll close strings, arrays, then objects.
            # A common truncation is inside the "files" array:
            # "...content": "some code" }
            # We need to add  ] } 
            
            # Just append a bunch of closers and let the JSON parser ignore trailing garbage? 
            # No, standard JSON doesn't allow trailing garbage.
            # Let's try to intelligently close it purely based on counts.
            missing_brackets = max(0, open_brackets - close_brackets)
            missing_braces = max(0, open_braces - close_braces)
            
            # If we were in the middle of a key/value pair but didn't finish the value...
            if repaired_text.rstrip().endswith(','):
                repaired_text = repaired_text.rstrip()[:-1]  # remove trailing comma
                
            # If we ended on a bare key:
            if repaired_text.rstrip().endswith(':'):
                repaired_text += '""' # add empty string value
                
            # Close arrays and objects. Usually arrays are inside objects in our schema.
            repaired_text += ']' * missing_brackets
            repaired_text += '}' * missing_braces
            
            try:
                data = json.loads(repaired_text)
                print(f"[Gemini] ✅ Advanced JSON repair successful.")
                data["description"] += " (Note: Output was slightly truncated and auto-repaired)"
            except Exception as repair_e:
                snippet = raw_text[-150:]
                raise ValueError(
                    f"Gemini returned invalid JSON: {e}\n"
                    f"Repair also failed: {repair_e}\n\n"
                    f"End of response: ...{snippet}\n\n"
                    "The requested app is too complex for a single generation. Try a simpler prompt."
                )

        # Validate required keys
        required_keys = ["repo_name", "description", "files", "readme", "how_to_run"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Gemini response missing required key: '{key}'")

        print(f"[Gemini] ✅ Generated '{data['repo_name']}' — {len(data['files'])} files")
        return data
