# tests/test_paper_synthesizer.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_synthesizer import (
    _batch_custom_id,
    _build_concepts_summary,
    _extract_title,
    clear_batch_job,
    load_pending_batch_job,
    parse_concepts_from_text,
    parse_frontmatter,
    sanitize_paper_id,
    save_batch_job,
    slugify,
    write_concept_note,
)


class TestWriteConceptNote:
    def _concept(self, **overrides):
        base = {
            "paper_id": "arxiv:2401.12345",
            "tier": "A",
            "concept_title": "Example atomic concept",
            "source_url": "http://arxiv.org/abs/2401.12345",
            "simple_explanation": "In plain words.",
            "essence": "The essential claim.",
            "detail": "Longer reasoning and context.",
            "tags": ["transformers", "attention"],
        }
        base.update(overrides)
        return base

    def test_writes_file_with_expected_filename_pattern(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        concepts = tmp_path / "concepts"
        monkeypatch.setattr(ps, "CONCEPTS_DIR", concepts)
        path = write_concept_note(self._concept(), "ai", 16, "2026-04-14", index=1)
        assert path.exists()
        assert path.name == "A-arxiv-2401-12345-1.md"

    def test_frontmatter_contains_tier_and_tags(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "CONCEPTS_DIR", tmp_path / "concepts")
        path = write_concept_note(self._concept(tier="S"), "cloud", 16, "2026-04-14")
        content = path.read_text()
        assert "tier: S" in content
        assert "#cloud" in content
        assert "#transformers" in content
        assert "# Example atomic concept" in content

    def test_fallback_when_paper_id_missing(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "CONCEPTS_DIR", tmp_path / "concepts")
        path = write_concept_note(
            self._concept(paper_id="", source_url="http://x/y"),
            "ai", 16, "2026-04-14",
        )
        # Filename uses the fallback pattern
        assert path.name.startswith("A-unknown-")
        assert path.exists()

    def test_index_appears_in_filename(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "CONCEPTS_DIR", tmp_path / "concepts")
        p1 = write_concept_note(self._concept(), "ai", 16, "2026-04-14", index=1)
        p2 = write_concept_note(self._concept(), "ai", 16, "2026-04-14", index=2)
        assert p1.name.endswith("-1.md")
        assert p2.name.endswith("-2.md")

    def test_frontmatter_includes_paper_id_for_nlm_grounding(self, tmp_path, monkeypatch):
        # Régression TD-2026-025 : notebooklm_weekly.ground_concept() cherche
        # `paper_id:` dans frontmatter. Sans lui, 30/30 Tier S skipped au grounding
        # (premier run Track B 2026-04-14).
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "CONCEPTS_DIR", tmp_path / "concepts")
        concept = self._concept(paper_id="arxiv:2604.08545")
        path = write_concept_note(concept, "ai", 16, "2026-04-14")
        content = path.read_text()
        assert "paper_id: " in content
        # The value should be the original (unsanitized) paper_id so downstream
        # tooling can recognize arxiv prefix
        assert "arxiv:2604.08545" in content


class TestParseFrontmatter:
    def test_returns_empty_when_no_frontmatter(self):
        meta, body = parse_frontmatter("# Just a title\n\nBody text")
        assert meta == {}
        assert body == "# Just a title\n\nBody text"

    def test_extracts_simple_yaml_fields(self):
        txt = "---\ntitle: Hello\ntier: A\n---\n# Body"
        meta, body = parse_frontmatter(txt)
        assert meta["title"] == "Hello"
        assert meta["tier"] == "A"
        assert body == "# Body"

    def test_returns_empty_when_frontmatter_not_closed(self):
        meta, body = parse_frontmatter("---\ntitle: Hello\n\nBody without closing")
        assert meta == {}

    def test_ignores_lines_without_colon(self):
        txt = "---\ntitle: Hello\nno-colon-line\ntier: A\n---\nBody"
        meta, _ = parse_frontmatter(txt)
        assert meta == {"title": "Hello", "tier": "A"}


class TestExtractTitle:
    def test_first_h1_is_returned(self):
        body = "Some lead-in text\n# The Real Title\n\nContent"
        assert _extract_title(body) == "The Real Title"

    def test_untitled_when_no_h1(self):
        assert _extract_title("Body without any h1 line") == "Untitled"

    def test_h2_not_picked(self):
        body = "## Sub heading\n# Real Title"
        assert _extract_title(body) == "Real Title"


class TestSlugify:
    def test_lowercases_and_kebabs(self):
        assert slugify("Hello World") == "hello-world"

    def test_strips_accents(self):
        assert slugify("À l'épopée française") == "a-lepopee-francaise"

    def test_strips_special_chars(self):
        assert slugify("Concept: foo/bar (test)") == "concept-foobar-test"

    def test_truncates_to_max_len(self):
        long = "a" * 100
        assert len(slugify(long, max_len=30)) == 30

    def test_collapses_dashes(self):
        assert slugify("foo---bar") == "foo-bar"

    def test_strips_trailing_dashes_after_truncation(self):
        # Truncating mid-dash must not leave trailing "-"
        result = slugify("hello world foo bar", max_len=12)
        assert not result.endswith("-")


class TestBuildConceptsSummary:
    def test_empty_list_returns_empty_string(self):
        assert _build_concepts_summary([]) == ""

    def test_formats_tier_prefix(self):
        concepts = [{"tier": "S", "concept_title": "Foo", "essence": "bar"}]
        out = _build_concepts_summary(concepts)
        assert out.startswith("[S]")
        assert "Foo" in out
        assert "bar" in out

    def test_handles_missing_fields_gracefully(self):
        # No tier, no title, no essence → doesn't crash
        out = _build_concepts_summary([{}])
        assert "[?]" in out  # tier fallback

    def test_truncates_long_essence_to_120(self):
        long_essence = "x" * 500
        concepts = [{"tier": "A", "concept_title": "T", "essence": long_essence}]
        out = _build_concepts_summary(concepts)
        assert "x" * 120 in out
        assert "x" * 121 not in out

    def test_joins_with_newlines(self):
        concepts = [
            {"tier": "S", "concept_title": "A", "essence": "1"},
            {"tier": "A", "concept_title": "B", "essence": "2"},
        ]
        out = _build_concepts_summary(concepts)
        assert out.count("\n") == 1  # 2 lines → 1 separator


class TestBatchJobsFile:
    """save_batch_job / load_pending_batch_job / clear_batch_job persist
    a JSON state to LOGS_DIR/batch_jobs.json. Redirect the constant
    via monkeypatch for isolation."""

    def test_save_then_load_roundtrip(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "LOGS_DIR", tmp_path)
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", tmp_path / "batch_jobs.json")
        save_batch_job("ai", "msgbatch_01ABC")
        assert load_pending_batch_job("ai") == "msgbatch_01ABC"

    def test_load_returns_none_when_file_absent(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", tmp_path / "nonexistent.json")
        assert load_pending_batch_job("ai") is None

    def test_load_returns_none_on_malformed_json(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        bad = tmp_path / "batch_jobs.json"
        bad.write_text("not valid json {{{")
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", bad)
        assert load_pending_batch_job("ai") is None

    def test_save_preserves_other_domains(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "LOGS_DIR", tmp_path)
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", tmp_path / "batch_jobs.json")
        save_batch_job("ai", "batch_AI")
        save_batch_job("iot", "batch_IOT")
        assert load_pending_batch_job("ai") == "batch_AI"
        assert load_pending_batch_job("iot") == "batch_IOT"

    def test_clear_removes_only_specified_domain(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "LOGS_DIR", tmp_path)
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", tmp_path / "batch_jobs.json")
        save_batch_job("ai", "batch_AI")
        save_batch_job("iot", "batch_IOT")
        clear_batch_job("ai")
        assert load_pending_batch_job("ai") is None
        assert load_pending_batch_job("iot") == "batch_IOT"

    def test_clear_silent_on_missing_file(self, tmp_path, monkeypatch):
        import paper_synthesizer as ps
        monkeypatch.setattr(ps, "BATCH_JOBS_FILE", tmp_path / "nonexistent.json")
        # Should not raise
        clear_batch_job("ai")


class TestBatchCustomId:
    """Anthropic Batch API limits custom_id to 64 chars. Regression test."""

    def test_long_path_produces_id_under_64_chars(self):
        long_path = "_inbox/raw/papers/ai/2604.08545v1_act_wisely_cultivating_meta_cognitive_tool_use_in_agentic_mode_for_papers_too_long.md"
        assert len(long_path) > 64
        result = _batch_custom_id(long_path)
        assert len(result) <= 64

    def test_deterministic_same_path_same_id(self):
        path = "_inbox/raw/papers/ai/2604.08545v1_foo.md"
        assert _batch_custom_id(path) == _batch_custom_id(path)

    def test_different_paths_different_ids(self):
        assert _batch_custom_id("a/b.md") != _batch_custom_id("a/c.md")


class TestSanitizePaperId:
    def test_arxiv_id_replaces_colon_and_dot(self):
        assert sanitize_paper_id("arxiv:2401.12345") == "arxiv-2401-12345"

    def test_s2_id_replaces_colon(self):
        assert sanitize_paper_id("s2:abc1234567890abc") == "s2-abc1234567890abc"

    def test_no_special_chars_unchanged(self):
        assert sanitize_paper_id("arxiv-2401-12345") == "arxiv-2401-12345"


class TestParseConceptsFromText:
    def test_parses_single_valid_concept(self):
        text = '''
{"concept_title": "Le federated learning réduit la transmission de données de 60%",
 "tier": "S",
 "tier_reason": "Applicable à second-brain pour sync offline",
 "essence": "Entraîner localement, partager uniquement les gradients.",
 "detail": "Détail complet ici.",
 "tags": ["ml", "privacy"],
 "simple_explanation": "Apprendre sans envoyer ses données.",
 "paper_id": "arxiv:2401.12345",
 "source_url": "https://arxiv.org/abs/2401.12345"}
'''
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 1
        assert concepts[0]["tier"] == "S"
        assert concepts[0]["concept_title"].startswith("Le federated")

    def test_parses_multiple_concepts(self):
        text = '''
{"concept_title": "Concept A", "tier": "S", "essence": "E1",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "arxiv:1", "source_url": "http://a"}

{"concept_title": "Concept B", "tier": "A", "essence": "E2",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "arxiv:1", "source_url": "http://a"}
'''
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 2

    def test_ignores_invalid_json(self):
        text = 'Some prose {"broken": json, } more prose'
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 0

    def test_ignores_json_missing_required_keys(self):
        text = '{"title": "No concept_title key", "tier": "S"}'
        concepts = parse_concepts_from_text(text)
        assert len(concepts) == 0

    def test_filters_by_tier_in_caller(self):
        text = '''
{"concept_title": "Tier S concept", "tier": "S", "essence": "E",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "p", "source_url": "u"}
{"concept_title": "Tier B concept", "tier": "B", "essence": "E",
 "tier_reason": "r", "detail": "d", "tags": [], "simple_explanation": "s",
 "paper_id": "p", "source_url": "u"}
'''
        all_concepts = parse_concepts_from_text(text)
        assert len(all_concepts) == 2
        tier_s = [c for c in all_concepts if c["tier"] == "S"]
        assert len(tier_s) == 1
