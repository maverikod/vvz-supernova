"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Index + theory text loading utilities.

Supports:
- Loading `ALL_index.yaml` with a lightweight pickle cache.
- Loading theory text from:
  - a single aggregated markdown file, or
  - a manifest file containing a list of part filenames (one per line),
    where part files are concatenated in order.
"""

from __future__ import annotations

import glob
import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from .index_data import IndexData
from .segment import Segment


def build_index(raw: Dict[str, Any]) -> IndexData:
    """
    Build an IndexData from a raw YAML-loaded dict.

    Skips segment entries that fail to parse. Other top-level keys are
    preserved in IndexData.raw.
    """
    segs: List[Segment] = []
    for d in raw.get("segments", []):
        if isinstance(d, dict):
            try:
                segs.append(Segment.from_dict(d))
            except Exception:
                continue
    return IndexData(segs, raw)


def load_index(path: str, use_cache: bool = True) -> IndexData:
    """
    Load index from YAML path, with optional pickle cache.

    If use_cache is True, a .pkl file alongside the YAML is used when
    mtime and size match; otherwise the YAML is loaded and the cache updated.
    """
    p = Path(path).resolve()
    cache_path = str(p) + ".pkl"

    mtime = os.path.getmtime(p)
    size = os.path.getsize(p)

    if use_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                payload = pickle.load(f)
            if payload.get("mtime") == mtime and payload.get("size") == size:
                return build_index(payload["data"])
        except Exception:
            pass

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    if use_cache:
        try:
            with open(cache_path, "wb") as f:
                pickle.dump({"mtime": mtime, "size": size, "data": raw}, f)
        except Exception:
            pass

    return build_index(raw)


def _is_sqlite_file(p: Path) -> bool:
    """Return True if path points to a file whose first bytes are SQLite magic."""
    try:
        with open(p, "rb") as f:
            sig = f.read(16)
        return sig.startswith(b"SQLite format 3")
    except Exception:
        return False


def _is_chain_manifest_file(p: Path) -> bool:
    """
    Exclude chain manifest (*.chain.sqlite) that is not a DB shard
    (*.chain.partN.sqlite).
    """
    if not p.name.endswith(".sqlite"):
        return False
    if re.search(r"\.chain\.part\d+\.sqlite$", p.name, re.IGNORECASE):
        return False
    return bool(re.search(r"\.chain\.sqlite$", p.name, re.IGNORECASE))


def _load_manifest_paths(manifest_path: Path) -> List[Path]:
    """
    Read a manifest file: one path per line, resolved against manifest dir.

    Blank lines and lines starting with # are skipped.
    """
    base_dir = manifest_path.parent
    lines = [
        ln.strip() for ln in manifest_path.read_text(encoding="utf-8").splitlines()
    ]
    files: List[Path] = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        files.append((base_dir / ln).resolve())
    return files


def load_theory_lines(path: str) -> List[str]:
    """
    Load theory lines from:
    - a single markdown file, or
    - a manifest (list of part files).

    Manifest is detected heuristically:
    - file is not SQLite;
    - file extension is not `.md` OR first non-empty line ends with `.md`.
    """

    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(str(p))

    if _is_sqlite_file(p):
        raise ValueError(f"--theory must be markdown or manifest, got SQLite: {p}")

    text = p.read_text(encoding="utf-8")
    first_non_empty: Optional[str] = None
    for ln in text.splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            first_non_empty = s
            break

    looks_like_manifest = False
    if p.suffix.lower() != ".md":
        looks_like_manifest = True
    if first_non_empty and first_non_empty.lower().endswith(".md"):
        looks_like_manifest = True

    if not looks_like_manifest:
        return text.splitlines(True)

    parts = _load_manifest_paths(p)
    out: List[str] = []
    for part in parts:
        out.extend(part.read_text(encoding="utf-8").splitlines(True))
    return out


def resolve_db_paths(db_path: str, db_path_glob: Optional[str] = None) -> List[Path]:
    """
    Resolve `--db-path` or `--db-path-glob` into a list of sqlite files.

    Supported:
    - a single `.sqlite` file;
    - a directory (all `*.sqlite` inside, sorted);
    - a manifest text file listing `.sqlite` filenames (one per line);
    - a glob pattern (via `--db-path-glob`);
    - auto-detect chain mode: if `db_path` is `chain.partXXX.sqlite`,
      automatically finds all `chain.part*.sqlite` in the same directory.

    Args:
        db_path: Path to single file, directory, or manifest.
        db_path_glob: Optional glob pattern (e.g., "*.chain.part*.sqlite").

    Returns:
        Sorted list of Path objects to SQLite files.
    """

    # Priority 1: explicit glob pattern
    if db_path_glob:
        matches = sorted(Path(p).resolve() for p in glob.glob(db_path_glob))
        sqlite_matches = [p for p in matches if p.is_file() and _is_sqlite_file(p)]
        if sqlite_matches:
            return sqlite_matches

    p = Path(db_path).resolve()

    # Priority 2: directory — all *.sqlite except chain manifest
    # (search uses all chain parts)
    if p.is_dir():
        candidates = sorted(p.glob("*.sqlite"))
        return [c for c in candidates if not _is_chain_manifest_file(c)]

    # Priority 3: single SQLite file
    if p.is_file() and _is_sqlite_file(p):
        # Auto-detect chain mode: if filename matches chain.partXXX.sqlite pattern
        # and there are other chain.part*.sqlite files in the same directory,
        # include all of them
        chain_match = re.search(r"chain\.part\d+\.sqlite$", p.name, re.IGNORECASE)
        if chain_match:
            parent_dir = p.parent
            chain_pattern = re.sub(
                r"chain\.part\d+\.sqlite$",
                "chain.part*.sqlite",
                p.name,
                flags=re.IGNORECASE,
            )
            chain_files = sorted(parent_dir.glob(chain_pattern))
            if len(chain_files) > 1:
                # Found multiple chain parts, return all of them
                return chain_files
        return [p]

    # Priority 4: manifest file
    if p.is_file():
        return _load_manifest_paths(p)

    return []


def segment_to_dict(seg: Segment) -> Dict[str, Any]:
    """Convert a Segment to a dict suitable for JSON or YAML serialization."""
    return {
        "id": seg.id,
        "category": seg.category,
        "keywords": seg.keywords,
        "summary": seg.summary,
        "start_line": seg.start_line,
        "end_line": seg.end_line,
        "ranges": [{"start_line": a, "end_line": b} for (a, b) in seg.ranges],
    }
