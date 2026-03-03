#!/usr/bin/env python3
"""
build.py — Termux / CLI interface for AppBuilder.

Usage (from phone/terminal):
  cd appbuilder
  python cli/build.py "make me a weather app with FastAPI backend and React frontend"

This will:
  1. Generate the full app with Gemini AI
  2. Push it to a private GitHub repo
  3. Print the repo URL

Designed to run on Termux (Android) or any terminal.
"""

import sys
import os
import argparse

# Fix import path so we can run from any location
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="🚀 AppBuilder CLI — Generate full-stack apps from plain English",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli/build.py "todo app with React and Node.js"
  python cli/build.py "REST API for a bookstore with FastAPI and PostgreSQL"
  python cli/build.py "Discord bot that tracks stock prices"
  python cli/build.py "simple blog with Django and SQLite, dark mode UI"
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Plain-English description of the app to build",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enter multi-line prompt interactively",
    )
    
    args = parser.parse_args()

    # Get the prompt
    if args.interactive or not args.prompt:
        print("\n🚀 AppBuilder — Interactive Mode")
        print("Describe the app you want to build (press Enter twice when done):\n")
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        prompt = "\n".join(lines).strip()
        if not prompt:
            print("❌ No prompt provided. Exiting.")
            sys.exit(1)
    else:
        prompt = args.prompt.strip()
        if not prompt:
            print("❌ Prompt cannot be empty.")
            sys.exit(1)

    # Run the pipeline
    try:
        result = run_pipeline(prompt)

        print("\n" + "─" * 60)
        print(f"  🎉 SUCCESS!")
        print("─" * 60)
        print(f"  📦 Repo:        {result['repo_url']}")
        print(f"  📝 Name:        {result['repo_name']}")
        print(f"  📁 Files:       {result['file_count']}")
        print(f"  🛠  Tech Stack:  {', '.join(result['tech_stack'] or ['auto'])}")
        print("─" * 60)
        print(f"\n  ▶️  HOW TO RUN:\n")
        print(result.get("how_to_run", "See HOW_TO_RUN.md in the repo."))
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
