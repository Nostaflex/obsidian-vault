# tests/test_paper_synthesizer.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_synthesizer import (
    _batch_custom_id,
    parse_concepts_from_text,
    sanitize_paper_id,
)


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
