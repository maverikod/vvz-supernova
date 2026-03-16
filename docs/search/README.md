# Theory search (Θ) — integration in supernova project

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

Full-text search over theory blocks stored in SQLite. All paths are **relative to this directory** (`docs/search/`).

## Layout

| Path | Contents |
|------|----------|
| **db/** | SQLite shards (`ALL_theory_blocks.chain.part*.sqlite`), manifest (`ALL_theory_blocks.chain.sqlite`), `ALL_index.yaml`, `All.md` |
| **engine/** | Entrypoint `search_theory_index.py` and package `theory_index/` |
| **doc/** | Full documentation (README, QUICK_REFERENCE, AI_DOCUMENTATION, MULTI_DB_MODE, etc.) |

## Quick start (from project root)

```bash
# Search (no --index needed; default db dir = docs/search/db)
python docs/search/engine/search_theory_index.py --mode sqlite_search --phrase "масштаб" --format text

# Help
python docs/search/engine/search_theory_index.py --help
```

## Paths and defaults

- **Search root:** `docs/search/` (set automatically when running the engine script).
- **Default DB directory:** `docs/search/db/` (all `*.sqlite` shards and manifest).
- **Default index/theory** (for validate, assemble, sqlite_build): `db/ALL_index.yaml`, `db/All.md` when present.

Override with `--db-path`, `--db-path-glob`, or `--db-dir` if needed.

**Dependency:** For logical queries (`--query` with AND/OR/NOT), install `pyparsing`: `pip install pyparsing>=3.0.0`.

## More documentation

See **doc/** for:

- **README.md** — install and usage (paths adapted to this project).
- **QUICK_REFERENCE.md** — modes and options.
- **AI_DOCUMENTATION.md** — full reference for AI/automation.
