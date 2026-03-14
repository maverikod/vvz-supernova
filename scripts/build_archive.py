"""
Build final deliverable zip: README.md, scripts/, raw/, data/, plots/, report/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/build_archive.py
Reads: project root (README.md, scripts/, raw/, data/, plots/, report/).
Outputs: supernova_atomic_data_pipeline.zip in project root (or dist/).
Excludes: .venv, __pycache__, .git, *.pyc and other gitignore-like artifacts
  inside included directories. Does not include supernova_atomic/, docs/, etc.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Archive name and top-level entries (Final archive; Third spec adds report/)
ARCHIVE_NAME = "supernova_atomic_data_pipeline.zip"
TOP_LEVEL_ENTRIES = ("README.md", "scripts", "raw", "data", "plots", "report")

# Path segments that must not appear in archived paths (exclude per .gitignore)
EXCLUDE_SEGMENTS = (
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".egg-info",
    ".eggs",
)
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".egg")


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _should_exclude(relative_path: Path) -> bool:
    """True if path should be excluded from archive (artifact/cache)."""
    parts = relative_path.parts
    for seg in EXCLUDE_SEGMENTS:
        if seg in parts:
            return True
    if relative_path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def _add_path(
    zf: zipfile.ZipFile,
    root: Path,
    entry: str,
    prefix: str,
) -> None:
    """
    Add a single top-level entry (file or directory) to the zip.
    Paths in archive are prefixed with prefix (e.g. '' for root-level).
    """
    full = root / entry
    if not full.exists():
        return
    if full.is_file():
        arcname = f"{prefix}{entry}" if prefix else entry
        zf.write(full, arcname=arcname)
        return
    # Directory: walk and add files, skipping excluded
    for path in full.rglob("*"):
        if path.is_dir():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if _should_exclude(rel):
            continue
        arcname = f"{prefix}{rel.as_posix()}" if prefix else rel.as_posix()
        zf.write(path, arcname=arcname)


def build_archive(
    root: Path | None = None,
    output_dir: Path | None = None,
    archive_name: str = ARCHIVE_NAME,
) -> Path:
    """
    Build zip with README.md, scripts/, raw/, data/, plots/, report/.

    Args:
        root: Project root; default from script location.
        output_dir: Where to write the zip; default project root.
        archive_name: Name of the zip file.

    Returns:
        Path to the created zip file.

    Raises:
        FileNotFoundError: If README.md is missing (blackstop).
    """
    if root is None:
        root = project_root()
    if output_dir is None:
        output_dir = root
    readme = root / "README.md"
    if not readme.exists():
        raise FileNotFoundError(
            f"README.md not found at {readme}; cannot build archive (blackstop)."
        )
    zip_path = output_dir / archive_name
    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False
    ) as zf:
        for entry in TOP_LEVEL_ENTRIES:
            _add_path(zf, root, entry, prefix="")
    return zip_path


def main() -> int:
    """Resolve paths, build zip, print path. Exit 0 on success."""
    root = project_root()
    try:
        out = build_archive(root=root, output_dir=root)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
