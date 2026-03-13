# Supernova Atomic Pipeline

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

Data pipeline: atomic spectral lines (NIST) and supernova catalogs (OSC, ASAS-SN, ZTF, etc.).  
Cleaned outputs go to `data/`; raw downloads to `raw/`. Flat layout (no `src/`).

- **Structure and PyPI**: see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- **Task spec**: [docs/task_supernova_atomic_pipeline.txt](docs/task_supernova_atomic_pipeline.txt)

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
python scripts/download_atomic_data.py   # then clean_*, download_supernova_*, etc.
```

## PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```
