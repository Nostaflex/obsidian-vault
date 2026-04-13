"""moc_freshness.py — détection des notes nouvelles depuis dernière régen MOC.

Pure detection layer (no regeneration). Used by /load-moc skill to surface
notes added between two nightly cron runs (the "freshness gap").

Architecture rationale:
- mtime-based dirty detection (file watchers unreliable on iCloud Drive)
- Skips .icloud placeholders + dotfiles
- Returns notes per MOC tag for downstream consumption
- No LLM calls, no I/O beyond stat() — safe to call on every retrieval
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# CLI exit codes
EXIT_OK = 0
EXIT_STALE = 1  # at least one MOC has stale notes (signal, not error)


def scan_active_notes(vault: Path, active_dirs: List[str]) -> List[Path]:
    """Return all active .md notes under `active_dirs`, sorted by name.

    Skips:
    - iCloud Drive placeholder stubs (`.<name>.icloud`)
    - Dotfiles (any path component starting with `.`)
    - Non-`.md` files
    """
    notes: List[Path] = []
    for d in active_dirs:
        root = vault / d
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if any(part.startswith(".") for part in path.relative_to(vault).parts):
                continue
            notes.append(path)
    return sorted(notes)


def _note_has_tag(note_path: Path, tag: str) -> bool:
    """Detect whether a note carries `tag` either via YAML frontmatter
    `tags: [...]` or via inline `#tag` (word-bounded)."""
    try:
        content = note_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    # 1. YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                tags = fm.get("tags", [])
                if isinstance(tags, list) and tag in tags:
                    return True
            except yaml.YAMLError:
                pass  # fall through to inline check

    # 2. Inline #tag (word-bounded so #architecture doesn't match #architectures)
    if re.search(rf"#{re.escape(tag)}\b", content):
        return True

    return False


def _moc_regen_timestamp(moc_path: Path) -> float:
    """Return the timestamp of the MOC's last *content regeneration*.

    Prefers the `last_updated: YYYY-MM-DD` field from the YAML frontmatter
    (set by the nightly regen) over filesystem mtime, because mtime is reset
    by any manual edit (frontmatter tweak, wikilink fix...) and would mask
    notes that were created between the regen and the manual edit.

    Falls back to mtime if the frontmatter is missing or malformed.
    Returns 0.0 if the MOC file does not exist (every tagged note then
    counts as stale relative to "nothing").
    """
    if not moc_path.exists():
        return 0.0
    try:
        content = moc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return moc_path.stat().st_mtime
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                last_updated = fm.get("last_updated")
                if last_updated:
                    # Accept date (YAML auto-converts YYYY-MM-DD) or string
                    if hasattr(last_updated, "year"):  # datetime.date or datetime
                        date_str = last_updated.isoformat()[:10]
                    else:
                        date_str = str(last_updated)[:10]
                    return (
                        datetime.strptime(date_str, "%Y-%m-%d")
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                    )
            except (yaml.YAMLError, ValueError):
                pass  # fall through to mtime
    return moc_path.stat().st_mtime


def find_stale_notes_for_moc(
    vault: Path,
    moc_path: Path,
    moc_tag: str,
    active_dirs: List[str],
) -> List[Path]:
    """Return notes tagged `moc_tag` that were modified after the MOC's last
    content regeneration (see `_moc_regen_timestamp`).

    If the MOC file is missing, every tagged note counts as stale (no snapshot
    to compare against — they're all "new" relative to nothing).
    """
    regen_ts = _moc_regen_timestamp(moc_path)
    return [
        n
        for n in scan_active_notes(vault, active_dirs)
        if n.stat().st_mtime > regen_ts and _note_has_tag(n, moc_tag)
    ]


def find_all_stale(
    vault: Path,
    moc_dir: Path,
    active_dirs: List[str],
) -> Dict[str, List[Path]]:
    """For every content MOC under `moc_dir` (excluding `moc-index.md`),
    return `{tag: [stale_notes]}`. MOCs with zero stale notes are omitted."""
    result: Dict[str, List[Path]] = {}
    if not moc_dir.exists():
        return result
    for moc_file in sorted(moc_dir.glob("moc-*.md")):
        if moc_file.name == "moc-index.md":
            continue
        tag = moc_file.stem[len("moc-") :]
        stale = find_stale_notes_for_moc(vault, moc_file, tag, active_dirs)
        if stale:
            result[tag] = stale
    return result


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

# Active vault dirs (notes generators may write here). Mirrors the convention
# used in integrity_check.py (PR#1) — kept independent here to avoid a
# cross-PR import dependency. Refactor when PR#1 lands on main.
_DEFAULT_ACTIVE_DIRS = ["universal", "projects", "gpparts"]


def _format_status(stale: Dict[str, List[Path]], vault: Path) -> str:
    if not stale:
        return "✅ All MOCs are fresh (no notes modified since last regen)."
    lines = ["⚠️ Stale MOCs (notes modified since last regen):"]
    for tag, notes in stale.items():
        lines.append(f"  #{tag} — {len(notes)} note(s):")
        for n in notes:
            lines.append(f"    {n.relative_to(vault)}")
    lines.append("")
    lines.append(
        "→ These notes won't appear in /load-moc routing until next nightly run."
    )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect notes added since last MOC regen (freshness gap)."
    )
    parser.add_argument(
        "--vault",
        default=".",
        help="Vault root (default: cwd).",
    )
    parser.add_argument(
        "--moc-dir",
        default="_meta/moc",
        help="MOC directory relative to vault (default: _meta/moc).",
    )
    parser.add_argument(
        "--active-dirs",
        nargs="+",
        default=_DEFAULT_ACTIVE_DIRS,
        help=f"Active dirs to scan (default: {_DEFAULT_ACTIVE_DIRS}).",
    )
    parser.add_argument(
        "--moc",
        help="Check only one specific MOC tag (e.g. 'architecture').",
    )
    args = parser.parse_args(argv)

    vault = Path(args.vault).resolve()
    moc_dir = vault / args.moc_dir

    if args.moc:
        moc_path = moc_dir / f"moc-{args.moc}.md"
        stale_notes = find_stale_notes_for_moc(
            vault, moc_path, args.moc, args.active_dirs
        )
        stale = {args.moc: stale_notes} if stale_notes else {}
    else:
        stale = find_all_stale(vault, moc_dir, args.active_dirs)

    print(_format_status(stale, vault))
    return EXIT_STALE if stale else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
