import time
import json
import json_repair
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
6. EXTREMELY IMPORTANT: Keep the code CONCISE. Avoid massive SVG blocks, huge repetitive CSS, or thousands of lines of boilerplate. Focus on functional core logic. If a feature needs a lot of data, use a small sample. Your output MUST fit within the token limit.
7. If the user doesn't specify a tech stack, choose the most appropriate one.
8. Include error handling, logging, and environment variable support.
9. repo_name must be all lowercase with hyphens, no spaces or special chars.
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
                    contents=user_prompt + "\n\nCRITICAL: DO NOT get stuck in a repetition loop. Output concise, complete code and terminate normally. Your output must fit within the token limit.",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.4,  # Increased from 0.1 to prevent repetition loops
                        max_output_tokens=65536,  # Significantly increased limit
                        response_mime_type="application/json", # Native JSON Enforcement
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
            # json_repair magically fixes unescaped quotes, missing commas, and extreme truncation
            data = json_repair.loads(raw_text)
            if not isinstance(data, dict):
                raise ValueError(f"Parsed JSON is not a dictionary. Got: type {type(data)}")
        except Exception as e:
            snippet = raw_text[-150:]
            raise ValueError(
                f"Gemini returned invalid JSON that could not be repaired: {e}\n\n"
                f"End of response: ...{snippet}\n\n"
                "The requested app is too complex for a single generation. Try a simpler prompt."
            )

        # Validate required keys
        required_keys = ["repo_name", "description", "files", "readme", "how_to_run"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Gemini response missing required key: '{key}'")

        # Inject token usage stats
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            data["tokens_used"] = response.usage_metadata.candidates_token_count
            data["tokens_prompt"] = response.usage_metadata.prompt_token_count
            print(f"[Gemini] 📊 Tokens Used: {data['tokens_used']} (Prompt: {data['tokens_prompt']})")

        print(f"[Gemini] ✅ Generated '{data['repo_name']}' — {len(data['files'])} files")
        return data
