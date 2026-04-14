"""Tests for notebooklm_weekly.py logic classes (NLMClient is mocked)."""
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ── NLMClient command splitting (regression 2026-04-14) ───────────────────────

class TestNLMClientCommandSplitting:
    """NLM_MCP_CMD='npx notebooklm-mcp@latest' must be shlex-split into argv,
    not treated as a single binary name."""

    def test_start_splits_multiword_command(self):
        from notebooklm_weekly import NLMClient
        client = NLMClient(cmd="npx notebooklm-mcp@latest")
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.stdin = MagicMock()
            mock_popen.return_value.stdout = MagicMock()
            mock_popen.return_value.stderr = MagicMock()
            with patch.object(client, "_initialize"):
                client._start()
            argv = mock_popen.call_args[0][0]
            assert argv == ["npx", "notebooklm-mcp@latest"], f"cmd not split: {argv}"

    def test_start_single_word_command_still_works(self):
        from notebooklm_weekly import NLMClient
        client = NLMClient(cmd="notebooklm-mcp")
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.stdin = MagicMock()
            mock_popen.return_value.stdout = MagicMock()
            mock_popen.return_value.stderr = MagicMock()
            with patch.object(client, "_initialize"):
                client._start()
            argv = mock_popen.call_args[0][0]
            assert argv == ["notebooklm-mcp"]


# ── NotebookManager ──────────────────────────────────────────────────────────

class TestNotebookManagerRotation:
    def _make_domain_data(self, source_count: int, pushed: list = None) -> dict:
        return {
            "current": {
                "id": "nb_test123",
                "source_count": source_count,
                "created": "2026-04-06",
                "pushed_paper_ids": pushed or [],
            },
            "previous": None,
        }

    def test_needs_rotation_at_45(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation(self._make_domain_data(45)) is True

    def test_needs_rotation_below_45(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation(self._make_domain_data(44)) is False

    def test_needs_rotation_no_current(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        assert mgr.needs_rotation({"current": None, "previous": None}) is False

    def test_rotate_moves_current_to_previous(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        old = self._make_domain_data(45, pushed=["arxiv:2401.001"])
        result = mgr.rotate(old, "nb_new456")
        assert result["previous"]["id"] == "nb_test123"
        assert result["current"]["id"] == "nb_new456"
        assert result["current"]["source_count"] == 0
        assert result["current"]["pushed_paper_ids"] == []

    def test_increment_source_count(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        domain_data = self._make_domain_data(3, pushed=["arxiv:2401.001"])
        result = mgr.increment_source_count(domain_data, "arxiv:2401.002")
        assert result["current"]["source_count"] == 4
        assert "arxiv:2401.002" in result["current"]["pushed_paper_ids"]
        assert "arxiv:2401.001" in result["current"]["pushed_paper_ids"]

    def test_get_new_papers_excludes_pushed(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mgr = NotebookManager(Path(f.name))
        domain_data = {
            "current": {"id": "nb1", "source_count": 2, "pushed_paper_ids": ["arxiv:2401.001", "s2:abc123"]},
            "previous": {"id": "nb0", "source_count": 45, "pushed_paper_ids": ["arxiv:2400.001"]},
        }
        all_ids = ["arxiv:2401.001", "arxiv:2401.002", "arxiv:2400.001", "s2:new999"]
        result = mgr.get_new_papers(domain_data, all_ids)
        assert result == ["arxiv:2401.002", "s2:new999"]

    def test_atomic_write_and_load(self):
        from notebooklm_weekly import NotebookManager
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-notebooks.json"
            schema = {
                "schema_version": 1,
                "domains": {"ai": {"current": None, "previous": None}},
            }
            path.write_text(json.dumps(schema))
            mgr = NotebookManager(path)
            loaded = mgr.load()
            assert loaded["schema_version"] == 1
            loaded["domains"]["ai"]["current"] = {"id": "nb_abc", "source_count": 1, "pushed_paper_ids": []}
            mgr.save(loaded)
            reloaded = mgr.load()
            assert reloaded["domains"]["ai"]["current"]["id"] == "nb_abc"


# ── GroundingRouter ───────────────────────────────────────────────────────────

class TestGroundingRouter:
    def test_supported_with_multiple_sources(self):
        from notebooklm_weekly import GroundingRouter
        text = (
            "The evidence strongly supports this claim. [Source 1] demonstrates "
            "the effect clearly, consistent with prior work. [Source 2] corroborates "
            "these findings and confirms the hypothesis."
        )
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "supported"
        assert confidence >= 0.65

    def test_disputed_with_contradictions(self):
        from notebooklm_weekly import GroundingRouter
        text = (
            "While [Source 1] supports this, [Source 2] contradicts the main claim. "
            "The evidence is inconsistent across sources, with mixed results."
        )
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "disputed"
        assert confidence < 0.5

    def test_partially_supported_single_source(self):
        from notebooklm_weekly import GroundingRouter
        # Exactly 1 support phrase ("according to"), 2 sources, 0 dispute phrases
        # → must land unambiguously in partially_supported.
        text = "According to prior work [Source 1] [Source 2], the topic is discussed."
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "partially_supported"
        assert confidence == 0.60

    def test_insufficient_evidence_empty(self):
        from notebooklm_weekly import GroundingRouter
        verdict, confidence = GroundingRouter.parse_verdict("")
        assert verdict == "insufficient_evidence"
        assert confidence == 0.0

    def test_insufficient_evidence_no_sources(self):
        from notebooklm_weekly import GroundingRouter
        text = "The topic is interesting but no sources were found in the notebook."
        verdict, confidence = GroundingRouter.parse_verdict(text)
        assert verdict == "insufficient_evidence"

    def test_confidence_is_float_between_0_and_1(self):
        from notebooklm_weekly import GroundingRouter
        for text in [
            "Strongly supports [Source 1] confirms shows evidence [Source 2]",
            "contradicts however contrary conflicts",
            "",
            "according to shows [Source 1]",
        ]:
            _, conf = GroundingRouter.parse_verdict(text)
            assert 0.0 <= conf <= 1.0, f"conf={conf} out of range for: {text!r}"


# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_record_success_resets_failures(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            path.write_text(json.dumps({"consecutive_failures": 3, "complete": False}))
            cb = CircuitBreaker(path)
            cb.record_success({"papers_added": 5})
            loaded = json.loads(path.read_text())
            assert loaded["complete"] is True
            assert loaded["consecutive_failures"] == 0
            assert loaded["status"] == "complete"
            assert "timestamp" in loaded
            assert loaded["papers_added"] == 5

    def test_record_failure_increments_counter(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            path.write_text(json.dumps({"consecutive_failures": 1}))
            cb = CircuitBreaker(path)
            failures = cb.record_failure("auth_error")
            assert failures == 2
            loaded = json.loads(path.read_text())
            assert loaded["consecutive_failures"] == 2
            assert loaded["complete"] is False
            assert loaded["reason"] == "auth_error"

    def test_load_missing_file_returns_defaults(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            cb = CircuitBreaker(Path(tmpdir) / "absent.json")
            state = cb.load()
            assert state["consecutive_failures"] == 0
            assert state["status"] == "not_initialized"

    def test_atomic_write_no_partial_state(self):
        from notebooklm_weekly import CircuitBreaker
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nlm-status.json"
            cb = CircuitBreaker(path)
            cb.record_success({"concepts_grounded": 3})
            assert not path.with_suffix(".json.tmp").exists()


# ── write_grounded_note ───────────────────────────────────────────────────────

class TestWriteGroundedNote:
    def _write(self, tmpdir, paper_id="arxiv:2401.12345", verdict="supported", confidence=0.87):
        from notebooklm_weekly import write_grounded_note
        return write_grounded_note(
            paper_id=paper_id,
            tier="S",
            source_chain=["origin: https://arxiv.org/abs/2401.12345", "via: abstract"],
            verdict=verdict,
            confidence=confidence,
            notebook_ids=["nb_abc123", "nb_xyz789"],
            nlm_response="The sources confirm this claim strongly.",
            output_dir=Path(tmpdir),
            today="2026-04-13",
        )

    def test_filename_uses_sanitized_paper_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            assert path.name == "B-arxiv-2401-12345-grounded.md"

    def test_s2_paper_id_sanitized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from notebooklm_weekly import write_grounded_note
            path = write_grounded_note(
                paper_id="s2:abc1234567890abc",
                tier="S",
                source_chain=["origin: https://example.com", "via: abstract"],
                verdict="partially_supported",
                confidence=0.60,
                notebook_ids=["nb_abc"],
                nlm_response="Partial evidence found.",
                output_dir=Path(tmpdir),
                today="2026-04-13",
            )
            assert path.name == "B-s2-abc1234567890abc-grounded.md"

    def test_frontmatter_contains_nlm_grounding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            text = path.read_text()
            fm = yaml.safe_load(text.split("---")[1])
            assert fm["nlm_grounding"]["verdict"] == "supported"
            assert fm["nlm_grounding"]["confidence"] == 0.87
            assert "nb_abc123" in fm["nlm_grounding"]["notebook_ids"]

    def test_frontmatter_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir)
            text = path.read_text()
            fm = yaml.safe_load(text.split("---")[1])
            for field in ("type", "maturity", "tier", "created", "paper_id", "source_chain"):
                assert field in fm, f"Missing required field: {field}"
            assert fm["maturity"] == "fleeting"
            assert fm["type"] == "concept"

    def test_disputed_adds_review_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir, verdict="disputed", confidence=0.30)
            content = path.read_text()
            assert "<!-- review-flag: nlm-disputed -->" in content

    def test_non_disputed_no_review_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(tmpdir, verdict="supported", confidence=0.90)
            content = path.read_text()
            assert "review-flag: nlm-disputed" not in content


# ── load_tier_s_concepts ──────────────────────────────────────────────────────

class TestLoadTierSConcepts:
    def _make_concept_file(self, tmpdir, paper_id: str, tier: str) -> Path:
        pid_sanitized = paper_id.replace(":", "-").replace(".", "-")
        path = Path(tmpdir) / f"A-{pid_sanitized}-1.md"
        fm = {
            "type": "concept",
            "maturity": "fleeting",
            "tier": tier,
            "created": "2026-04-13",
            "paper_id": paper_id,
            "source_chain": [f"origin: https://arxiv.org/abs/2401.001", "via: abstract"],
        }
        path.write_text(
            f"---\n{yaml.dump(fm, allow_unicode=True)}---\n\n# Titre test\n\nContenu.\n",
            encoding="utf-8",
        )
        return path

    def test_loads_only_tier_s(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_concept_file(tmpdir, "arxiv:2401.001", "S")
            self._make_concept_file(tmpdir, "arxiv:2401.002", "A")
            self._make_concept_file(tmpdir, "arxiv:2401.003", "S")
            results = load_tier_s_concepts(Path(tmpdir))
            assert len(results) == 2
            paper_ids = {r["paper_id"] for r in results}
            assert "arxiv:2401.001" in paper_ids
            assert "arxiv:2401.003" in paper_ids

    def test_extracts_title(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_concept_file(tmpdir, "arxiv:2401.001", "S")
            results = load_tier_s_concepts(Path(tmpdir))
            assert results[0]["title"] == "Titre test"

    def test_empty_dir_returns_empty(self):
        from notebooklm_weekly import load_tier_s_concepts
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_tier_s_concepts(Path(tmpdir)) == []
