"""
file_writer.py — Writes a generated AppBundle to a temp directory on disk.
"""

import os
import tempfile
import shutil
from pathlib import Path
from core.app_generator import AppBundle


class FileWriter:
    def write_to_temp(self, bundle: AppBundle) -> str:
        """
        Write all files in an AppBundle to a fresh temp directory.
        
        Args:
            bundle: The AppBundle to write
            
        Returns:
            Path to the temp directory containing all files
        """
        # Create a temp dir; caller is responsible for cleanup
        tmp_dir = tempfile.mkdtemp(prefix=f"appbuilder_{bundle.repo_name}_")
        print(f"[FileWriter] Writing {len(bundle.files)} files to: {tmp_dir}")

        for gen_file in bundle.files:
            dest_path = Path(tmp_dir) / gen_file.path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(gen_file.content, encoding="utf-8")
            print(f"[FileWriter]   ✍  {gen_file.path}")

        print(f"[FileWriter] ✅ Done writing files.")
        return tmp_dir

    def cleanup(self, tmp_dir: str):
        """Remove the temp directory after pushing to GitHub."""
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"[FileWriter] 🧹 Cleaned up: {tmp_dir}")
