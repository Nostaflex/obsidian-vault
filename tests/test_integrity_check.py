# tests/test_integrity_check.py
"""Tests TDD pour integrity_check.py — migration depuis integrity-check.sh.

Couvre :
- Pure functions (parse, extract, format)
- Vault operations (via tmpdir fixture)
- Atomic writes (race condition fix)
- Crash detection + restore
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from integrity_check import (
    basename_of_link,
    detect_crash_status,
    detect_icloud_conflicts,
    extract_tags,
    extract_title,
    extract_wikilinks,
    find_broken_wikilinks,
    is_excluded_path,
    list_active_notes,
    parse_frontmatter,
    rebuild_index,
    restore_status_after_crash,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tmp_vault(tmp_path):
    """Vault Obsidian minimal pour les tests."""
    vault = tmp_path / "vault"
    (vault / "universal").mkdir(parents=True)
    (vault / "projects").mkdir(parents=True)
    (vault / "_logs").mkdir(parents=True)
    (vault / "_meta").mkdir(parents=True)
    (vault / "_work.nosync").mkdir(parents=True)
    return vault


def _write_note(path: Path, title: str, tags: str = "", body: str = ""):
    """Helper : écrit une note Obsidian avec titre et tags."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"# {title}\n"
    if tags:
        content += f"\nTags: {tags}\n"
    if body:
        content += f"\n{body}\n"
    path.write_text(content, encoding="utf-8")


# ============================================================================
# Couche 1 — Pure functions
# ============================================================================


class TestParseFrontmatter:
    def test_yaml_frontmatter_present(self):
        content = "---\ntype: concept\ntier: A\n---\n\n# Titre"
        result = parse_frontmatter(content)
        assert result == {"type": "concept", "tier": "A"}

    def test_no_frontmatter_returns_empty_dict(self):
        content = "# Titre\n\nContenu"
        assert parse_frontmatter(content) == {}

    def test_malformed_frontmatter_returns_empty_dict(self):
        # Fix I7 PR#1 review : utilise un YAML vraiment malformed
        # (l'ancien "not: valid: yaml: at: all" était en fait valide en YAML flow mapping)
        content = "---\n[unclosed bracket\n---"
        result = parse_frontmatter(content)
        assert result == {}, f"Expected empty dict on malformed YAML, got {result}"


class TestExtractTitle:
    def test_simple_title(self):
        assert extract_title("# Mon titre\n\nContenu") == "Mon titre"

    def test_title_with_hash_inside(self):
        # BUG bash original : `head -1 | sed 's/^# //'` casserait
        assert extract_title("# Hooks #PreToolUse explained") == "Hooks #PreToolUse explained"

    def test_title_with_emoji(self):
        assert extract_title("# 🚀 Sprint planning") == "🚀 Sprint planning"

    def test_no_title_returns_empty(self):
        assert extract_title("Pas de titre H1") == ""

    def test_frontmatter_then_title(self):
        content = "---\ntype: concept\n---\n\n# Vrai titre"
        assert extract_title(content) == "Vrai titre"


class TestExtractTags:
    def test_tags_line_present(self):
        content = "# Titre\n\nTags: #ai #notebooklm\n\nContenu"
        assert extract_tags(content) == "#ai #notebooklm"

    def test_no_tags_returns_dash(self):
        # Convention rétro-compat avec bash: "—"
        content = "# Titre sans tags"
        assert extract_tags(content) == "—"

    def test_tags_at_end(self):
        content = "# Titre\n\nContenu\n\nTags: #x"
        assert extract_tags(content) == "#x"


class TestExtractWikilinks:
    def test_single_wikilink(self):
        assert extract_wikilinks("Voir [[note-A]] pour plus") == ["note-A"]

    def test_multiple_wikilinks(self):
        content = "Liens : [[note-A]] et [[note-B]] et [[note-C]]"
        assert sorted(extract_wikilinks(content)) == ["note-A", "note-B", "note-C"]

    def test_wikilink_with_alias(self):
        # [[path/note|alias]] → on extrait le path, alias géré ailleurs
        assert extract_wikilinks("[[note-X|Mon alias]]") == ["note-X|Mon alias"]

    def test_wikilink_with_path(self):
        assert extract_wikilinks("[[universal/concept-Y]]") == ["universal/concept-Y"]

    def test_no_wikilinks(self):
        assert extract_wikilinks("Aucun lien dans ce texte") == []

    def test_multiline_content(self):
        # BUG bash : grep multiline cassé
        content = "Premier paragraphe\n\nSecond avec [[link-A]]\n\nTroisième [[link-B]]"
        assert sorted(extract_wikilinks(content)) == ["link-A", "link-B"]


class TestBasenameOfLink:
    def test_simple_link(self):
        assert basename_of_link("note-A") == "note-A"

    def test_link_with_path(self):
        # Obsidian résout par basename uniquement
        assert basename_of_link("universal/concept-X") == "concept-X"

    def test_link_with_alias(self):
        # [[note|alias]] → basename = note (pas alias)
        assert basename_of_link("note-X|Mon alias") == "note-X"

    def test_link_with_path_and_alias(self):
        assert basename_of_link("universal/note-Y|alias") == "note-Y"


class TestIsExcludedPath:
    def test_processed_excluded(self):
        assert is_excluded_path(Path("universal/_processed/note.md")) is True

    def test_archive_excluded(self):
        assert is_excluded_path(Path("projects/_archive/old.md")) is True

    def test_icloud_excluded(self):
        assert is_excluded_path(Path("universal/note.icloud")) is True

    def test_normal_note_not_excluded(self):
        assert is_excluded_path(Path("universal/concept-A.md")) is False


# ============================================================================
# Couche 2 — Vault operations
# ============================================================================


class TestListActiveNotes:
    def test_empty_vault(self, tmp_vault):
        assert list_active_notes(tmp_vault) == []

    def test_lists_md_files(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "concept-A.md", "Concept A")
        _write_note(tmp_vault / "projects" / "decision-X.md", "Decision X")
        result = list_active_notes(tmp_vault)
        assert len(result) == 2

    def test_excludes_processed_archive_index(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "good.md", "Good")
        _write_note(tmp_vault / "universal" / "INDEX.md", "Index")
        _write_note(tmp_vault / "universal" / "VAULT.md", "Vault")
        _write_note(tmp_vault / "universal" / "_processed" / "old.md", "Old")
        _write_note(tmp_vault / "universal" / "_archive" / "ancien.md", "Ancien")
        result = list_active_notes(tmp_vault)
        assert len(result) == 1
        assert result[0].name == "good.md"


class TestDetectIcloudConflicts:
    def test_no_conflicts(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "normal.md", "Normal")
        assert detect_icloud_conflicts(tmp_vault) == []

    def test_conflict_detected(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "note (Mac mini conflicted copy 2026-04-12).md", "Conflict")
        _write_note(tmp_vault / "universal" / "normal.md", "Normal")
        result = detect_icloud_conflicts(tmp_vault)
        assert len(result) == 1
        assert "conflicted copy" in result[0].name


class TestRebuildIndex:
    def test_empty_vault_index(self, tmp_vault):
        index = rebuild_index(tmp_vault, work_nosync=False)
        assert "# INDEX — Knowledge Base" in index
        assert "Notes actives : 0" in index
        assert "Plafond : 300" in index

    def test_index_with_notes(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "concept-A.md", "Concept A", tags="#ai")
        _write_note(tmp_vault / "projects" / "decision-X.md", "Decision X", tags="#cloud")
        index = rebuild_index(tmp_vault, work_nosync=False)
        assert "Notes actives : 2" in index
        assert "[Concept A](universal/concept-A.md) — #ai" in index
        assert "[Decision X](projects/decision-X.md) — #cloud" in index

    def test_index_with_work_nosync(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "public.md", "Public note")
        _write_note(tmp_vault / "_work.nosync" / "secret.md", "Secret work")
        index = rebuild_index(tmp_vault, work_nosync=True)
        assert "### Travail (index structurel — contenu local uniquement)" in index
        assert "🔒 Secret work" in index


class TestFindBrokenWikilinks:
    def test_all_links_resolve(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "note-A.md", "Note A", body="Voir [[note-B]]")
        _write_note(tmp_vault / "universal" / "note-B.md", "Note B")
        assert find_broken_wikilinks(tmp_vault) == []

    def test_broken_link_detected(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "note-A.md", "Note A", body="Voir [[note-missing]]")
        result = find_broken_wikilinks(tmp_vault)
        assert "note-missing" in result

    def test_link_resolved_by_basename(self, tmp_vault):
        # Obsidian résout par basename même avec path partiel
        _write_note(tmp_vault / "universal" / "concept-Z.md", "Concept Z")
        _write_note(tmp_vault / "projects" / "decision.md", "Decision", body="Voir [[universal/concept-Z]]")
        assert find_broken_wikilinks(tmp_vault) == []

    def test_link_with_alias_resolves(self, tmp_vault):
        _write_note(tmp_vault / "universal" / "note-Y.md", "Note Y")
        _write_note(tmp_vault / "universal" / "ref.md", "Ref", body="Voir [[note-Y|Mon alias]]")
        assert find_broken_wikilinks(tmp_vault) == []


class TestDetectCrashStatus:
    def test_no_log_file(self, tmp_vault):
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        assert detect_crash_status(log_path) is None

    def test_completed_status(self, tmp_vault):
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text(json.dumps({"status": "completed"}))
        assert detect_crash_status(log_path) == "completed"

    def test_in_progress_status(self, tmp_vault):
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text(json.dumps({"status": "in_progress", "started_at": "2026-04-13T01:00Z"}))
        assert detect_crash_status(log_path) == "in_progress"

    def test_malformed_json_returns_unknown(self, tmp_vault):
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text("not valid json {{{")
        assert detect_crash_status(log_path) == "unknown"


class TestRestoreStatusAfterCrash:
    def test_atomic_write_no_race(self, tmp_vault):
        # Race fix : pas de /tmp/nightly.tmp partagé. Utilise NamedTemporaryFile + os.replace
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text(json.dumps({"status": "in_progress", "started_at": "2026-04-13T01:00Z"}))
        restore_status_after_crash(log_path)
        result = json.loads(log_path.read_text())
        assert result["status"] == "restored_after_crash"
        assert result["started_at"] == "2026-04-13T01:00Z"  # autres champs préservés

    def test_no_temp_file_leaked(self, tmp_vault):
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text(json.dumps({"status": "in_progress"}))
        restore_status_after_crash(log_path)
        # Aucun fichier .tmp ne traîne dans _logs/
        leaked = list((tmp_vault / "_logs").glob("*.tmp"))
        assert leaked == []

    def test_handles_missing_file(self, tmp_vault):
        # Fix B1 PR#1 review : restore robuste si le fichier n'existe pas
        log_path = tmp_vault / "_logs" / "missing.json"
        # Doit créer le fichier sans crasher
        restore_status_after_crash(log_path)
        result = json.loads(log_path.read_text())
        assert result == {"status": "restored_after_crash"}

    def test_handles_corrupted_json(self, tmp_vault):
        # Fix B1 PR#1 review : restore robuste si JSON corrompu (évite restore loop)
        log_path = tmp_vault / "_logs" / "last-nightly.json"
        log_path.write_text("{not valid json {{{")
        restore_status_after_crash(log_path)
        result = json.loads(log_path.read_text())
        assert result["status"] == "restored_after_crash"


# ============================================================================
# Couche 3 — Subprocess wrappers (I9 PR#1 review : tests via mock)
# ============================================================================


class TestSubprocessWrappers:
    """Tests pour download_icloud, check_work_nosync_sync, backup_vault, restore_from_backup.

    Mock subprocess.run + shutil.which pour tester sans dépendre de brctl/rsync réels.
    """

    def test_download_icloud_returns_false_when_brctl_missing(self, monkeypatch, tmp_vault):
        from integrity_check import download_icloud
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        assert download_icloud(tmp_vault) is False

    def test_download_icloud_calls_brctl_when_available(self, monkeypatch, tmp_vault):
        from integrity_check import download_icloud
        called = []
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/brctl")
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: called.append(args[0]) or subprocess.CompletedProcess(args[0], 0),
        )
        assert download_icloud(tmp_vault) is True
        assert called[0][:2] == ["brctl", "download"]

    def test_check_work_nosync_sync_no_dir(self, tmp_vault):
        from integrity_check import check_work_nosync_sync
        # _work.nosync est créé par fixture mais on le supprime pour ce test
        import shutil as sh
        sh.rmtree(tmp_vault / "_work.nosync")
        assert check_work_nosync_sync(tmp_vault) is False

    def test_check_work_nosync_sync_no_brctl(self, monkeypatch, tmp_vault):
        from integrity_check import check_work_nosync_sync
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        # Doit retourner False (pas crasher) sur Linux/non-macOS
        assert check_work_nosync_sync(tmp_vault) is False

    def test_check_work_nosync_sync_detects_uploading(self, monkeypatch, tmp_vault):
        from integrity_check import check_work_nosync_sync
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/brctl")
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="status: uploading\n", stderr=""),
        )
        assert check_work_nosync_sync(tmp_vault) is True

    def test_backup_vault_strict_raises_on_failure(self, monkeypatch, tmp_vault):
        from integrity_check import backup_vault
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b"rsync: error"),
        )
        with pytest.raises(RuntimeError, match="rsync backup failed"):
            backup_vault(tmp_vault, tmp_vault.parent / "backup", strict=True)

    def test_backup_vault_best_effort_returns_false_on_failure(self, monkeypatch, tmp_vault, capsys):
        from integrity_check import backup_vault
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b"rsync: error"),
        )
        result = backup_vault(tmp_vault, tmp_vault.parent / "backup", strict=False)
        assert result is False
        # Warning émis sur stderr
        captured = capsys.readouterr()
        assert "rsync backup failed" in captured.err
