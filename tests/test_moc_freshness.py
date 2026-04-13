# tests/test_moc_freshness.py
"""TDD pour moc_freshness.py — détection des notes nouvelles depuis dernière régen MOC."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from moc_freshness import (
    scan_active_notes,
    find_stale_notes_for_moc,
    find_all_stale,
)


@pytest.fixture
def tmp_vault(tmp_path):
    """Vault Obsidian minimal pour tests."""
    vault = tmp_path / "vault"
    (vault / "universal").mkdir(parents=True)
    (vault / "projects").mkdir(parents=True)
    (vault / "_meta" / "moc").mkdir(parents=True)
    (vault / "_inbox" / "raw").mkdir(parents=True)
    return vault


def _write_note(path: Path, body: str = "", mtime: float | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


ACTIVE = ["universal", "projects"]


# ---- scan_active_notes ----

class TestScanActiveNotes:
    def test_returns_md_files_from_active_dirs(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "a.md", "# A")
        _write_note(tmp_vault / "projects" / "b.md", "# B")
        result = scan_active_notes(tmp_vault, ACTIVE)
        names = sorted(p.name for p in result)
        assert names == ["a.md", "b.md"]

    def test_skips_icloud_placeholders(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "a.md", "# A")
        # iCloud placeholder pattern: leading dot + .icloud suffix
        _write_note(tmp_vault / "universal" / ".b.md.icloud", "stub")
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert [p.name for p in result] == ["a.md"]

    def test_skips_dotfiles(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "a.md", "# A")
        _write_note(tmp_vault / "universal" / ".hidden.md", "secret")
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert [p.name for p in result] == ["a.md"]

    def test_ignores_non_md_files(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "a.md", "# A")
        _write_note(tmp_vault / "universal" / "img.png", "binary")
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert [p.name for p in result] == ["a.md"]

    def test_excludes_dirs_outside_active(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "a.md", "# A")
        _write_note(tmp_vault / "_inbox" / "raw" / "draft.md", "# Draft")
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert [p.name for p in result] == ["a.md"]

    def test_recurses_into_subdirs(self, tmp_vault):
        _write_note(tmp_vault / "projects" / "sub" / "deep.md", "# Deep")
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert [p.name for p in result] == ["deep.md"]

    def test_returns_empty_when_no_md(self, tmp_vault):
        result = scan_active_notes(tmp_vault, ACTIVE)
        assert result == []


# ---- find_stale_notes_for_moc ----

class TestFindStaleNotesForMoc:
    def test_returns_notes_newer_than_moc_with_matching_tag(self, tmp_vault):
        moc = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        _write_note(moc, "# MOC architecture", mtime=1000.0)
        # Note newer than MOC, containing #architecture
        _write_note(
            tmp_vault / "projects" / "decision-X.md",
            "# Decision\n\nTags: #architecture #pipeline\n",
            mtime=2000.0,
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "architecture", ACTIVE)
        assert [p.name for p in result] == ["decision-X.md"]

    def test_excludes_notes_older_than_moc(self, tmp_vault):
        moc = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        _write_note(moc, "# MOC", mtime=2000.0)
        _write_note(
            tmp_vault / "projects" / "old.md",
            "Tags: #architecture\n",
            mtime=1000.0,  # older than MOC
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "architecture", ACTIVE)
        assert result == []

    def test_excludes_newer_notes_without_tag(self, tmp_vault):
        moc = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        _write_note(moc, "# MOC", mtime=1000.0)
        _write_note(
            tmp_vault / "projects" / "newer-but-untagged.md",
            "# No relevant tags\n",
            mtime=2000.0,
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "architecture", ACTIVE)
        assert result == []

    def test_detects_tag_in_yaml_frontmatter_tags_list(self, tmp_vault):
        moc = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        _write_note(moc, "# MOC", mtime=1000.0)
        _write_note(
            tmp_vault / "projects" / "fm-tagged.md",
            "---\ntype: architecture\ntags: [architecture, patterns]\n---\n# X\n",
            mtime=2000.0,
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "architecture", ACTIVE)
        assert [p.name for p in result] == ["fm-tagged.md"]

    def test_returns_empty_if_moc_missing(self, tmp_vault):
        # MOC doesn't exist (case: tag has 0 notes yet)
        missing = tmp_vault / "_meta" / "moc" / "moc-nonexistent.md"
        _write_note(
            tmp_vault / "projects" / "n.md",
            "Tags: #nonexistent\n",
        )
        result = find_stale_notes_for_moc(tmp_vault, missing, "nonexistent", ACTIVE)
        # Si MOC manquant, TOUTES les notes taggées sont "stale"
        assert [p.name for p in result] == ["n.md"]

    def test_uses_last_updated_frontmatter_over_mtime(self, tmp_vault):
        # Régression: éditer le MOC (fix wikilink, ajout tags...) ne doit pas
        # masquer une note non-indexée. last_updated frontmatter = vérité
        # sur la dernière régen du CONTENU.
        moc = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        # MOC: régénéré 2026-04-10, mais ÉDITÉ manuellement 2026-04-15 (mtime récent)
        _write_note(
            moc,
            "---\ntype: moc\nlast_updated: 2026-04-10\n---\n# MOC\n",
            mtime=1776211200.0,  # 2026-04-15 UTC — édition manuelle après régen
        )
        # Note créée 2026-04-13 (entre la régen du MOC et l'édition manuelle)
        _write_note(
            tmp_vault / "projects" / "newer-than-regen.md",
            "Tags: #architecture\n",
            mtime=1776038400.0,  # 2026-04-13 UTC
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "architecture", ACTIVE)
        # mtime-only logic dirait "fresh" (note mtime < moc mtime)
        # last_updated-aware logic dit "stale" (note mtime > last_updated UTC midnight)
        assert [p.name for p in result] == ["newer-than-regen.md"]

    def test_falls_back_to_mtime_when_no_last_updated(self, tmp_vault):
        # Régression: si frontmatter manque ou pas de last_updated, fallback mtime
        moc = tmp_vault / "_meta" / "moc" / "moc-x.md"
        _write_note(moc, "# MOC sans frontmatter\n", mtime=1000.0)
        _write_note(
            tmp_vault / "projects" / "n.md",
            "Tags: #x\n",
            mtime=2000.0,
        )
        result = find_stale_notes_for_moc(tmp_vault, moc, "x", ACTIVE)
        assert [p.name for p in result] == ["n.md"]


# ---- find_all_stale ----

class TestFindAllStale:
    def test_aggregates_across_existing_mocs(self, tmp_vault):
        moc_arch = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        moc_decision = tmp_vault / "_meta" / "moc" / "moc-decision.md"
        _write_note(moc_arch, "# MOC arch", mtime=1000.0)
        _write_note(moc_decision, "# MOC decision", mtime=1000.0)
        _write_note(
            tmp_vault / "projects" / "n1.md",
            "Tags: #architecture\n",
            mtime=2000.0,
        )
        _write_note(
            tmp_vault / "projects" / "n2.md",
            "Tags: #decision\n",
            mtime=2000.0,
        )
        result = find_all_stale(tmp_vault, tmp_vault / "_meta" / "moc", ACTIVE)
        assert set(result.keys()) == {"architecture", "decision"}
        assert [p.name for p in result["architecture"]] == ["n1.md"]
        assert [p.name for p in result["decision"]] == ["n2.md"]

    def test_excludes_moc_index_from_iteration(self, tmp_vault):
        # moc-index.md est le master index, pas un MOC content
        moc_index = tmp_vault / "_meta" / "moc" / "moc-index.md"
        _write_note(moc_index, "# Master Index", mtime=1000.0)
        _write_note(
            tmp_vault / "projects" / "n.md",
            "Tags: #index\n",
            mtime=2000.0,
        )
        result = find_all_stale(tmp_vault, tmp_vault / "_meta" / "moc", ACTIVE)
        assert "index" not in result

    def test_omits_mocs_with_no_stale_notes(self, tmp_vault):
        moc_arch = tmp_vault / "_meta" / "moc" / "moc-architecture.md"
        _write_note(moc_arch, "# MOC", mtime=2000.0)
        _write_note(
            tmp_vault / "projects" / "old.md",
            "Tags: #architecture\n",
            mtime=1000.0,
        )
        result = find_all_stale(tmp_vault, tmp_vault / "_meta" / "moc", ACTIVE)
        assert result == {}
