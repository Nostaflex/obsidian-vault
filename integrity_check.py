#!/usr/bin/env python3
"""integrity_check.py — pre-nightly vault integrity validation.

Migration Python de integrity-check.sh (TD-2026-016).
Améliorations vs bash :
- Parsing markdown robuste (regex propre, pas sed)
- Atomic writes avec NamedTemporaryFile (fix race condition TD-017)
- Mode --strict par défaut (échec rsync critique = exit 1, fix TD-018)
- Tests pytest (voir tests/test_integrity_check.py)
- Portable Linux (plus de dépendances BSD)

Usage:
    python3 integrity_check.py           # strict mode (défaut)
    python3 integrity_check.py --best-effort   # rétro-compat bash (échecs masqués)
    python3 integrity_check.py --vault PATH    # override vault path

Exit codes:
    0 : tout OK
    1 : échec critique (rsync, crash non restore, wikilinks cassés en strict)
    2 : conflits iCloud détectés (requiert action manuelle)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ============================================================================
# Constants (rétro-compat avec integrity-check.sh)
# ============================================================================

VAULT_DEFAULT = Path.home() / "Documents" / "Obsidian" / "KnowledgeBase"
BACKUP_DEFAULT = Path.home() / ".second-brain-backup"

INDEX_CEILING = 300
EXCLUDED_NAMES = {"INDEX.md", "VAULT.md"}
EXCLUDED_NAME_PREFIXES = ("context-",)
EXCLUDED_PATH_SEGMENTS = ("_processed", "_archive")
EXCLUDED_EXTENSIONS = (".icloud",)
CONFLICT_PATTERN = "* conflicted copy*"
ACTIVE_ROOTS = ("universal", "projects")

# ============================================================================
# Couche 1 — Pure functions
# ============================================================================

_WIKILINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_TAGS_RE = re.compile(r"^Tags:\s*(.+)$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content.

    Returns {} if no frontmatter or if malformed.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        import yaml
        result = yaml.safe_load(match.group(1))
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def extract_title(content: str) -> str:
    """Extract first H1 title from markdown, skipping frontmatter.

    Robust to titles containing '#' (unlike bash `head -1 | sed`).
    """
    # Skip frontmatter if present
    fm = _FRONTMATTER_RE.match(content)
    scan_from = fm.end() if fm else 0
    match = _TITLE_RE.search(content, scan_from)
    return match.group(1).strip() if match else ""


def extract_tags(content: str) -> str:
    """Extract Tags: line from markdown, or '—' if absent (retro-compat bash)."""
    match = _TAGS_RE.search(content)
    return match.group(1).strip() if match else "—"


def extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from markdown content.

    Multi-line safe (unlike bash grep). Returns raw link target
    including path and alias (basename_of_link to resolve).
    """
    return _WIKILINK_RE.findall(content)


def basename_of_link(link: str) -> str:
    """Extract basename from a wikilink target.

    Obsidian resolves [[path/note|alias]] by basename 'note' only.
    """
    # Strip alias (after |)
    before_alias = link.split("|", 1)[0]
    # Strip path (after last /)
    return before_alias.rsplit("/", 1)[-1].strip()


def is_excluded_path(path: Path) -> bool:
    """Check if a path should be excluded from active notes scanning."""
    if path.name in EXCLUDED_NAMES:
        return True
    if any(path.name.startswith(p) for p in EXCLUDED_NAME_PREFIXES):
        return True
    if path.suffix in EXCLUDED_EXTENSIONS:
        return True
    parts = path.parts
    if any(seg in parts for seg in EXCLUDED_PATH_SEGMENTS):
        return True
    return False


# ============================================================================
# Couche 2 — Vault operations
# ============================================================================


def list_active_notes(vault: Path) -> list[Path]:
    """List all active .md notes in the vault (excluding _processed, _archive, etc.)."""
    notes: list[Path] = []
    for root_name in ACTIVE_ROOTS:
        root = vault / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if is_excluded_path(path.relative_to(vault)):
                continue
            notes.append(path)
    return sorted(notes)


def detect_icloud_conflicts(vault: Path) -> list[Path]:
    """Find iCloud sync conflict files (pattern: '* conflicted copy*').

    Scope restreint (fix B3 PR#1 review) :
    - Scanne uniquement les dossiers utilisateurs (ACTIVE_ROOTS + _meta + _inbox)
    - Exclut .git, _work.nosync (secrets), .obsidian, _logs, _archive, node_modules
    - Évite leak vers _logs/conflicts.txt + perf walk inutile sur .git
    """
    if not vault.exists():
        return []
    scan_roots = list(ACTIVE_ROOTS) + ["_meta", "_inbox"]
    excluded_dirs = {".git", "_work.nosync", ".obsidian", "_archive", "_processed", "node_modules", "sensitive.nosync"}
    conflicts: list[Path] = []
    for root_name in scan_roots:
        root = vault / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            # Skip if any path component is in excluded_dirs
            if any(part in excluded_dirs for part in path.parts):
                continue
            if path.is_file() and "conflicted copy" in path.name:
                conflicts.append(path)
    return sorted(conflicts)


def rebuild_index(vault: Path, work_nosync: bool = True) -> str:
    """Rebuild INDEX.md content from actual vault files.

    Format identique à integrity-check.sh pour rétro-compat.
    """
    notes = list_active_notes(vault)
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# INDEX — Knowledge Base",
        "",
        f"Mis à jour : {today} | Notes actives : {len(notes)} | Plafond : {INDEX_CEILING}",
        "",
        "_Dérivé — recalculé par integrity-check.sh avant chaque run nocturne._",
        "_Ne pas éditer manuellement._",
        "",
        "---",
        "",
    ]

    for note in notes:
        try:
            content = note.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        title = extract_title(content) or note.stem
        tags = extract_tags(content)
        relpath = note.relative_to(vault).as_posix()
        lines.append(f"- [{title}]({relpath}) — {tags}")

    # _work.nosync section (titres H1 uniquement — contenu jamais lu publiquement)
    if work_nosync:
        work_dir = vault / "_work.nosync"
        if work_dir.exists():
            work_notes = sorted(
                p for p in work_dir.rglob("*.md") if p.name != "README.md"
            )
            if work_notes:
                lines.extend([
                    "",
                    "### Travail (index structurel — contenu local uniquement)",
                    "",
                ])
                for note in work_notes:
                    try:
                        content = note.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    title = extract_title(content) or note.stem
                    relpath = note.relative_to(vault).as_posix()
                    lines.append(f"- [🔒 {title}]({relpath}) — work-only")

    return "\n".join(lines) + "\n"


def find_broken_wikilinks(vault: Path) -> list[str]:
    """Find all broken [[wikilinks]] in vault (target note doesn't exist).

    Resolves by basename (Obsidian convention).
    """
    notes = list_active_notes(vault)
    # Build basename index: "note-name" → exists
    basenames = {note.stem for note in notes}

    broken = set()
    for note in notes:
        try:
            content = note.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for link in extract_wikilinks(content):
            basename = basename_of_link(link)
            if basename and basename not in basenames:
                broken.add(link)
    return sorted(broken)


def detect_crash_status(log_path: Path) -> str | None:
    """Read last-nightly.json and return status string (or None if file missing)."""
    if not log_path.exists():
        return None
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "unknown"
    return data.get("status", "unknown")


def restore_status_after_crash(log_path: Path) -> None:
    """Update last-nightly.json status to 'restored_after_crash'.

    Atomic write via NamedTemporaryFile + os.replace (fix TD-017 race condition).
    Robust to missing file or corrupted JSON (fix B1 from PR#1 review):
    - FileNotFoundError → start with empty dict (vault was never run before)
    - JSONDecodeError → start with empty dict + log warning (avoid restore loop)
    """
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    except json.JSONDecodeError as e:
        print(f"⚠️  last-nightly.json corrupted ({e}) — recreating with restored status", file=sys.stderr)
        data = {}
    data["status"] = "restored_after_crash"

    # Atomic write : tempfile dans le même dossier pour os.replace atomique
    fd, tmp_path = tempfile.mkstemp(
        suffix=".json.tmp",
        prefix=".nightly-",
        dir=log_path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, log_path)
    except Exception:
        # Cleanup temp on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ============================================================================
# Couche 3 — Subprocess wrappers
# ============================================================================


def download_icloud(vault: Path) -> bool:
    """Force iCloud download of vault files (brctl download).

    Returns True if brctl available and ran (regardless of success).
    Returns False if brctl not found (non-macOS).
    Fix B4 PR#1 review: shutil.which is portable + faster than `which` subprocess.
    """
    if not shutil.which("brctl"):
        return False
    subprocess.run(
        ["brctl", "download", str(vault)],
        capture_output=True,
        check=False,
    )
    return True


def check_work_nosync_sync(vault: Path) -> bool:
    """Check if _work.nosync is being synced by iCloud (should NOT be).

    Returns True if sync detected (= PROBLEM), False otherwise.
    Fix B4 PR#1 review: guard brctl availability (Linux compat — was crashing FileNotFoundError).
    """
    work_nosync = vault / "_work.nosync"
    if not work_nosync.exists():
        return False
    if not shutil.which("brctl"):
        return False  # non-macOS: assume no iCloud sync
    result = subprocess.run(
        ["brctl", "status", str(work_nosync)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).lower()
    return any(kw in output for kw in ("uploaded", "uploading", "download"))


def backup_vault(vault: Path, backup: Path, strict: bool = True) -> bool:
    """Backup vault to backup dir via rsync.

    Args:
        strict: If True, raise on rsync failure (TD-017 fix).
                If False, log warning and continue (retro-compat bash).
    """
    backup.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "rsync",
            "-a",
            "--quiet",
            f"{vault}/",
            f"{backup}/",
            "--exclude=*.icloud",
            "--exclude=* conflicted copy*",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"rsync backup failed (exit {result.returncode}): {result.stderr.decode(errors='replace')}"
        if strict:
            raise RuntimeError(msg)
        print(f"⚠️  {msg}", file=sys.stderr)
        return False
    return True


def restore_from_backup(backup: Path, vault: Path, strict: bool = True) -> bool:
    """Restore vault from backup (used after crash detection)."""
    result = subprocess.run(
        [
            "rsync",
            "-a",
            "--quiet",
            f"{backup}/",
            f"{vault}/",
            "--exclude=sensitive.nosync",
            "--exclude=_work.nosync",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"rsync restore failed (exit {result.returncode})"
        if strict:
            raise RuntimeError(msg)
        print(f"⚠️  {msg}", file=sys.stderr)
        return False
    return True


# ============================================================================
# Main orchestrator
# ============================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-nightly vault integrity check")
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_DEFAULT,
        help=f"Path to Obsidian vault (default: {VAULT_DEFAULT})",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        default=BACKUP_DEFAULT,
        help=f"Backup directory (default: {BACKUP_DEFAULT})",
    )
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="Retro-compat bash mode: mask errors with warnings (not recommended)",
    )
    args = parser.parse_args(argv)

    strict = not args.best_effort
    vault = args.vault
    backup = args.backup
    logs = vault / "_logs"
    logs.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"=== integrity-check {now_iso} ===")

    # Step 0. iCloud download
    if download_icloud(vault):
        print("✓ Fichiers iCloud disponibles localement")

    # Step 1. Backup rsync
    try:
        if backup_vault(vault, backup, strict=strict):
            print(f"✓ Backup OK → {backup}")
    except RuntimeError as e:
        print(f"🚨 {e}", file=sys.stderr)
        return 1

    # Step 1b. _work.nosync sync check
    if check_work_nosync_sync(vault):
        print("🚨 ALERTE: _work.nosync/ est en cours de sync iCloud — vérifier immédiatement")

    # Step 2. Crash detection + restore
    log_path = logs / "last-nightly.json"
    status = detect_crash_status(log_path)
    if status == "in_progress":
        print("⚠️  Run précédent interrompu (status: in_progress) — restore depuis backup")
        try:
            restore_from_backup(backup, vault, strict=strict)
            restore_status_after_crash(log_path)
            print(f"✓ Vault restauré depuis {backup}")
        except RuntimeError as e:
            print(f"🚨 {e}", file=sys.stderr)
            return 1

    # Step 3. iCloud conflicts
    conflicts = detect_icloud_conflicts(vault)
    conflicts_log = logs / "conflicts.txt"
    if conflicts:
        conflicts_log.write_text("\n".join(str(p) for p in conflicts) + "\n")
        print(f"⚠️  {len(conflicts)} copie(s) de conflit iCloud détectée(s) → {conflicts_log}")
        print("    Résoudre manuellement dans Obsidian avant de continuer")
    else:
        conflicts_log.write_text("")
        print("✓ Aucune copie de conflit iCloud")

    # Step 4. Rebuild INDEX.md → /tmp/INDEX_rebuilt.md
    index_content = rebuild_index(vault)
    index_tmp = Path("/tmp/INDEX_rebuilt.md")
    index_tmp.write_text(index_content, encoding="utf-8")
    note_count = len(list_active_notes(vault))
    print(f"✓ INDEX.md reconstruit ({note_count} notes) → {index_tmp}")
    # Fix B2 PR#1 review : warning si le plafond est dépassé
    if note_count > INDEX_CEILING:
        print(f"⚠️  Plafond INDEX_CEILING ({INDEX_CEILING}) dépassé : {note_count} notes — envisager archivage")

    # Step 5. Broken wikilinks
    broken = find_broken_wikilinks(vault)
    broken_log = logs / "broken-links.txt"
    if broken:
        broken_log.write_text("\n".join(f"BROKEN: [[{link}]]" for link in broken) + "\n")
        print(f"⚠️  {len(broken)} wikilink(s) cassé(s) → {broken_log}")
        for link in broken:
            print(f"BROKEN: [[{link}]]")
    else:
        broken_log.write_text("")
        print("✓ Aucun wikilink cassé")

    # Exit code
    if conflicts:
        print("=== integrity-check terminé (exit 2 : conflits iCloud) ===")
        return 2
    print("=== integrity-check terminé ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
