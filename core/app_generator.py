"""
app_generator.py — Orchestrates the full app generation pipeline.
Takes an NLP prompt, returns an AppBundle with all generated content.
"""

from dataclasses import dataclass, field
from typing import List
from core.gemini_client import GeminiClient


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class AppBundle:
    repo_name: str
    description: str
    tech_stack: List[str]
    files: List[GeneratedFile]
    readme: str
    technical_docs: str
    how_to_run: str


class AppGenerator:
    def __init__(self):
        self.gemini = GeminiClient()

    def generate(self, prompt: str) -> AppBundle:
        """
        Full pipeline: NLP prompt → AppBundle
        
        Args:
            prompt: Plain-English description of the app
            
        Returns:
            AppBundle with all generated content
        """
        print(f"[AppGenerator] Processing: \"{prompt[:80]}{'...' if len(prompt) > 80 else ''}\"")
        
        # Step 1: Call Gemini
        raw = self.gemini.generate_app(prompt)
        
        # Step 2: Parse files
        files = [
            GeneratedFile(path=f["path"], content=f["content"])
            for f in raw.get("files", [])
        ]
        
        # Inject README.md and TECHNICAL_DOCS.md as files too
        # (so they get committed to the repo)
        file_paths = {f.path for f in files}

        if "README.md" not in file_paths:
            files.insert(0, GeneratedFile(path="README.md", content=raw["readme"]))

        if "TECHNICAL_DOCS.md" not in file_paths and raw.get("technical_docs"):
            files.append(GeneratedFile(path="TECHNICAL_DOCS.md", content=raw["technical_docs"]))

        # Inject HOW_TO_RUN.md
        if "HOW_TO_RUN.md" not in file_paths:
            files.append(GeneratedFile(path="HOW_TO_RUN.md", content=raw.get("how_to_run", "")))

        bundle = AppBundle(
            repo_name=raw["repo_name"],
            description=raw.get("description", prompt[:100]),
            tech_stack=raw.get("tech_stack", []),
            files=files,
            readme=raw["readme"],
            technical_docs=raw.get("technical_docs", ""),
            how_to_run=raw.get("how_to_run", ""),
        )

        print(f"[AppGenerator] ✅ Bundle ready: {len(bundle.files)} files, repo: {bundle.repo_name}")
        return bundle
